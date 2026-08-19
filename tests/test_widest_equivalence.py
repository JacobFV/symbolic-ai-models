"""Flood's three-kernel flow computes a widest path.

Measured over 200 cases. This is not a proposal to replace the flow -- the flow
is the system under study and its numbers are the published ones -- but the
equivalence is load-bearing for how those numbers should be read, so it is
pinned.
"""

from __future__ import annotations

import pytest

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.widest import bottleneck, widest_answer


@pytest.mark.parametrize("lo,hi", [(0, 40), (100, 140)])
def test_widest_path_reproduces_the_flow(lo: int, hi: int) -> None:
    for seed in range(lo, hi):
        case = generate(seed)
        assert widest_answer(case.world) == solve(case.world)[0], seed


def test_it_calls_no_kernel() -> None:
    """Its whole point is being polynomial and cheap."""
    import inspect

    from symbolic_ai_generators.flood import widest

    src = inspect.getsource(widest)
    for forbidden in ("get_kernel", "solve(", "evaluate(", "KernelRequest"):
        assert forbidden not in src, forbidden


def test_flooding_and_limits_both_bind() -> None:
    """A control: the equivalence must not hold because both sides ignore the
    hard parts. Flooding and bridge limits have to change the bottleneck."""
    seen_flood = seen_limit = False
    for seed in range(60):
        case = generate(seed)
        w = bottleneck(case.world)
        no_flood = tuple(c for c in case.world.claims
                         if c.predicate != "flooded")
        from dataclasses import replace
        if bottleneck(replace(case.world, claims=no_flood)) != w:
            seen_flood = True
        no_lim = tuple(c for c in case.world.claims
                       if c.predicate != "load_limit")
        if bottleneck(replace(case.world, claims=no_lim)) != w:
            seen_limit = True
    assert seen_flood, "flooding never changed the bottleneck"
    assert seen_limit, "bridge limits never changed the bottleneck"
