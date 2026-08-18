"""Datalog: the fixed point, stratified negation, and what the projection drops.

Tier 1 of the kernel stack. The engine tests are ordinary correctness; the
projection tests are the interesting ones, because a projection that silently
carried a hypothesis or a negated claim as a fact would produce a model that is
wrong in a way nothing downstream could detect.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.artifact import Interval
from symbolic_ai_core.world import (Claim, Entity, EntityRef, Facet, Quantity,
                                    WorldSnapshot)
from symbolic_ai_kernels import KernelRequest, get_kernel
from symbolic_ai_kernels.datalog import (Atom, Literal, Program, Rule,
                                         StratificationError, Var,
                                         add_facts_report, evaluate,
                                         project_world, rule_from_dict)

X, Y, Z = Var("x"), Var("y"), Var("z")

ANCESTRY = [
    Rule(Atom("ancestor", (X, Y)), (Literal(Atom("parent", (X, Y))),)),
    Rule(Atom("ancestor", (X, Z)), (Literal(Atom("parent", (X, Y))),
                                    Literal(Atom("ancestor", (Y, Z))))),
]


# --- the engine -----------------------------------------------------------
def test_transitive_closure():
    edb = {("parent", "b", "a"), ("parent", "c", "b"), ("parent", "d", "c")}
    model = evaluate(Program(tuple(ANCESTRY)), edb)
    anc = {f for f in model if f[0] == "ancestor"}
    assert anc == {("ancestor", "b", "a"), ("ancestor", "c", "b"),
                   ("ancestor", "d", "c"), ("ancestor", "c", "a"),
                   ("ancestor", "d", "b"), ("ancestor", "d", "a")}


def test_negation_as_failure_gives_defaults_with_exceptions():
    p = Program((
        Rule(Atom("flies", (X,)), (Literal(Atom("bird", (X,))),
                                   Literal(Atom("abnormal", (X,)), True))),
        Rule(Atom("abnormal", (X,)), (Literal(Atom("penguin", (X,))),)),
    ))
    model = evaluate(p, {("bird", "tweety"), ("bird", "pingu"),
                         ("penguin", "pingu")})
    assert ("flies", "tweety") in model
    assert ("flies", "pingu") not in model, "the exception did not defeat"


def test_negation_is_non_monotonic():
    """Adding a fact retracts a conclusion. This is why the semantics is
    metadata rather than convention."""
    p = Program((
        Rule(Atom("flies", (X,)), (Literal(Atom("bird", (X,))),
                                   Literal(Atom("abnormal", (X,)), True))),
        Rule(Atom("abnormal", (X,)), (Literal(Atom("penguin", (X,))),)),
    ))
    assert ("flies", "opus") in evaluate(p, {("bird", "opus")})
    assert ("flies", "opus") not in evaluate(p, {("bird", "opus"),
                                                 ("penguin", "opus")})


def test_negation_inside_its_own_recursion_is_refused():
    p = Program((
        Rule(Atom("p", (X,)), (Literal(Atom("base", (X,))),
                               Literal(Atom("q", (X,)), True))),
        Rule(Atom("q", (X,)), (Literal(Atom("base", (X,))),
                               Literal(Atom("p", (X,)), True))),
    ))
    with pytest.raises(StratificationError, match="no unique model"):
        evaluate(p, {("base", "a")})


def test_an_unsafe_rule_is_refused_at_construction():
    with pytest.raises(ValueError, match="unsafe rule"):
        Rule(Atom("p", (X, Y)), (Literal(Atom("q", (X,))),))
    with pytest.raises(ValueError, match="unsafe rule"):
        Rule(Atom("p", (X,)), (Literal(Atom("q", (X,))),
                               Literal(Atom("r", (Y,)), True)))


def test_a_fact_rule_needs_no_body():
    model = evaluate(Program((Rule(Atom("seed", ("a",))),)), set())
    assert model == {("seed", "a")}


# --- incremental ----------------------------------------------------------
def test_incremental_matches_a_full_recomputation():
    p = Program(tuple(ANCESTRY))
    edb = {("parent", "b", "a"), ("parent", "c", "b")}
    known = evaluate(p, edb)
    added, full = add_facts_report(p, known, {("parent", "d", "c")})
    assert not full, "a monotone addition should not have needed a recompute"
    assert known | added == evaluate(p, edb | {("parent", "d", "c")})


def test_an_addition_touching_negation_recomputes_rather_than_being_wrong():
    """Under negation a new fact can *retract* a conclusion, which no purely
    additive maintenance can express. It recomputes and says so."""
    p = Program((
        Rule(Atom("flies", (X,)), (Literal(Atom("bird", (X,))),
                                   Literal(Atom("abnormal", (X,)), True))),
        Rule(Atom("abnormal", (X,)), (Literal(Atom("penguin", (X,))),)),
    ))
    known = evaluate(p, {("bird", "opus")})
    assert ("flies", "opus") in known
    added, full = add_facts_report(p, known, {("penguin", "opus")})
    assert full, "an addition under negation was maintained additively"


def test_adding_nothing_new_is_free():
    p = Program(tuple(ANCESTRY))
    known = evaluate(p, {("parent", "b", "a")})
    assert add_facts_report(p, known, {("parent", "b", "a")}) == (set(), False)


# --- the projection -------------------------------------------------------
def world() -> WorldSnapshot:
    return WorldSnapshot(
        entities={
            "a": Entity("a", types=("person",),
                        facets={"core.identity": Facet("core.identity",
                                                       {"name": "Ada"})}),
            "b": Entity("b", types=("person",)),
            "c": Entity("c", types=("person",)),
        },
        claims=(
            Claim("parent", {"child": EntityRef("b"), "of": EntityRef("a")}),
            Claim("parent", {"child": EntityRef("c"), "of": EntityRef("b")}),
            # each of the following must be discarded, for a different reason
            Claim("believes", {"who": EntityRef("a"),
                               "what": Claim("parent",
                                             {"child": EntityRef("c"),
                                              "of": EntityRef("a")})}),
            Claim("parent", {"child": EntityRef("a"), "of": EntityRef("c")},
                  polarity="negative"),
            Claim("parent", {"child": EntityRef("a"), "of": EntityRef("b")},
                  modality="hypothesised"),
            Claim("mass", {"of": EntityRef("a"),
                           "value": Quantity(70.0, "kg")}),
            # projected, but with qualifications recorded as losses
            Claim("parent", {"child": EntityRef("c"), "of": EntityRef("a")},
                  confidence=0.6, valid_time=Interval("2020", "2021"),
                  scope="rumour"),
        ))


def discards_by_kind(p):
    out: dict[str, list[str]] = {}
    for d in p.discarded:
        out.setdefault(d.kind, []).append(d.why)
    return out


def test_the_projection_declares_every_loss_with_a_reason():
    p = project_world(world())
    by = discards_by_kind(p)
    claim_reasons = " ".join(by["claim"])
    assert "nested proposition" in claim_reasons
    assert "negation-as-failure" in claim_reasons
    assert "hypothesised" in claim_reasons
    assert "Quantity" in claim_reasons
    assert "confidence 0.6" in " ".join(by["uncertainty"])
    assert "untimed" in " ".join(by["valid_time"])
    assert "rumour" in " ".join(by["scope"])
    assert not p.lossless


def test_a_hypothesis_does_not_become_a_fact():
    p = project_world(world())
    facts = p.program.facts
    assert ("parent", "a", "b") not in facts, "a hypothesis was asserted"
    assert ("parent", "a", "c") not in facts, "a negative claim was asserted"


def test_entity_types_and_scalar_facets_project():
    p = project_world(world())
    assert ("type", "a", "person") in p.program.facts
    assert ("attr", "a", "core.identity.name", "Ada") in p.program.facts
    assert ("has_profile", "a", "core.identity") in p.program.facts


def test_a_non_scalar_facet_value_is_discarded_not_stringified():
    w = WorldSnapshot(entities={"a": Entity("a", facets={
        "scene.shape": Facet("scene.shape", {"mesh": [1, 2, 3]})})})
    p = project_world(w)
    assert any(d.kind == "facet" and "list" in d.why for d in p.discarded)
    assert not any(f[0] == "attr" for f in p.program.facts)


def test_the_semantics_travels_with_the_projection():
    assert project_world(world()).semantics == ("closed_world", "non_monotonic")


def test_rules_can_ride_on_a_logic_rule_facet():
    w = WorldSnapshot(
        entities={"kb": Entity("kb", facets={"logic.rule": Facet(
            "logic.rule", {"rules": [{
                "head": {"pred": "ancestor",
                         "terms": [{"var": "x"}, {"var": "y"}]},
                "body": [{"pred": "parent",
                          "terms": [{"var": "x"}, {"var": "y"}]}]}]})}),
                  "a": Entity("a"), "b": Entity("b")},
        claims=(Claim("parent", {"child": EntityRef("b"),
                                 "of": EntityRef("a")}),))
    p = project_world(w)
    assert p.meta["n_rules"] == 1
    out = get_kernel("datalog@1").run(p, KernelRequest())
    assert [c.predicate for c in out.claims] == ["ancestor"]


def test_a_malformed_rule_is_discarded_not_guessed():
    w = WorldSnapshot(entities={"kb": Entity("kb", facets={"logic.rule": Facet(
        "logic.rule", {"rules": [{"head": {"pred": "p", "terms": ["x"]}}]})})})
    p = project_world(w)
    assert any(d.kind == "rule" for d in p.discarded)
    assert p.meta["n_rules"] == 0


def test_a_bare_term_string_is_not_guessed_to_be_a_variable():
    with pytest.raises(ValueError, match="'var'"):
        rule_from_dict({"head": {"pred": "p", "terms": ["X"]}})


# --- the kernel -----------------------------------------------------------
def test_the_kernel_returns_derived_facts_not_the_whole_model():
    k = get_kernel("datalog@1")
    p = k.project(world(), KernelRequest(params={"rules": ANCESTRY}))
    r = k.run(p, KernelRequest())
    assert r.ok
    assert {c.predicate for c in r.claims} == {"ancestor"}, (
        "the input facts came back as if the kernel had derived them")
    assert r.diagnostics["derived"] == len(r.claims)
    assert r.cost.cpu_ns > 0 and r.cost.wall_ns > 0
    assert r.cost.usd is not None and r.cost.usd > 0, (
        "the kernel did not price itself, so every ledger above it "
        "would read it as free")


def test_a_derived_predicate_gets_positional_roles_unless_named():
    """A predicate the rules invent never had role names. Saying arg0/arg1 is
    honest; inventing plausible ones would not be."""
    k = get_kernel("datalog@1")
    p = k.project(world(), KernelRequest(params={"rules": ANCESTRY}))
    r = k.run(p, KernelRequest())
    assert all(set(c.roles) == {"arg0", "arg1"} for c in r.claims)

    named = k.project(world(), KernelRequest(params={
        "rules": ANCESTRY, "role_names": {"ancestor": ["descendant", "of"]}}))
    r2 = k.run(named, KernelRequest())
    assert all(set(c.roles) == {"descendant", "of"} for c in r2.claims)
    assert all(isinstance(v, EntityRef) for c in r2.claims
               for v in c.roles.values())


def test_derived_claims_carry_the_kernels_provenance():
    k = get_kernel("datalog@1")
    p = k.project(world(), KernelRequest(params={"rules": ANCESTRY}))
    c = k.run(p, KernelRequest()).claims[0]
    assert c.provenance.producer == "datalog@1"
    assert "closed world" in c.provenance.method


def test_a_kernel_with_no_rules_refuses_rather_than_returning_nothing():
    k = get_kernel("datalog@1")
    r = k.run(k.project(world(), KernelRequest()), KernelRequest())
    assert not r.ok and "no rules" in r.refused
    assert r.delta.is_empty()


def test_the_delta_applies_without_touching_the_world():
    w = world()
    before = w.to_dict()
    k = get_kernel("datalog@1")
    r = k.run(k.project(w, KernelRequest(params={"rules": ANCESTRY})),
              KernelRequest())
    after = r.delta.apply(w)
    assert w.to_dict() == before
    assert len(after.claims) == len(w.claims) + len(r.claims)


def test_run_delta_computes_only_the_consequences_of_the_delta():
    from symbolic_ai_core.world import WorldDelta

    k = get_kernel("datalog@1")
    p = k.project(world(), KernelRequest(params={"rules": ANCESTRY}))
    full = k.run(p, KernelRequest())

    delta = WorldDelta(
        entities=(Entity("d", types=("person",)),),
        claims=(Claim("parent", {"child": EntityRef("d"),
                                 "of": EntityRef("c")}),))
    r = k.run_delta(p, delta)
    assert r.ok
    assert r.diagnostics["recomputed_from_scratch"] is False
    derived = {tuple([c.predicate] + [getattr(v, "id", v)
                                      for v in c.roles.values()])
               for c in r.claims}
    assert ("ancestor", "d", "c") in derived
    assert ("ancestor", "d", "a") in derived, "the closure did not extend"
    assert not (derived & {tuple([c.predicate] + [getattr(v, "id", v)
                                                  for v in c.roles.values()])
                           for c in full.claims}), (
        "the incremental run re-derived what the full run already had")


def test_run_delta_covers_the_entities_the_delta_introduced():
    """Projecting the delta through the same P_K is what earns this. Handing
    raw tuples over would let a fact about an unprojected entity through."""
    from symbolic_ai_core.world import WorldDelta

    k = get_kernel("datalog@1")
    p = k.project(world(), KernelRequest(params={"rules": ANCESTRY}))
    assert not p.covers("d")
    delta = WorldDelta(entities=(Entity("d"),),
                       claims=(Claim("parent", {"child": EntityRef("d"),
                                                "of": EntityRef("c")}),))
    r = k.run_delta(p, delta)
    assert all(isinstance(v, EntityRef) for c in r.claims
               for v in c.roles.values()), (
        "a new entity came back as a bare string rather than a reference")


def test_run_delta_discards_what_the_delta_could_not_carry():
    from symbolic_ai_core.world import WorldDelta

    k = get_kernel("datalog@1")
    p = k.project(world(), KernelRequest(params={"rules": ANCESTRY}))
    delta = WorldDelta(claims=(
        Claim("parent", {"child": EntityRef("d"), "of": EntityRef("c")},
              modality="hypothesised"),))
    r = k.run_delta(p, delta)
    assert r.diagnostics["new_facts"] == 0
    assert r.diagnostics["discarded"] > len(p.discarded)


def test_the_manifest_says_it_does_not_adjudicate():
    m = get_kernel("datalog@1").manifest
    assert m.authority["derived_fact"] == "propose"
    assert m.incremental and m.runtime == "native" and m.dependencies == ()


def test_run_delta_prices_the_base_evaluation_it_performs():
    """The reported cost must cover the work actually done.

    An earlier version timed only the incremental step while recomputing the
    base model underneath it in the same call, so an O(model) invocation
    reported an O(delta) price -- measured at 5.3 ms against 213.7 ms of real
    work on a 120-node chain, a 40x understatement.
    """
    from symbolic_ai_core.world import Entity, WorldDelta
    from symbolic_ai_kernels.datalog import evaluate

    n = 120
    w = WorldSnapshot(
        entities={f"e{i}": Entity(f"e{i}") for i in range(n)},
        claims=tuple(Claim("par", {"a": EntityRef(f"e{i}"),
                                   "b": EntityRef(f"e{i+1}")})
                     for i in range(n - 1)))
    k = get_kernel("datalog@1")
    rules = [Rule(Atom("anc", (X, Y)), (Literal(Atom("par", (X, Y))),)),
             Rule(Atom("anc", (X, Z)), (Literal(Atom("par", (X, Y))),
                                        Literal(Atom("anc", (Y, Z)))))]
    p = k.project(w, KernelRequest(params={"rules": rules}))
    delta = WorldDelta(entities=(Entity("x9"),),
                       claims=(Claim("par", {"a": EntityRef("x9"),
                                             "b": EntityRef("e0")}),))

    cold = k.run_delta(p, delta)
    warm = k.run_delta(p, delta,
                       known=evaluate(p.program.program, p.program.facts))

    assert cold.diagnostics["base_recomputed"] is True
    assert warm.diagnostics["base_recomputed"] is False
    assert cold.cost.cpu_ns > 5 * warm.cost.cpu_ns, (
        "recomputing the base model cost the same as not recomputing it, so "
        "the price is not covering the work")
    def facts(result):
        return {(c.predicate, tuple(sorted((k, v.id) for k, v in c.roles.items())))
                for c in result.claims}

    assert facts(cold) == facts(warm), (
        "the cached path and the recomputing path disagreed about the answer")
