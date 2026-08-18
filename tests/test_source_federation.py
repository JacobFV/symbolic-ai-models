"""Sources, snapshots, artifacts: schemas, vocabularies, refs and licence closure.

The tests that matter here are the ones about what *cannot* happen: an unknown
licence cannot come out permissive, a source card cannot claim to know what is
on a disk, a composite source cannot be counted twice, and a location cannot
change an identity.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.source import (LICENSE_ORDER, SourceRegistry,
                                     canonical_json, data_root, license_closure,
                                     manifest_hash, parse_ref, typed_ref)
from symbolic_ai_core.source.build import build_catalog, catalog_path
from symbolic_ai_core.source.validate import validate_all, vocab


def reg() -> SourceRegistry:
    return SourceRegistry()


# --- the manifests in this repo are valid --------------------------------
def test_every_manifest_validates():
    errs = validate_all()
    assert errs == [], "\n".join(errs)


def test_every_source_card_has_a_matching_filename():
    for sid, s in reg().sources().items():
        assert s.path is not None and s.path.stem == sid


def test_the_generated_catalog_is_current():
    """`generated/` is compiled and never edited. A hand edit fails here."""
    import json
    on_disk = json.loads(catalog_path().read_text(encoding="utf-8"))
    rebuilt = build_catalog()
    assert on_disk["digest"] == rebuilt["digest"], (
        "generated/catalog.json is stale -- rebuild it with "
        "symbolic_ai_core.source.build.write_catalog()")


# --- licence closure ------------------------------------------------------
def test_license_closure_takes_the_most_restrictive_term():
    c = license_closure([
        {"redistribution": "permitted", "commercial_use": "permitted"},
        {"redistribution": "share_alike", "commercial_use": "permitted"},
    ])
    assert c["redistribution"] == "share_alike"


def test_an_unknown_licence_poisons_the_closure():
    """`unresolved` is not a synonym for `permitted`. This is the whole point."""
    c = license_closure([{"redistribution": "permitted"},
                         {"redistribution": "unresolved"}])
    assert c["redistribution"] == "unresolved"
    assert LICENSE_ORDER[-1] == "unresolved"


def test_an_artifact_with_no_parents_is_unresolved_not_permitted():
    assert license_closure([])["redistribution"] == "unresolved"


def test_the_staged_artifacts_inherit_a_blocking_closure():
    """A real consequence, not a hypothetical: these cannot be published."""
    cat = build_catalog()
    for aid, closure in cat["closures"].items():
        assert closure["redistribution"] != "permitted", (
            f"{aid} came out publishable; its parents include a prohibited "
            f"and several unresolved sources")


def test_a_prohibited_parent_is_actually_present():
    """Guards the test above from passing for the wrong reason."""
    sources = reg().sources()
    assert sources["commandagi-kg"].license["redistribution"] == "prohibited"


# --- identity, refs and locations ----------------------------------------
def test_a_bare_string_is_not_a_ref():
    assert parse_ref("source/openalex") == ("source", "openalex")
    with pytest.raises(ValueError, match="typed ref"):
        parse_ref("openalex")
    with pytest.raises(ValueError, match="typed ref"):
        parse_ref("dataset_thing/openalex")
    with pytest.raises(ValueError, match="unknown ref class"):
        typed_ref("corpus", "x")


def test_filesystem_location_is_never_identity():
    m = {"id": "x@1", "source": "source/x", "acquired": {"at": "2026-01-01"},
         "storage": {"layout": "source_native", "locations": ["file:///a"],
                     "root": "sources/x/1"},
         "inventory": {"s": {"files": 1, "bytes": 2}}}
    h1 = manifest_hash(m)
    moved = dict(m, storage=dict(m["storage"],
                                 locations=["file:///a", "s3://mirror/x"],
                                 root="elsewhere/x/1"))
    assert manifest_hash(moved) == h1
    changed = dict(m, inventory={"s": {"files": 2, "bytes": 2}})
    assert manifest_hash(changed) != h1


def test_a_comment_or_key_order_does_not_change_an_identity():
    a = {"b": 1, "a": {"y": 2, "x": 1}}
    b = {"a": {"x": 1, "y": 2}, "b": 1}
    assert canonical_json(a) == canonical_json(b)


# --- a source card says nothing about this disk ---------------------------
def test_a_source_card_carries_no_holdings():
    forbidden = {"held_inventory", "held", "local_root", "on_disk"}
    for sid, s in reg().sources().items():
        assert not (forbidden & set(s.raw)), (
            f"{sid} asserts something about a disk; that belongs on a snapshot")


def test_holdings_are_a_property_of_the_disk_and_absence_is_normal(tmp_path):
    r = reg()
    snaps = r.snapshots()
    assert snaps, "no snapshots registered"
    some = next(iter(snaps.values()))
    assert r.held(some, tmp_path) is False, (
        "a machine without the bytes must report False, not raise")


def test_the_census_reports_every_snapshot():
    rows = reg().census()
    assert len(rows) == len(reg().snapshots())
    assert all({"snapshot", "source", "files", "bytes", "held"} <= set(r)
               for r in rows)


# --- composite sources ----------------------------------------------------
def test_composite_sources_do_not_double_count():
    """CSKG consolidates seven upstreams. Ingesting one directly *and* through
    CSKG is one observation seen twice, and the card has to say so."""
    cskg = reg().source("cskg")
    text = (cskg.raw.get("notes", "") + cskg.raw.get("description", "")).lower()
    assert "composite" in text or "seven" in text or "one observation" in text

    kg = reg().source("commandagi-kg")
    note = kg.raw.get("notes", "").lower()
    assert "not three sources" in note or "one graph" in note, (
        "the three CommandAGI storage formats must be marked as one graph, or "
        "their agreeing counts read as three independent verifications")


def test_the_vendored_cskg_projection_is_named_as_a_projection():
    note = reg().source("cskg").raw.get("notes", "")
    assert "projection" in note and "selectional" in note


# --- vocabularies ---------------------------------------------------------
def test_every_enum_lives_in_one_file():
    v = vocab()
    assert "unresolved" in v["access_classes"]
    assert set(v["alignment_relations"]) >= {"exact_match", "possibly_same",
                                             "contradicts"}
    from symbolic_ai_core.world.claim import ALIGNMENT_RELATIONS
    assert set(ALIGNMENT_RELATIONS) == set(v["alignment_relations"]), (
        "the world IR and ontology/vocab.yaml disagree about alignment "
        "relations -- two allegedly identical vocabularies have drifted, which "
        "is the exact failure ontology/README.md exists to prevent")


def test_the_data_root_is_overridable(monkeypatch):
    monkeypatch.setenv("SYMBOLIC_AI_DATA", "/tmp/elsewhere")
    assert str(data_root()) == "/tmp/elsewhere"
