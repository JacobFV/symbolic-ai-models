"""Machine assignment: the third task, built for the cell the first two miss.

flood has expensive kernels and a moderate margin; solvency has a tunable margin
and a pipeline 179x cheaper. This has both an expensive kernel (ASP searching
3^6 assignments, 99% of pipeline cost) and a margin knob, so the regime claims
can be tested where neither was measured.
"""

from __future__ import annotations

import pytest

from symbolic_ai_generators.scheduling import (CORRUPTIONS, corrupt,
                                               feasible_by_search, generate)
from symbolic_ai_generators.scheduling.ops import build_program, capacity_gate
from symbolic_ai_kernels import KernelRequest, get_kernel

pytest.importorskip("clingo")
ASP = get_kernel("asp@1")


def solve(world) -> bool:
    program, _ = build_program(world)
    request = KernelRequest(params={"program": program, "max_models": 1})
    return ASP.run(ASP.project(world, request), request).ok


# --- the task ------------------------------------------------------------
def test_generation_is_a_pure_function_of_its_seed():
    a, b = generate(9, slack=0.4), generate(9, slack=0.4)
    assert a.world.to_dict() == b.world.to_dict() and a.feasible == b.feasible


def test_the_slack_knob_moves_the_decision_margin():
    rates = [sum(generate(s, slack=k).feasible for s in range(120)) / 120
             for k in (0.0, 0.15, 0.5, 1.0)]
    assert rates == sorted(rates), f"feasibility not monotone in slack: {rates}"
    assert rates[0] < 0.1 and rates[-1] > 0.7, "the knob does not span regimes"


def test_asp_agrees_with_the_exhaustive_oracle():
    for s in range(40):
        c = generate(s, slack=0.5)
        assert solve(c.world) == c.feasible, c.seed


def test_the_oracle_is_exhaustive_rather_than_heuristic():
    """A heuristic that occasionally missed a feasible packing would be
    indistinguishable from a kernel bug."""
    import inspect

    from symbolic_ai_generators.scheduling import world as W

    src = inspect.getsource(W.feasible_by_search)
    assert "itertools.product" in src
    for forbidden in ("clingo", "get_kernel", "build_program", "asp@1"):
        assert forbidden not in src


def test_the_expensive_kernel_really_is_the_expensive_part():
    """The property that makes this task the missing cell."""
    from symbolic_ai_core.flow import (Binding, Context, FlowGraph, Node,
                                       evaluate)
    from symbolic_ai_core.flow import ops as _o
    from symbolic_ai_generators.scheduling import ops as _so
    from symbolic_ai_kernels import flow_ops as _k
    from symbolic_ai_kernels.flow_ops import world_artifact

    assert _o and _so and _k
    total = solve_cost = 0.0
    for s in range(20):
        g = FlowGraph(nodes=(
            Node(id="world", op="flow.const@1",
                 params={"artifact": world_artifact(generate(s, slack=0.5).world)}),
            Node(id="solve", op="scheduling.solve@1",
                 inputs={"world": Binding("world", "out")}),
        ), outputs={"claims": Binding("solve", "claims")})
        _, ctx = evaluate(g, ctx=Context())
        for r in ctx.trace.runs:
            total += r.cost_usd or 0.0
            if r.node == "solve":
                solve_cost += r.cost_usd or 0.0
    assert solve_cost / total > 0.8, (
        f"the solver is only {solve_cost / total:.0%} of the pipeline; this task "
        f"is supposed to have an expensive kernel")


# --- the provable gate ---------------------------------------------------
def test_the_capacity_gate_is_never_wrong():
    """Demand above capacity is infeasible whatever the assignment. A theorem,
    so it must hold at every slack and every N."""
    for slack in (-0.3, -0.05, 0.0, 0.15, 0.5, 1.0):
        for s in range(60):
            c = generate(s, slack=slack)
            if not capacity_gate(c.world)[0]:
                assert not c.feasible, (slack, c.seed)


