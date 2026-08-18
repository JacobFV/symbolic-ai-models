"""What the held columns can populate, as against what the cards declare.

The audit that produced this module found that GeoNames -- the only geospatial
source in 14 GB -- arrives with no coordinate column, so the tests here are
mostly about the two ways that could have stayed invisible: a capability
inferred from a name rather than a column, and an empty measurement reading as
a confident negative.
"""

from __future__ import annotations

import json

import pytest

from symbolic_ai_core.source import SourceRegistry, data_root
from symbolic_ai_core.source.columns import (DETECTABLE_PROFILES,
                                             GENERIC_SCHEMAS, IngestProjection,
                                             body_fields,
                                             SnapshotSchema, _fields_of,
                                             audit_snapshots, build_schemas,
                                             declared_profiles,
                                             profiles_supported, schemas_path,
                                             write_schemas)


def _schema(**kw) -> SnapshotSchema:
    base = dict(snapshot="s", source="src", files_read=1, rows=10,
                columns=(("id", "kind"),), fields=frozenset())
    base.update(kw)
    return SnapshotSchema(**base)


class TestFieldDetection:
    def test_a_latitude_column_is_found_under_several_spellings(self):
        for name in ("lat", "latitude", "LAT", "lat_deg"):
            assert "lat" in _fields_of([name]), name

    def test_a_place_needs_both_halves_of_a_coordinate(self):
        """The failure that started this: a source with a name and a country
        code and no numbers is not a geo source."""
        assert "geo.place" not in profiles_supported({"lat", "identity"})
        assert "geo.place" not in profiles_supported({"lon", "identity"})
        assert "geo.place" in profiles_supported({"lat", "lon"})

    def test_the_bare_triple_schema_yields_no_domain_field(self):
        assert _fields_of(("source_id", "target_id", "kind")) == {
            "identity", "relation"}

    def test_a_value_column_does_not_imply_a_unit(self):
        """``Quantity`` refuses a unitless number, so a source with a value and
        no unit cannot populate one without inventing the unit."""
        fields = _fields_of(("source_id", "target_id", "kind", "value"))
        assert "value" in fields and "unit" not in fields


class TestGenericDetection:
    def test_a_snapshot_of_only_bare_schemas_is_generic(self):
        assert _schema(columns=(GENERIC_SCHEMAS[0],)).generic

    def test_one_domain_bearing_file_makes_it_not_generic(self):
        assert not _schema(
            columns=(GENERIC_SCHEMAS[0], ("id", "lat", "lon"))).generic

    def test_a_snapshot_that_read_nothing_is_not_reported_as_generic(self):
        """Absence of evidence. An unreadable snapshot must not read as a
        confident 'this source carries nothing'."""
        assert not _schema(columns=(), files_read=0).generic


class TestIngestProjection:
    def _proj(self, declared, held):
        return IngestProjection(snapshot="s", source="src", declared=declared,
                                held=held, schema=_schema())

    def test_an_undetectable_declaration_is_not_counted_as_a_loss(self):
        p = self._proj(("geo.network",), ())
        assert not p.lossy and p.undetermined == ("geo.network",)

    def test_body_keys_are_read_only_for_unambiguous_names(self):
        assert body_fields(["lat=1 lon=2"]) == {"lat", "lon"}
        assert body_fields(["callsign=GENERAL active=Y"]) == frozenset()

    def test_a_declared_profile_absent_from_the_bytes_is_a_discard(self):
        p = self._proj(("geo.place", "core.identity"), ("core.identity",))
        assert p.discarded == ("geo.place",)
        assert p.retained == ("core.identity",)
        assert p.lossy

    def test_holding_more_than_the_card_declares_is_not_a_discard(self):
        p = self._proj(("core.identity",), ("core.identity", "core.time"))
        assert not p.lossy and p.discarded == ()


@pytest.mark.skipif(not data_root().exists(), reason="snapshots not held here")
class TestAgainstTheHeldBytes:
    @staticmethod
    @pytest.fixture(scope="class")
    def audits():
        return audit_snapshots(SourceRegistry(), data_root(), max_files=4)

    def test_every_snapshot_is_audited(self, audits):
        assert len(audits) == len(SourceRegistry().snapshots())

    def test_only_openflights_can_populate_a_coordinate(self, audits):
        """Written first as "no source can", which was true of the *columns*
        and false of the data: openflights hides lat/lon in its body string.
        The corrected claim is narrower and still worth pinning."""
        assert sorted(a.source for a in audits if "geo.place" in a.held) == [
            "openflights"]

    def test_geonames_is_the_one_provably_lossy_ingest(self, audits):
        """29 M rows of the repo's flagship gazetteer, and its body carries
        pop/feature/country/area and no coordinate at all."""
        assert sorted(a.source for a in audits if a.lossy) == ["geonames"]

    def test_a_declaration_with_no_detector_is_undetermined_not_discarded(
            self, audits):
        of = next(a for a in audits if a.source == "openflights")
        assert of.undetermined == ("geo.network",) and not of.lossy

    def test_the_shadow_schema_is_found_where_it_exists(self, audits):
        """gutenberg's only temporal field is `issued=` inside a body."""
        gb = next(a for a in audits if a.source == "gutenberg")
        assert "core.time" in gb.held

    def test_every_declared_profile_is_accounted_for(self, audits):
        """Retained, discarded or undetermined -- a declaration may not simply
        vanish from the audit."""
        for a in audits:
            assert (set(a.retained) | set(a.discarded)
                    | set(a.undetermined)) == set(a.declared)


class TestGeneratedDocument:
    @pytest.mark.skipif(not schemas_path().exists(),
                        reason="no audit generated here")
    def test_the_committed_audit_names_only_known_snapshots(self):
        doc = json.loads(schemas_path().read_text())
        known = set(SourceRegistry().snapshots())
        assert set(doc["snapshots"]) <= known

    @pytest.mark.skipif(not schemas_path().exists(),
                        reason="no audit generated here")
    def test_the_committed_audit_is_internally_consistent(self):
        doc = json.loads(schemas_path().read_text())
        for entry in doc["snapshots"].values():
            held = set(entry["held"])
            assert held == set(profiles_supported(entry["schema"]["fields"]))
            assert set(entry["discarded"]) == (
                (set(entry["declared"]) & DETECTABLE_PROFILES) - held)

    def test_an_empty_measurement_refuses_to_be_written(self, tmp_path):
        """A generated file asserting 'no source has coordinates' because it
        read no bytes is worse than no file at all."""
        with pytest.raises(RuntimeError, match="refusing to write"):
            write_schemas(tmp_path, data=tmp_path / "absent")

    def test_building_over_an_absent_root_reports_nothing_rather_than_lying(
            self, tmp_path):
        doc = build_schemas(data=tmp_path / "absent")
        assert doc["totals"]["rows_sampled"] == 0
        assert all(not e["held"] for e in doc["snapshots"].values())


class TestDeclaredProfiles:
    def test_a_card_with_no_streams_declares_nothing(self):
        class _S:
            raw = {}
        assert declared_profiles(_S()) == ()

    def test_profiles_union_across_streams(self):
        class _S:
            raw = {"streams": {"a": {"profiles": ["core.identity"]},
                               "b": {"profiles": ["geo.place",
                                                  "core.identity"]}}}
        assert declared_profiles(_S()) == ("core.identity", "geo.place")
