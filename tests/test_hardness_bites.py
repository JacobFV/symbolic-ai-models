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


def test_the_hard_regime_is_not_gate_settleable() -> None:
    """The point of the constant. At negative slack the capacity gate fires on
    everything, and those are exactly the cells where clingo is slowest -- so a
    hard regime chosen there would measure work nobody needs to do."""
    from symbolic_ai_generators.scheduling import HARD_REGIME, generate_hard

    fired = sum(not capacity_gate(generate_hard(s).world)[0] for s in range(20))
    assert fired < 14, f"gate settles {fired}/20 of the hard regime"

    negative = sum(not capacity_gate(
        generate(s, **{**HARD_REGIME, "slack": -0.02}).world)[0]
        for s in range(20))
    assert negative == 20, negative


def test_the_hard_regime_keeps_ground_truth_affordable() -> None:
    """It sits at exact fit, where the oracle's capacity bound stops pruning.
    20 jobs is affordable and 30 is not -- see HARD_REGIME."""
    import time

    from symbolic_ai_generators.scheduling import generate_hard

    t0 = time.perf_counter()
    for seed in range(3):
        generate_hard(seed)
    assert time.perf_counter() - t0 < 2.0


def test_the_capacity_gate_is_sound_at_exact_fit() -> None:
    """The regression this gate's float comparison caused.

    At HARD_REGIME total demand equals total capacity by construction, and
    summation order made demand exceed capacity by 1.4e-14 on 4 of 30 instances
    -- so a gate documented as "provably sufficient" refused schedules that
    provably exist. It now sums in integer centihours, the same units
    ``build_program`` uses.

    A one-sided check that is sometimes wrong is worse than no check, because
    everything downstream trusts it.
    """
    from symbolic_ai_generators.scheduling import generate_hard

    for seed in range(30):
        case = generate_hard(seed)
        need_search, _ = capacity_gate(case.world)
        if not need_search:
            assert not case.feasible, (seed, "gate refused a feasible schedule")


def test_the_gate_still_fires_where_it_should() -> None:
    """The fix must not silence it: below the boundary it still settles."""
    from symbolic_ai_generators.scheduling import HARD_REGIME

    fired = sum(not capacity_gate(
        generate(s, **{**HARD_REGIME, "slack": -0.02}).world)[0]
        for s in range(20))
    assert fired == 20, fired
