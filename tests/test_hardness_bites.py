"""Which of our instances actually need search, and for what.

Flood's decision is a widest path and solvency's is a sum against a threshold,
both polynomial. Scheduling is the one domain whose decision is genuinely
NP-hard -- and "NP-hard in principle" is not "hard on this distribution", so the
distribution is what these check.

Both halves of the polynomial procedure are ONE-SIDED SOUND, which is what makes
the inconclusive band meaningful rather than a measure of a weak heuristic.
"""

from __future__ import annotations

import sys

from symbolic_ai_generators.scheduling import generate
from symbolic_ai_generators.scheduling.ops import capacity_gate

sys.path.insert(0, "scripts")
from does_hardness_bite import greedy_feasible  # noqa: E402

N = 40


def test_greedy_success_is_never_wrong() -> None:
    """It exhibits an assignment, so success proves feasibility."""
    for seed in range(N):
        for slack in (0.02, 0.15, 0.40):
            case = generate(seed, n_jobs=6, n_machines=3, slack=slack)
            if greedy_feasible(case.jobs, case.machines):
                assert case.feasible, (seed, slack)


def test_the_capacity_gate_is_never_wrong() -> None:
    """Total demand above total capacity is infeasible whatever the packing."""
    for seed in range(N):
        for slack in (-0.10, -0.02, 0.02, 0.15):
            case = generate(seed, n_jobs=6, n_machines=3, slack=slack)
            need_search, _ = capacity_gate(case.world)
            if not need_search:
                assert not case.feasible, (seed, slack)


def test_greedy_finds_nearly_every_feasible_instance() -> None:
    """The claim that makes the band an INFEASIBILITY band rather than a
    weak-heuristic band."""
    feasible = found = 0
    for seed in range(N):
        for slack in (0.05, 0.15, 0.40):
            case = generate(seed, n_jobs=6, n_machines=3, slack=slack)
            if case.feasible:
                feasible += 1
                found += greedy_feasible(case.jobs, case.machines)
    assert feasible > 10, feasible
    assert found / feasible > 0.8, (found, feasible)


def test_search_is_still_needed_at_the_default() -> None:
    """If the polynomial pair settled everything, scheduling would be as
    decorative as flood and the suite would have no hard domain at all."""
    settled = 0
    for seed in range(N):
        case = generate(seed, n_jobs=6, n_machines=3, slack=0.15)
        need_search, _ = capacity_gate(case.world)
        settled += (not need_search) or greedy_feasible(case.jobs,
                                                        case.machines)
    assert settled / N < 0.6, settled / N