def test_routing_headroom_is_a_function_of_the_margin():
    """The gate fires on everything below the boundary and nothing above it."""
    def fires(slack):
        return sum(1 for s in range(120)
                   if not capacity_gate(generate(s, slack=slack).world)[0]) / 120

    assert fires(-0.15) > 0.9, "the gate missed over-subscribed instances"
    assert fires(0.5) == 0.0 and fires(1.0) == 0.0, (
        "the gate fired where capacity is ample, so it is not the bound it "
        "claims to be")


def test_the_converse_is_not_a_gate():
    """Capacity to spare says nothing about whether the capabilities line up,
    so there is one gate here and not two."""
    spare = [c for c in (generate(s, slack=1.0) for s in range(200))
             if not c.feasible]
    assert spare, "no instance with ample capacity was infeasible"
    assert all(capacity_gate(c.world)[0] for c in spare)


# --- the regime boundary, on a task with an expensive kernel -------------
def _ratio(slack, n=120, rate=0.20):
    cs = [generate(s, slack=slack) for s in range(n)]
    d = sum(solve(corrupt(c, seed=i, rate=rate, kind="drop_job")) != c.feasible
            for i, c in enumerate(cs))
    m = sum(solve(corrupt(c, seed=i, rate=rate, kind="misread_duration"))
            != c.feasible for i, c in enumerate(cs))
    return d / n, m / n


def test_the_recall_precision_inversion_reproduces_with_an_expensive_kernel():
    """The solvency result was on a pipeline 179x cheaper with no search in it.
    If the boundary is really about the decision margin it must appear here too,
    and at comparable ratios.

      solvency:   2.28 at slack 0.10  ->  0.11 at slack 1.00
      scheduling: 2.38 at slack 0.15  ->  0.13 at slack 2.00
    """
    tight_d, tight_m = _ratio(0.15)
    loose_d, loose_m = _ratio(2.00)
    assert tight_d > tight_m, f"no recall dominance at a tight margin ({tight_d} vs {tight_m})"
    assert loose_m > loose_d, (
        f"the ordering did not invert at a large margin ({loose_m} vs "
        f"{loose_d}); the boundary is then not about the margin")
    assert loose_d < tight_d / 3


def test_every_corruption_channel_is_reachable():
    """A channel that never changes anything tests nothing."""
    c = generate(1, slack=0.15)
    for kind in CORRUPTIONS:
        changed = any(
            corrupt(c, seed=i, rate=0.9, kind=kind).to_dict()
            != c.world.to_dict() for i in range(5))
        assert changed, kind


# --- where the numbers enter --------------------------------------------
def test_the_projection_discards_the_numbers_the_program_smuggles_back():
    """Honest about the trade: the relational projection drops every Quantity,
    which is what makes it unit-safe, so durations reach the solver through the
    program text and are NOT unit-checked by it."""
    c = generate(2, slack=0.5)
    program, notes = build_program(c.world)
    assert notes, "no numeric fact entered outside the projection"
    p = ASP.project(c.world, KernelRequest(params={"program": program}))
    assert any("Quantity" in d.why for d in p.discarded)
    assert "duration(" in program, "the numbers did not reach the solver at all"


def test_a_duration_in_the_wrong_unit_is_refused_where_the_check_still_exists():
    from dataclasses import replace

    from symbolic_ai_core.world import Quantity, WorldSnapshot

    c = generate(2, slack=0.5)
    claims = []
    for cl in c.world.claims:
        if cl.predicate == "duration":
            q = cl.roles["value"]
            claims.append(replace(cl, roles={**cl.roles,
                                             "value": Quantity(q.value, "min")}))
        else:
            claims.append(cl)
    with pytest.raises(ValueError, match="not hours"):
        build_program(WorldSnapshot(entities=c.world.entities,
                                    claims=tuple(claims)))
