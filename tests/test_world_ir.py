"""The represented half: arbitrary topology, nested claims, and no silent merges.

Everything the flow layer refuses, this layer must accept. A world with a cycle
in it is a road network, not a bug; a claim about a claim is *casey believes that
lara performed exam 17*, not a reification hack; two ids from two sources are two
identities until something claims otherwise, with a confidence.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.artifact import Interval, Provenance
from symbolic_ai_core.world import (Alignment, Claim, Entity, EntityRef, Facet,
                                    Quantity, WorldDelta, WorldSnapshot,
                                    check_profiles)


def road_network() -> WorldSnapshot:
    """Four junctions in a loop. The canonical thing a DAG cannot hold."""
    ids = ["j1", "j2", "j3", "j4"]
    ents = {i: Entity(id=i, types=("junction",),
                      facets={"geo.place": Facet("geo.place", {"name": i})})
            for i in ids}
    claims = tuple(
        Claim("road", {"from": EntityRef(a), "to": EntityRef(b)})
        for a, b in zip(ids, ids[1:] + ids[:1]))
    return WorldSnapshot(entities=ents, claims=claims)


def test_world_ir_accepts_cycles():
    w = road_network()
    assert w.neighbours("j1") == ("j2", "j4")
    # and the cycle survives a round trip through JSON
    assert WorldSnapshot.from_dict(w.to_dict()).to_dict() == w.to_dict()


def test_world_ir_accepts_a_self_loop():
    """A bus route returning to its depot. Not filtered, because it is real."""
    w = WorldSnapshot(entities={"d": Entity("d")},
                      claims=(Claim("route", {"from": EntityRef("d"),
                                              "to": EntityRef("d")}),))
    assert "d" in w.neighbours("d")


def test_nested_claim_roundtrip():
    inner = Claim("performed", {"agent": EntityRef("lara"),
                                "patient": EntityRef("exam_17")})
    outer = Claim("believes", {"believer": EntityRef("casey"), "content": inner},
                  modality="believed",
                  valid_time=Interval("2026-01-01", "2026-12-31"))
    assert outer.depth() == 2
    assert outer.entities() == ("casey", "lara", "exam_17")
    back = Claim.from_dict(outer.to_dict())
    assert back == outer
    assert isinstance(back.roles["content"], Claim)


def test_a_role_filler_keeps_its_kind():
    """`"dog"` the word and `EntityRef("dog")` the thing are different claims."""
    word = Claim("mentions", {"what": "dog"})
    thing = Claim("mentions", {"what": EntityRef("dog")})
    assert word.to_dict() != thing.to_dict()
    assert word.entities() == () and thing.entities() == ("dog",)
    assert Claim.from_dict(word.to_dict()).roles["what"] == "dog"


def test_claim_provenance_roundtrip():
    c = Claim("population", {"of": EntityRef("sf"),
                             "value": Quantity(873965, "person")},
              confidence=0.9,
              valid_time=Interval("2020-04-01", None),
              transaction_time=Interval("2026-08-18", None),
              evidence=("artifact:blake2b:abc",),
              assumptions=("census undercount not corrected",),
              provenance=Provenance(producer="census_reader",
                                    source="uscb", source_version="2020",
                                    license="US Government work"))
    back = Claim.from_dict(c.to_dict())
    assert back == c
    assert back.provenance.source_version == "2020"
    assert back.valid_time != back.transaction_time, (
        "one time cannot answer 'what did we believe on the day we decided'")


def test_confidence_none_is_not_one():
    assert Claim("p").confidence is None
    with pytest.raises(ValueError, match="not a probability"):
        Claim("p", confidence=1.5)


def test_polarity_and_modality_are_closed_vocabularies():
    with pytest.raises(ValueError, match="polarity"):
        Claim("p", polarity="maybe")
    with pytest.raises(ValueError, match="modality"):
        Claim("p", modality="vibes")


def test_a_quantity_must_name_its_unit():
    with pytest.raises(ValueError, match="unit"):
        Quantity(3.0, "")
    assert Quantity(3.0, "1").unit == "1", "dimensionless still says so"


def test_source_native_ids_survive():
    """Three ids for one animal stay three entities; sameness is a claim."""
    w = WorldSnapshot(entities={
        "wn:dog.n.01": Entity("wn:dog.n.01"),
        "wd:Q144": Entity("wd:Q144"),
        "cn:/c/en/dog": Entity("cn:/c/en/dog"),
    }, alignments=(
        Alignment("wn:dog.n.01", "wd:Q144", relation="close_match",
                  confidence=0.98, method="label+gloss"),
    ))
    assert len(w.entities) == 3
    a = w.alignments[0]
    assert a.confidence == 0.98
    assert a.as_claim().predicate == "close_match"
    assert WorldSnapshot.from_dict(w.to_dict()) == w


def test_an_alignment_within_one_namespace_is_refused():
    with pytest.raises(ValueError, match="are both in"):
        Alignment("wd:Q144", "wd:Q145", relation="close_match")


def test_a_shared_vendor_prefix_is_not_a_shared_namespace():
    """The bug real bytes found. This repo's own corpus writes
    `kg:sec:cik:320193` and `kg:lei:2138...`; splitting on the first colon
    called both "kg" and refused every genuine cross-source alignment in 3.3
    million entities."""
    a = Alignment("kg:sec:cik:320193", "kg:lei:HWUPKR0MPOU8FGXBT394")
    assert a.relation == "possibly_same"


def test_the_same_source_under_a_vendor_prefix_is_still_refused():
    with pytest.raises(ValueError, match="are both in"):
        Alignment("kg:sec:cik:1", "kg:sec:cik:2")


def test_a_stated_source_overrides_the_guess():
    """Reading an id is guessing; the caller usually knows better."""
    with pytest.raises(ValueError, match="are both in"):
        Alignment("a:1", "b:2", left_source="same", right_source="same")
    ok = Alignment("kg:x:1", "kg:x:2", left_source="sec", right_source="gleif")
    assert ok.left_source == "sec"


def test_an_alignment_relation_is_a_closed_vocabulary():
    with pytest.raises(ValueError, match="alignment relation"):
        Alignment("wn:a", "wd:b", relation="probably_ok")


def test_one_entity_carries_several_profiles_without_duplication():
    sf = (Entity("sf", types=("city",))
          .with_facet(Facet("geo.place", {"lat": 37.77, "lon": -122.42}))
          .with_facet(Facet("core.identity", {"name": "San Francisco"}))
          .with_facet(Facet("logic.term", {"symbol": "sf"})))
    assert sf.profiles() == ("core.identity", "geo.place", "logic.term")
    assert sf.has("geo.place", "logic.term")
    w = WorldSnapshot(entities={"sf": sf})
    geo = w.project(["geo.place"])
    assert geo.entity("sf").profiles() == ("geo.place",)
    assert w.entity("sf").profiles() == ("core.identity", "geo.place",
                                         "logic.term"), "project mutated its input"


def test_an_unregistered_profile_is_refused():
    with pytest.raises(ValueError, match="unknown profile"):
        Facet("geo.plaec", {})
    with pytest.raises(ValueError, match="unknown profile"):
        check_profiles(["scene.pose", "scene.psoe"])


def test_a_missing_capability_is_a_loud_refusal():
    w = WorldSnapshot(entities={"a": Entity("a", facets={
        "logic.term": Facet("logic.term", {})})})
    assert w.provides(["logic.term"])
    assert not w.provides(["scene.body"])
    with pytest.raises(KeyError, match="scene.body"):
        w.require(["scene.body"], who="rigid_body kernel")


def test_a_delta_does_not_mutate_the_world_it_is_applied_to():
    before = road_network()
    snapshot = before.to_dict()
    d = WorldDelta(entities=(Entity("j5"),),
                   claims=(Claim("road", {"from": EntityRef("j4"),
                                          "to": EntityRef("j5")}),))
    after = d.apply(before)
    assert before.to_dict() == snapshot, "apply mutated its input"
    assert "j5" in after.entities and "j5" not in before.entities
    assert len(after.claims) == len(before.claims) + 1


def test_a_delta_can_retract():
    before = road_network()
    after = WorldDelta(retracted=(0,)).apply(before)
    assert len(after.claims) == len(before.claims) - 1


def test_applying_a_delta_merges_facets_and_unions_types():
    w = WorldSnapshot(entities={"sf": Entity("sf", types=("city",), facets={
        "geo.place": Facet("geo.place", {"lat": 37.77})})})
    after = WorldDelta(entities=(Entity("sf", types=("port",), facets={
        "core.identity": Facet("core.identity", {"name": "SF"})}),)).apply(w)
    e = after.entity("sf")
    assert set(e.types) == {"city", "port"}
    assert e.profiles() == ("core.identity", "geo.place")
