"""SMT: the projection that picks up exactly what datalog throws away.

The clearest demonstration in the repo that there is no universal inference
language. Datalog discards a claim whose role is a ``Quantity``, because
projecting it would drop the unit; SMT exists precisely for those claims. One
world, two projections, disjoint strengths, and neither is the world.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.world import (Claim, Entity, EntityRef, Facet, Quantity,
                                    WorldSnapshot)
from symbolic_ai_kernels import KernelRequest, get_kernel
from symbolic_ai_kernels.smt import (UnitError, div, mul, parse_unit,
                                     project_world, same, unit_of)

z3 = pytest.importorskip("z3")

K = get_kernel("smt@1")


def robot() -> WorldSnapshot:
    return WorldSnapshot(entities={
        "robot": Entity("robot", facets={"logic.constraint": Facet(
            "logic.constraint", {"variables": {"payload": {"unit": "kg"}}})}),
    }, claims=(Claim("mass", {"of": EntityRef("robot"),
                              "value": Quantity(14.0, "kg")}),))


def under_20kg():
    return [{"op": "<=", "args": [
        {"op": "+", "args": [{"var": "mass@robot"}, {"var": "payload@robot"}]},
        {"q": {"value": 20, "unit": "kg"}}]}]


# --- the unit algebra -----------------------------------------------------
def test_units_compose_and_round_trip():
    assert parse_unit("kg*m/s/s") == parse_unit(div(div("kg*m", "s"), "s"))
    assert mul("kg/s", "s") == "kg"
    assert parse_unit("1/s") == parse_unit(div("1", "s"))
    assert parse_unit("1") == parse_unit("")


def test_a_dimensional_mismatch_names_both_sides():
    with pytest.raises(UnitError, match="kg beside m"):
        same("kg", "m", where="the comparison <")


def test_there_is_deliberately_no_conversion_table():
    with pytest.raises(UnitError, match="no conversion table"):
        same("m", "ft")


# --- the projection -------------------------------------------------------
def test_the_projection_reads_the_claims_datalog_discards():
    from symbolic_ai_kernels.datalog import project_world as project_relational

    w = robot()
    rel = project_relational(w)
    assert any(d.kind == "claim" and "Quantity" in d.why for d in rel.discarded)
    smt = project_world(w)
    assert smt.covered_claims == (0,), "SMT did not pick up the mass claim"
    assert smt.program.variables["mass@robot"].fixed == 14.0
    assert smt.program.variables["mass@robot"].unit == "kg"


def test_a_dimensional_mismatch_is_a_refusal_not_a_discard():
    """A malformed question, not an unrepresentable part of the world."""
    with pytest.raises(UnitError):
        K.project(robot(), KernelRequest(params={"constraints": [
            {"op": "<", "args": [{"var": "mass@robot"},
                                 {"q": {"value": 2, "unit": "m"}}]}]}))


def test_a_free_variable_is_refused():
    with pytest.raises(UnitError, match="which nothing declared"):
        unit_of({"op": "<", "args": [{"var": "ghost"},
                                     {"q": {"value": 1, "unit": "kg"}}]}, {})


def test_a_hypothesised_quantity_does_not_become_a_measurement():
    w = WorldSnapshot(
        entities={"r": Entity("r")},
        claims=(Claim("mass", {"of": EntityRef("r"),
                               "value": Quantity(9.0, "kg")},
                      modality="hypothesised"),))
    p = project_world(w)
    assert p.covered_claims == ()
    assert any("not a measurement" in d.why for d in p.discarded)


def test_a_stderr_is_recorded_as_a_loss_not_silently_dropped():
    w = WorldSnapshot(entities={"r": Entity("r")},
                      claims=(Claim("mass", {"of": EntityRef("r"),
                                             "value": Quantity(9.0, "kg", 0.4)}),))
    p = project_world(w)
    assert any(d.kind == "uncertainty" and "0.4" in d.why for d in p.discarded)
    assert p.program.variables["mass@r"].fixed == 9.0


def test_an_ambiguous_claim_shape_is_discarded_rather_than_guessed():
    w = WorldSnapshot(
        entities={"a": Entity("a"), "b": Entity("b")},
        claims=(Claim("distance", {"from": EntityRef("a"), "to": EntityRef("b"),
                                   "value": Quantity(3.0, "m")}),))
    p = project_world(w)
    assert p.covered_claims == ()
    assert any("guessing which is which" in d.why for d in p.discarded)


# --- solving --------------------------------------------------------------
def test_a_satisfying_model_comes_back_with_units():
    req = KernelRequest(params={"constraints": under_20kg() + [
        {"op": ">=", "args": [{"var": "payload@robot"},
                              {"q": {"value": 3, "unit": "kg"}}]}]})
    r = K.run(K.project(robot(), req), req)
    assert r.ok and r.diagnostics["satisfiable"]
    payload = next(c for c in r.claims if c.predicate == "payload")
    q = payload.roles["value"]
    assert isinstance(q, Quantity) and q.unit == "kg"
    assert 3.0 <= q.value <= 6.0


def test_a_witness_is_not_a_measurement():
    req = KernelRequest(params={"constraints": under_20kg()})
    r = K.run(K.project(robot(), req), req)
    assert all(c.modality == "possible" for c in r.claims)
    assert r.delta.is_empty(), "a satisfying witness was written into the world"
    assert "not a measurement" in r.claims[0].provenance.method


def test_a_measured_quantity_is_not_re_reported_as_a_witness():
    req = KernelRequest(params={"constraints": under_20kg()})
    r = K.run(K.project(robot(), req), req)
    assert {c.predicate for c in r.claims} == {"payload"}, (
        "the measured mass came back as if the solver had chosen it")


def test_unsat_says_it_is_about_the_projection():
    req = KernelRequest(params={"constraints": [
        {"op": ">", "args": [{"var": "mass@robot"},
                             {"q": {"value": 100, "unit": "kg"}}]}]})
    r = K.run(K.project(robot(), req), req)
    assert not r.ok
    assert "unsat" in r.refused and "PROJECTION" in r.refused
    assert r.diagnostics["satisfiable"] is False


def test_no_constraints_is_a_refusal():
    r = K.run(K.project(robot(), KernelRequest()), KernelRequest())
    assert not r.ok and "no constraints" in r.refused


def test_an_unsat_is_a_veto_and_a_witness_is_not():
    a = K.manifest.authority
    assert a["constraint_violation"] == "veto"
    assert a["witness_value"] == "propose"


def test_the_manifest_declares_an_external_dependency():
    assert K.manifest.runtime == "external"
    assert K.manifest.dependencies == ("z3-solver>=4.13",)
    assert set(K.manifest.semantics) == {"classical", "constraint"}


# --- the budget, and the outcomes it makes distinguishable -----------------
def _wide_system(n: int = 300, ratio: float = 6.0, seed: int = 1):
    """A system large enough that z3 takes real time to settle it."""
    import random
    rng = random.Random(seed)
    names = [f"x{i}" for i in range(n)]
    cons = [{"op": ">=", "args": [
        {"op": "+", "args": [{"var": f"{l}@sat"}
                             for l in rng.sample(names, 3)]},
        {"q": {"value": 1, "unit": "1"}}]} for _ in range(int(n * ratio))]
    w = WorldSnapshot(entities={"sat": Entity("sat", facets={
        "logic.constraint": Facet("logic.constraint",
                                  {"variables": {m: {"unit": "1"}
                                                 for m in names}})})})
    return w, cons


def test_a_small_budget_is_exhausted_rather_than_refused():
    """The distinction the ABI could not express: a planner must tell "ran out
    of time" from "cannot be done" -- one is retryable and the other is waste.

    `budget_ns` was declared on KernelRequest when the ABI was written and read
    by nothing in the repo until now.
    """
    w, cons = _wide_system()
    req = KernelRequest(params={"constraints": cons}, budget_ns=1_000_000)
    r = K.run(K.project(w, req), req)
    assert r.exhausted and r.retryable
    assert not r.conclusive, "nothing was established"
    assert "retryable" in r.refused


def test_the_same_system_settles_when_the_budget_is_lifted():
    """Which is what makes the previous result a statement about the budget
    and not about the problem."""
    w, cons = _wide_system()
    req = KernelRequest(params={"constraints": cons})
    r = K.run(K.project(w, req), req)
    assert r.conclusive and not r.exhausted


def test_an_unsat_is_a_proof_not_a_refusal():
    """Reporting a proof of infeasibility as a failure reads the most valuable
    thing a solver says as the least."""
    req = KernelRequest(params={"constraints": [
        {"op": "<=", "args": [{"var": "mass@robot"},
                              {"q": {"value": 1, "unit": "kg"}}]}]})
    r = K.run(K.project(robot(), req), req)
    assert r.proved_impossible
    assert r.conclusive, "unsat settles the question"
    assert not r.ok, "and ok keeps its old meaning: no positive answer"
    assert not r.retryable, "more budget will not make it satisfiable"


def test_a_unit_mismatch_never_reaches_the_budget_at_all():
    """Units are checked at projection, so comparing kilograms to seconds
    fails before a solver is asked -- and therefore can never be mistaken for
    a budget exhaustion, which is the whole point of checking there."""
    req = KernelRequest(params={"constraints": [
        {"op": "<=", "args": [{"var": "mass@robot"},
                              {"q": {"value": 1, "unit": "s"}}]}]})
    with pytest.raises(UnitError):
        K.run(K.project(robot(), req), req)


def test_an_empty_system_is_refused_and_not_retryable():
    r = K.run(K.project(robot(), KernelRequest()), KernelRequest())
    assert not r.conclusive and not r.retryable and not r.exhausted


def test_ok_still_means_what_two_generators_read_it_to_mean():
    """`feasible = result.ok` appears in scheduling/ops.py and flood/ops.py and
    feeds published numbers. Widening ok to include proved_impossible would
    have inverted them silently."""
    req = KernelRequest(params={"constraints": under_20kg()})
    r = K.run(K.project(robot(), req), req)
    assert r.ok and r.conclusive and not r.proved_impossible


def test_a_kernel_that_sets_no_outcome_still_classifies():
    """Seven kernels predate this field and must keep working."""
    from symbolic_ai_kernels.abi import ANSWERED, REFUSED, KernelResult
    assert KernelResult(kernel="k").classification == ANSWERED
    assert KernelResult(kernel="k", refused="nope").classification == REFUSED
