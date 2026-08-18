"""The first task in this repo that three kernels solve and none of them can.

This is the gate the architecture note set: at least two kernels operating on
overlapping profiles of one entity, one kernel's output changing another's
through explicit coupling, every output arising from one flow DAG, and a task
that cannot be answered by copying from the text.

The agreement number is measured against a **brute-force oracle that shares no
code with the kernels**. An oracle built from the same machinery would agree by
construction, which is the same defect as a floor fitted with the model's own
features.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.flow import Context, FlowError, compile_flow
from symbolic_ai_generators.flood import generate, solution_by_search
from symbolic_ai_generators.flood.flow import build_flow, solve

pytest.importorskip("clingo")
pytest.importorskip("z3")

#: Small enough to stay a unit test, large enough that agreement is not luck.
SEEDS = range(24)


@pytest.fixture(scope="module")
def cases():
    return [generate(s) for s in SEEDS]


# --- the gate -------------------------------------------------------------
def test_the_whole_task_is_one_acyclic_flow_graph(cases):
    compiled = compile_flow(build_flow(cases[0].world))
    assert compiled.order[0] == "world"
    assert set(compiled.order) == {"world", "reach", "world2", "routes",
                                   "loads", "fused"}


def test_the_world_it_reasons_about_is_cyclic(cases):
    """The thing the flow DAG refuses and the world IR exists to hold."""
    c = cases[0]
    ring = {tuple(sorted((c.regions[i], c.regions[(i + 1) % len(c.regions)])))
            for i in range(len(c.regions))}
    assert ring <= set(c.links), "the road network is not a ring"
    assert c.world.neighbours(c.regions[0]), "no relations to traverse"


def test_three_kernels_run_and_each_does_something_the_others_cannot(cases):
    _, outs, _ = solve(cases[0].world)
    dl = outs["projection_datalog"].value
    asp = outs["projection_asp"].value
    assert dl["kernel"] == "datalog@1" and asp["kernel"] == "asp@1"
    # datalog discards exactly what SMT is for
    assert any("Quantity" in d["why"] for d in dl["discarded"]), (
        "the relational projection kept the load limits, so SMT is redundant")
    assert outs["load_report"].value["n_smt_calls"] > 0


def test_kernels_share_profiles_on_one_entity(cases):
    """A vehicle carries scene.body for the physical view and logic.constraint
    for the solver view, on one identity, without duplication."""
    truck = cases[0].world.entity("truck_0")
    assert truck.has("scene.body", "logic.constraint")
    assert truck.profiles() == ("logic.constraint", "scene.body")


def test_the_coupling_is_real_datalog_to_asp(cases):
    """Removing datalog's contribution changes ASP's answer set, which is what
    'one kernel's output changes another kernel's result' means."""
    changed = 0
    for c in cases:
        full, _, _ = solve(c.world)
        ablated, _, _ = solve(c.world, ignore_flooding=True)
        changed += full != ablated
    assert changed > 0, "routing over raw links gave the same answer every time"


def test_the_coupling_is_real_asp_to_smt(cases):
    """The SMT constraints are built from ASP's routes: keeping only the first
    route changes the answer, so the route set is load-bearing."""
    changed = sum(solve(c.world)[0] != solve(c.world, first_route_only=True)[0]
                  for c in cases)
    assert changed > 0


# --- the number -----------------------------------------------------------
def test_the_flow_agrees_with_an_independent_brute_force_oracle(cases):
    disagree = [(c.seed, solve(c.world)[0], c.answer) for c in cases
                if solve(c.world)[0] != c.answer]
    assert not disagree, disagree


def test_the_oracle_shares_no_code_with_the_kernels(cases):
    """Guards the test above from being a tautology."""
    import inspect

    from symbolic_ai_generators.flood import world as W
    src = inspect.getsource(W.solution_by_search) + inspect.getsource(W._routes)
    for forbidden in ("clingo", "z3", "datalog", "get_kernel", "evaluate("):
        assert forbidden not in src, f"the oracle reaches for {forbidden}"


def test_every_ablation_is_worse_than_the_whole(cases):
    def acc(**kw):
        return sum(solve(c.world, **kw)[0] == c.answer for c in cases) / len(cases)

    full = acc()
    assert full == 1.0
    assert acc(ignore_bridge_limits=True) < full
    assert acc(ignore_flooding=True) < full
    assert acc(first_route_only=True) < full


def test_the_best_floor_is_well_below_the_flow(cases):
    """The strongest non-reasoning rule available: capacity plus the laden mass
    against the *most permissive* bridge, ignoring the network entirely."""
    def floor(c):
        return tuple(sorted(
            v for v, (m, cap) in c.vehicles.items()
            if cap >= c.demand_kg and m + c.demand_kg <= max(c.bridges.values())))

    hit = sum(floor(c) == c.answer for c in cases) / len(cases)
    assert hit < 0.75, f"the floor scores {hit}; the task has little in it"


# --- what the text does and does not say ---------------------------------
def test_the_report_never_states_the_answer(cases):
    for c in cases:
        for vid in c.vehicles:
            assert f"{vid} can" not in c.report
            assert f"dispatch {vid}" not in c.report.lower()
        assert "can_serve" not in c.report


def test_the_deciding_facts_are_in_different_paragraphs(cases):
    """No single paragraph contains flooding, limits and masses together."""
    for c in cases[:4]:
        for para in c.report.split("\n\n"):
            has_flood = "closed" in para
            has_limit = "posted at" in para
            has_mass = "unladen mass" in para
            assert sum((has_flood, has_limit, has_mass)) <= 1


# --- honesty of the trace -------------------------------------------------
def test_the_trace_reports_every_node_as_unpriced_rather_than_free(cases):
    _, _, ctx = solve(cases[0].world, ctx=Context())
    assert len(ctx.trace.runs) == 6
    assert ctx.trace.total_usd == 0.0
    assert ctx.trace.unpriced == 6, (
        "a node that reported no cost was counted as free")


def test_re_running_the_same_case_hits_the_cache(cases):
    ctx = Context()
    solve(cases[0].world, ctx=ctx)
    n = len(ctx.trace.runs)
    solve(cases[0].world, ctx=ctx)
    second = ctx.trace.runs[n:]
    assert all(r.cached for r in second), "an unchanged graph recomputed"


def test_generation_is_a_pure_function_of_its_seed():
    a, b = generate(7), generate(7)
    assert a.world.to_dict() == b.world.to_dict()
    assert a.report == b.report and a.answer == b.answer


def test_the_oracle_is_not_degenerate(cases):
    sizes = {len(c.answer) for c in cases}
    assert len(sizes) >= 3, f"the answer takes only {sizes}; no signal"
