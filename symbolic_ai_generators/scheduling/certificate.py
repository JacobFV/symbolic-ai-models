"""Insensitivity on the channel with no arity and no second source.

`has_capability` is multi-valued -- a machine holds any number -- so nothing
corroborates it and the `evidence_conflict` family fires **0.000** there. It is
also the worst channel measured on 2026-08-19: one admitted sentence costs
**0.210** accuracy with every failure in the **unsound** direction, an infeasible
floor reading as feasible because the reader granted a machine a capability it
does not have.

Detection is not the only response. This asks whether the answer **depends** on
any single capability claim, under the hypothesis that **at most one is
spurious** -- the same bound flood's link certificate and solvency's membership
certificate carry.

Two halves, and only one of them costs anything:

- **monotone, free.** Deleting a ``has_capability`` can only make an instance
  *more* infeasible, so an **infeasible** reading cannot have been produced by a
  spurious capability. No solve.
- **feasible, k solves.** Re-solve with each capability deleted; certify iff the
  instance stays feasible under every single deletion.

This is the half of the certificate pattern that *did* transfer to scheduling.
The structural analogue -- "every job has two capable machines with room" -- was
measured unsound on 8 of the 9 instances it fired on, because two capable
machines guarantee the capability survives and say nothing about the packing.
"""

from __future__ import annotations

from dataclasses import replace

__all__ = ["certifies_capability_insensitive"]


def certifies_capability_insensitive(world, solve) -> tuple[bool, int]:
    """``(certified, solves_spent)`` under at-most-one-spurious-capability.

    ``solve`` takes a world and returns the feasibility verdict first, matching
    `scripts/hard_regime_milestone.solve_world`.

    Sound for that hypothesis and **conditional on the rest of the reading**: it
    says nothing about a spurious ``needs_capability``, a wrong duration or a
    wrong capacity. That conditional is the whole content of the fifth appearance
    of *a check that reads part of the world inherits that part's errors*, and it
    is stated here rather than left to the name.
    """
    base = solve(world)[0]
    if base is None:
        return False, 1
    if not base:
        return True, 1                    # monotone: deletion cannot rescue it

    caps = [i for i, c in enumerate(world.claims)
            if c.predicate == "has_capability"]
    spent = 1
    for i in caps:
        without = replace(world, claims=tuple(
            c for j, c in enumerate(world.claims) if j != i))
        spent += 1
        if solve(without)[0] is not True:
            return False, spent
    return True, spent
