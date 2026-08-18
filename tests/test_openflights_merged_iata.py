"""The guard on a defect no existing check could see.

openflights merges airports that share an IATA code: ``kg:iata:AMN`` carries
Gratiot Community Airport's label, ICAO ``KAMN`` and Michigan coordinates
alongside ``city=Kamloops country=Canada``. Nothing in the corpus notices --
the row is well-formed, its coordinates are in range, and ``airport_country``'s
ground-truth anchor reads the *same* merged-in half it is scored against, so it
scores an exact 1.0 straight over the defect.

The tests that matter here are the synthetic ones. A guard whose test passes
before the guard exists is not a test, so
:meth:`TestTheGuardFires.test_an_injected_merge_stops_the_load` builds a table
that the pre-guard ``load_airports`` admits without complaint.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from symbolic_ai_adapters import load_airports
from symbolic_ai_adapters.openflights import (MERGED_IATA_NODES,
                                              OpenflightsIntegrityError,
                                              check_iata_merges,
                                              detect_merged_iata_nodes)
from symbolic_ai_core.source import SourceRegistry, data_root


def _write(path: Path, rows: list[dict]) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    pq.write_table(pa.Table.from_pylist(rows), path / "airports_toy_p0.parquet")


def _body(city: str, country: str, lat: float, lon: float, icao: str) -> str:
    return f"city={city} country={country} lat={lat} lon={lon} icao={icao}"


def _clean_rows() -> list[dict]:
    """Two countries, five airports each, on their own ICAO prefixes.

    Wonderland sits at the equator on ``WW*``; Otherland at 50N/50E on ``OO*``.
    Five apiece clears both support floors, and ~7,000 km apart is enough
    displacement for the second instrument to have something to measure.
    """
    rows = []
    for i in range(5):
        rows.append({"id": f"kg:iata:W{i}0", "label": f"Wonder {i}",
                     "kind": "place",
                     "body": _body(f"Wtown{i}", "Wonderland",
                                   0.0 + 0.1 * i, 0.0 + 0.1 * i, f"WW{i}0"),
                     "source_url": None})
        rows.append({"id": f"kg:iata:O{i}0", "label": f"Other {i}",
                     "kind": "place",
                     "body": _body(f"Otown{i}", "Otherland",
                                   50.0 + 0.1 * i, 50.0 + 0.1 * i, f"OO{i}0"),
                     "source_url": None})
    return rows


def _merged_row() -> dict:
    """One body wearing two airports: Wonderland's ICAO and coordinates, and
    Otherland's city and country. Exactly the shape of ``kg:iata:AMN``."""
    return {"id": "kg:iata:XXX", "label": "Wonder Field", "kind": "place",
            "body": _body("Otown9", "Otherland", 0.5, 0.5, "WWXX"),
            "source_url": None}


def _rows_for(rows: list[dict]) -> dict:
    from symbolic_ai_adapters import parse_body
    out = {}
    for r in rows:
        kv = parse_body(r["body"])
        out[r["id"]] = (kv, (float(kv["lat"]), float(kv["lon"])))
    return out


