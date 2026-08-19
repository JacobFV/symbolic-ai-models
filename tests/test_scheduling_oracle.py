"""The pruned feasibility oracle against the brute force it replaced.

``feasible_by_search`` decides ground truth for every scheduling case, so a
wrong answer there is indistinguishable from a kernel bug -- which is why the
brute force is kept as an executable specification rather than deleted. These
tests bind the two on every instance small enough to enumerate.

The pruning exists because the oracle *was* the cost of this domain: 53.1s on a
single 18-job instance, against milliseconds for the ASP kernel on the same
world. See ``feasible_by_search``'s docstring.
"""

from __future__ import annotations

import time

import pytest

from symbolic_ai_generators.scheduling.world import (CAPABILITIES,
                                                     feasible_by_brute_force,
                                                     feasible_by_search,
                                                     generate)


def _instance(seed: int, n_jobs: int, n_machines: int, slack: float):
    case = generate(seed, n_jobs=n_jobs, n_machines=n_machines, slack=slack)
    return case.jobs, case.machines


@pytest.mark.parametrize("n_jobs", [1, 2, 3, 5, 8])
@pytest.mark.parametrize("slack", [-0.30, -0.02, 0.0, 0.05, 0.40])
def test_agrees_with_brute_force(n_jobs: int, slack: float) -> None:
    """Same verdict as the specification, over both sides of the boundary."""
    for seed in range(6):
        jobs, machines = _instance(seed, n_jobs, 3, slack)
        assert feasible_by_search(jobs, machines) == \
            feasible_by_brute_force(jobs, machines), (n_jobs, slack, seed)


@pytest.mark.parametrize("n_machines", [1, 2, 4])
def test_agrees_across_machine_counts(n_machines: int) -> None:
    """Symmetry breaking keys on capability sets, so vary how many exist."""
    for seed in range(8):
        jobs, machines = _instance(seed, 6, n_machines, -0.02)
        assert feasible_by_search(jobs, machines) == \
            feasible_by_brute_force(jobs, machines), (n_machines, seed)


def test_both_verdicts_actually_occur() -> None:
    """A test that only ever saw one answer would pass on ``return False``."""
    seen = set()
    for slack in (-0.30, 0.60):
        for seed in range(8):
            jobs, machines = _instance(seed, 5, 3, slack)
            seen.add(feasible_by_search(jobs, machines))
    assert seen == {True, False}, seen


def test_unplaceable_capability_is_infeasible() -> None:
    """The one cut that is not about capacity: no machine can do the job."""
    jobs = {"job_0": (1.0, "weld")}
    machines = {"machine_0": (100.0, ("cut",))}
    assert feasible_by_search(jobs, machines) is False
    assert feasible_by_brute_force(jobs, machines) is False


def test_exact_fit_is_feasible() -> None:
    """The boundary itself: zero slack must not be lost to the tolerance."""
    jobs = {"job_0": (2.0, "cut"), "job_1": (3.0, "cut")}
    machines = {"machine_0": (5.0, ("cut",))}
    assert feasible_by_search(jobs, machines) is True


def test_one_hour_over_is_infeasible() -> None:
    jobs = {"job_0": (2.0, "cut"), "job_1": (3.01, "cut")}
    machines = {"machine_0": (5.0, ("cut",))}
    assert feasible_by_search(jobs, machines) is False


def test_capability_forces_the_split() -> None:
    """Capacity alone would fit; capabilities are what decide it."""
    jobs = {"job_0": (4.0, "cut"), "job_1": (4.0, "weld")}
    machines = {"machine_0": (8.0, ("cut",)), "machine_1": (4.0, ("weld",))}
    assert feasible_by_search(jobs, machines) is True
    jobs["job_1"] = (5.0, "weld")
    assert feasible_by_search(jobs, machines) is False


def test_the_oracle_is_no_longer_the_bottleneck() -> None:
    """The regression this whole change exists to stop.

    Seed 1 at 18 jobs took 53.1 seconds before pruning. A generous ceiling here
    still fails by three orders of magnitude if the brute force comes back.
    """
    t0 = time.perf_counter()
    for seed in range(3):
        generate(seed, n_jobs=18, n_machines=3, slack=-0.02)
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0, f"generating 3 18-job cases took {elapsed:.1f}s"


def test_capabilities_are_what_the_oracle_reads() -> None:
    """Guards the assumption the symmetry key rests on."""
    assert set(CAPABILITIES) == {"cut", "paint", "weld"}
