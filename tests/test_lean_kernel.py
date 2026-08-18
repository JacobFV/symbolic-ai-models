"""Lean: the verifier, and the only kernel in the stack that vetoes.

The relational kernels are untyped. `link(truck_0, region_1)` is a well-formed
datalog fact and a well-formed ASP atom, and neither can notice that a vehicle
was passed where a region belongs. This kernel reads the types the world already
carries — the `types` tuple the relational projection emits as an inert `type/2`
fact and never consults — and typechecks against them.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from symbolic_ai_core.world import (Claim, Entity, EntityRef, Facet, Quantity,
                                    WorldSnapshot)
from symbolic_ai_kernels import KernelRequest, get_kernel
from symbolic_ai_kernels.lean import project_world

K = get_kernel("lean@1")


def typed_world() -> WorldSnapshot:
    return WorldSnapshot(
        entities={
            "r0": Entity("r0", types=("region",)),
            "r1": Entity("r1", types=("region",)),
            "v0": Entity("v0", types=("vehicle",)),
        },
        claims=(Claim("link", {"a": EntityRef("r0"), "b": EntityRef("r1")}),
                Claim("mass", {"of": EntityRef("v0"),
                               "value": Quantity(1200.0, "kg")})))


def run(world):
    return K.run(K.project(world, KernelRequest()), KernelRequest())


# --- what it is for -------------------------------------------------------
def test_a_well_typed_world_is_not_refuted():
    r = run(typed_world())
    assert r.ok and r.diagnostics["refuted"] == 0
    assert r.delta.is_empty(), (
        "'this claim typechecks' was written into the world; that is a fact "
        "about the projection, not about the world")


def test_role_confusion_is_caught_by_name():
    w = typed_world()
    bad = WorldSnapshot(entities=w.entities, claims=w.claims + (
        Claim("link", {"a": EntityRef("v0"), "b": EntityRef("r1")}),))
    r = run(bad)
    assert r.diagnostics["refuted"] == 1
    why = r.artifacts["refutations"][0]["why"]
    assert "vehicle" in why and "region" in why


def test_the_untyped_kernels_cannot_see_it():
    """The comparison that justifies a fourth kernel."""
    from symbolic_ai_kernels.datalog import Atom, Literal, Rule, Var

    X, Y = Var("x"), Var("y")
    w = typed_world()
    bad = WorldSnapshot(entities=w.entities, claims=w.claims + (
        Claim("link", {"a": EntityRef("v0"), "b": EntityRef("r1")}),))
    dl = get_kernel("datalog@1")
    p = dl.project(bad, KernelRequest(params={"rules": [
        Rule(Atom("near", (X, Y)), (Literal(Atom("link", (X, Y))),))]}))
    out = dl.run(p, KernelRequest())
    derived = {tuple(getattr(v, "id", v) for v in c.roles.values())
               for c in out.claims}
    assert ("v0", "r1") in derived, (
        "datalog rejected the ill-typed fact, so this kernel has no job")
    assert run(bad).diagnostics["refuted"] == 1


def test_arity_disagreement_is_caught():
    w = typed_world()
    bad = WorldSnapshot(entities=w.entities, claims=w.claims + (
        Claim("link", {"a": EntityRef("r0"), "b": EntityRef("r1"),
                       "c": EntityRef("r0")}),))
    assert run(bad).diagnostics["refuted"] == 1


# --- modality, and why this projection does not filter it -----------------
def test_a_hypothesis_is_still_typechecked():
    """Type validity is independent of whether a claim is asserted. Datalog
    refuses to project a hypothesis because asserting it would make it a
    measurement; rejecting a badly-typed one BEFORE anybody adopts it is
    exactly the verifier's job."""
    w = typed_world()
    bad = WorldSnapshot(entities=w.entities, claims=w.claims + (
        Claim("link", {"a": EntityRef("v0"), "b": EntityRef("r1")},
              modality="hypothesised"),))
    assert run(bad).diagnostics["refuted"] == 1

    from symbolic_ai_kernels.datalog import project_world as relational
    assert any("hypothesised" in d.why for d in relational(bad).discarded)


# --- the projection's own losses -----------------------------------------
def test_a_multiply_typed_entity_is_a_declared_loss():
    """A monomorphic signature holds one sort. San Francisco is a place and a
    jurisdiction, and the discard says what the consequence will look like."""
    w = WorldSnapshot(entities={
        "sf": Entity("sf", types=("place", "jurisdiction"))},
        claims=(Claim("in", {"a": EntityRef("sf")}),))
    p = project_world(w)
    d = [x for x in p.discarded if x.kind == "entity"]
    assert d and "projection error" in d[0].why


def test_untyped_entities_make_the_check_vacuous_and_it_says_so():
    w = WorldSnapshot(entities={"a": Entity("a"), "b": Entity("b")},
                      claims=(Claim("p", {"x": EntityRef("a")}),
                              Claim("p", {"x": EntityRef("b")})))
    r = run(w)
    assert r.diagnostics["untyped_entities"] == 2
    assert r.diagnostics["vacuous"] is True
    assert r.diagnostics["refuted"] == 0, (
        "an untyped world cannot produce a type error; if it did, the sort "
        "assignment is inventing constraints")


def test_a_literal_and_an_entity_id_do_not_collide():
    """`"r0"` the string and `r0` the region are different things; a signature
    that let them share a constant would typecheck a claim nobody made."""
    w = typed_world()
    bad = WorldSnapshot(entities=w.entities, claims=w.claims + (
        Claim("link", {"a": "r0", "b": EntityRef("r1")}),))
    assert run(bad).diagnostics["refuted"] == 1


def test_a_nested_claim_is_discarded_with_a_reason():
    w = typed_world()
    nested = WorldSnapshot(entities=w.entities, claims=w.claims + (
        Claim("believes", {"who": EntityRef("v0"),
                           "what": Claim("link", {"a": EntityRef("r0"),
                                                  "b": EntityRef("r1")})}),))
    p = project_world(nested)
    assert any("nested proposition" in d.why for d in p.discarded)


def test_an_empty_world_is_a_refusal_not_a_pass():
    r = run(WorldSnapshot())
    assert not r.ok and "would be true and empty" in r.refused


# --- the manifest ---------------------------------------------------------
def test_it_is_the_veto_and_it_needs_no_toolchain():
    m = K.manifest
    assert m.authority["type_valid"] == "veto"
    assert m.runtime == "native" and m.dependencies == ()
    assert K.available() == (True, "")


def test_a_refutation_beats_a_majority_in_fusion():
    from symbolic_ai_core.artifact import Provenance
    from symbolic_ai_core.runtime import fuse

    proposals = [Claim("type_valid", {"claim": "claim#3"},
                       provenance=Provenance(producer=f"guesser{i}"))
                 for i in range(3)]
    veto = Claim("type_valid", {"claim": "claim#3"}, polarity="negative",
                 provenance=Provenance(producer="lean@1"))
    out = fuse(proposals + [veto],
               authority={"lean@1": dict(K.manifest.authority)})
    assert len(out.vetoed) == 3
    assert [c.provenance.producer for c in out.resolved] == ["lean@1"]