class TestTheDetector:
    def test_a_clean_corpus_detects_nothing_but_is_still_eligible(self):
        """Both halves of the return matter: an empty ``detected`` from an
        empty ``eligible`` is a blind detector, not a clean corpus."""
        detected, eligible = detect_merged_iata_nodes(_rows_for(_clean_rows()))
        assert detected == frozenset()
        assert len(eligible) == 10

    def test_the_injected_merge_is_found(self):
        detected, _ = detect_merged_iata_nodes(
            _rows_for(_clean_rows() + [_merged_row()]))
        assert detected == frozenset({"kg:iata:XXX"})

    def test_a_thin_prefix_makes_the_row_ineligible(self):
        """The support floor is what keeps the rule off a prefix carrying one
        or two airports, where unanimity is an accident of sample size."""
        rows = _clean_rows()[:4] + [_merged_row()]      # 2 W, 2 O airports
        detected, eligible = detect_merged_iata_nodes(_rows_for(rows))
        assert detected == frozenset()
        assert eligible == frozenset()

    def test_a_shared_prefix_is_not_a_merge(self):
        """A territory sits on a prefix its administering state shares. Drop
        the unanimity requirement and this row flags -- which is the 71%
        false-positive rate the bare leave-one-out rule has corpus-wide."""
        rows = _clean_rows()
        rows.append({"id": "kg:iata:TER", "label": "Territory Field",
                     "kind": "place",
                     "body": _body("Ttown", "Otherland", 0.6, 0.6, "WWTE"),
                     "source_url": None})
        rows.append({"id": "kg:iata:TE2", "label": "Territory Two",
                     "kind": "place",
                     "body": _body("Ttown2", "Otherland", 0.7, 0.7, "WWT2"),
                     "source_url": None})
        detected, _ = detect_merged_iata_nodes(_rows_for(rows))
        assert detected == frozenset()

    def test_a_remote_airport_of_its_own_country_is_not_a_merge(self):
        """Displacement, not distance. An airport far from its countrymen but
        no closer to anyone else's is Easter Island, not a defect."""
        rows = _clean_rows()
        rows.append({"id": "kg:iata:REM", "label": "Remote Field",
                     "kind": "place",
                     "body": _body("Rtown", "Otherland", 25.0, 25.0, "WWRM"),
                     "source_url": None})
        detected, _ = detect_merged_iata_nodes(_rows_for(rows))
        assert detected == frozenset()


class TestTheGuardFires:
    def test_an_injected_merge_stops_the_load(self, tmp_path):
        """**The test that fails on the pre-guard code path.** Before
        ``check_iata_merges`` existed this load returned an eleven-entity
        snapshot and said nothing."""
        _write(tmp_path, _clean_rows() + [_merged_row()])
        with pytest.raises(OpenflightsIntegrityError) as exc:
            load_airports(tmp_path)
        assert "kg:iata:XXX" in str(exc.value)

    def test_a_clean_table_loads(self, tmp_path):
        _write(tmp_path, _clean_rows())
        assert load_airports(tmp_path).admitted == 10

    def test_a_manifest_row_that_stopped_tripping_raises(self, monkeypatch):
        """The other direction. If the manifest names a row the detector can
        see and no longer flags, the manifest has become a lie about the bytes
        and every number measured under it is suspect."""
        monkeypatch.setattr("symbolic_ai_adapters.openflights.MERGED_IATA_NODES",
                            frozenset({"kg:iata:W00"}))
        with pytest.raises(OpenflightsIntegrityError) as exc:
            check_iata_merges(_rows_for(_clean_rows()))
        assert "kg:iata:W00" in str(exc.value)

    def test_a_manifest_row_the_detector_cannot_see_does_not_raise(self):
        """Restricting the staleness check to *eligible* rows is what makes the
        guard correct under a partial load. Firing on its own blindness would
        make it noise."""
        assert check_iata_merges(_rows_for(_clean_rows()[:4])) == frozenset()


@pytest.mark.skipif(not data_root().exists(), reason="snapshots not held here")
class TestAgainstTheRealSnapshot:
    @staticmethod
    @pytest.fixture(scope="class")
    def base():
        return next(s for s in SourceRegistry().snapshots().values()
                    if s.source == "openflights").resolve(data_root())

    def test_the_snapshot_carries_exactly_the_seven(self, base):
        """Reached independently by a cross-source join against geonames
        (``scripts/two_source_country_conflict.py``) and by this detector,
        which never looks outside openflights."""
        res = load_airports(base)
        assert res.admitted == 6072
        assert len(MERGED_IATA_NODES) == 7

    def test_the_merged_rows_load_unrepaired(self, base):
        """The guard refuses an *unrecognised* contamination; it does not
        correct a recognised one. Every published ``airport_country`` number
        was measured with these seven in, and repairing them on load would
        silently redefine all of them."""
        world = load_airports(base).world
        amn = world.entities["kg:iata:AMN"]
        assert amn.facets["core.identity"].values["country"] == "Canada"
        assert amn.facets["geo.place"].values["lat"] == pytest.approx(43.3221,
                                                                     abs=1e-3)
        for nid in MERGED_IATA_NODES:
            assert nid in world.entities
