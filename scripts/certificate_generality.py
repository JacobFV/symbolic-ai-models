"""Does the certificate pattern transfer, and which half of it?

The flood certificate replaced sixteen flow solves with one DFS and made
soundness free. That finding claimed the pattern is *not flood-specific* on the
strength of one instance, which is the generality-from-one-case error this thread
has already made three times. So: test it.

The pattern has two ingredients.

1. **Monotonicity** -- the perturbation moves the answer one way only, so half
   the objects are safe with no work.
2. **A cheap structural invariant** standing in for the expensive computation --
   for flood, 2-edge-connectivity for "a route survives".

Scheduling separates them. It **has** monotonicity: deleting a ``has_capability``
claim removes assignments and never adds one, so an infeasible instance stays
infeasible. It plausibly **lacks** the invariant, because feasibility here is
bin-packing with capability constraints and has no polynomial characterisation of
"a feasible assignment survives deleting any one claim".

If that is right, the pattern's reach is set by the complexity of the underlying
decision rather than by anything about readers or ambiguity.

Run: uv run python -u scripts/certificate_generality.py
"""

from __future__ import annotations

import json
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_core.world import Quantity
from symbolic_ai_generators.scheduling import generate
from symbolic_ai_generators.scheduling.world import feasible_by_search

OUT = Path("runs/certificate_generality.json")
N = 60
KIND = "has_capability"


def answer(world) -> bool | None:
    jobs, machines, needs, has = {}, {}, {}, {}
    for c in world.claims:
        q = c.roles.get("value")
        if c.predicate == "duration" and isinstance(q, Quantity):
            jobs[c.roles["of"].id] = q.value
        elif c.predicate == "capacity" and isinstance(q, Quantity):
            machines[c.roles["of"].id] = q.value
        elif c.predicate == "needs_capability":
            needs[c.roles["job"].id] = str(c.roles["capability"])
        elif c.predicate == "has_capability":
            has.setdefault(c.roles["machine"].id, []).append(
                str(c.roles["capability"]))
    if not jobs or not machines:
        return None
    J = {j: (v, needs.get(j, "")) for j, v in jobs.items()}
    M = {m: (v, tuple(sorted(has.get(m, [])))) for m, v in machines.items()}
    return feasible_by_search(J, M)


def monotone_certificate(world) -> bool:
    """Infeasible is safe for free: deleting a capability cannot create one.

    The exact analogue of flood's non-qualifying vehicles, and the half of the
    pattern that needs no structural invariant at all.
    """
    return answer(world) is False


def structural_attempt(world) -> bool:
    """A cheap sufficient condition for FEASIBLE instances, attempted.

    "Every job has at least two machines that are capable of it and could hold
    it alone" -- the closest analogue to two edge-disjoint routes. It is
    genuinely sufficient for the *capability* half and says nothing about
    whether the packing still fits, which is where bin-packing bites.
    """
    jobs, machines, needs, has = {}, {}, {}, {}
    for c in world.claims:
        q = c.roles.get("value")
        if c.predicate == "duration" and isinstance(q, Quantity):
            jobs[c.roles["of"].id] = q.value
        elif c.predicate == "capacity" and isinstance(q, Quantity):
            machines[c.roles["of"].id] = q.value
        elif c.predicate == "needs_capability":
            needs[c.roles["job"].id] = str(c.roles["capability"])
        elif c.predicate == "has_capability":
            has.setdefault(c.roles["machine"].id, []).append(
                str(c.roles["capability"]))
    for j, dur in jobs.items():
        cap = needs.get(j)
        able = [m for m, cs in has.items()
                if cap in cs and machines.get(m, 0.0) >= dur]
        if len(able) < 2:
            return False
    return True


def main() -> None:
    rows = []
    for s in range(N):
        case = generate(s, n_jobs=6, n_machines=3, slack=0.15)
        world = case.world
        base = answer(world)
        idx = [i for i, c in enumerate(world.claims) if c.predicate == KIND]
        answers = {base}
        for i in idx:
            answers.add(answer(replace(world, claims=tuple(
                c for j, c in enumerate(world.claims) if j != i))))
        rows.append({"decided": len(answers) == 1, "n": len(idx) + 1,
                     "feasible": base,
                     "monotone": monotone_certificate(world),
                     "structural": structural_attempt(world)})

    dec = sum(r["decided"] for r in rows)
    infeasible = sum(r["feasible"] is False for r in rows)
    mono_fires = sum(r["monotone"] for r in rows)
    mono_unsound = sum(r["monotone"] and not r["decided"] for r in rows)
    struct_fires = sum(r["structural"] and r["feasible"] for r in rows)
    struct_unsound = sum(r["structural"] and r["feasible"] and not r["decided"]
                         for r in rows)

    print(f"{N} scheduling instances, perturbation = delete one {KIND}\n")
    print(f"  decided by enumeration        : {dec}/{N}")
    print(f"  infeasible (monotone-safe)    : {infeasible}/{N}")
    print(f"  monotone certificate fires    : {mono_fires}   "
          f"unsound {mono_unsound}")
    print(f"  structural attempt fires (feasible only): {struct_fires}   "
          f"unsound {struct_unsound}")

    enum = statistics.mean(r["n"] for r in rows)
    mono = statistics.mean(1 if r["monotone"] else r["n"] for r in rows)
    both = statistics.mean(
        1 if (r["monotone"] or (r["structural"] and r["feasible"]))
        else r["n"] for r in rows)
    print(f"\n  mean solves, enumeration      : {enum:.1f}")
    print(f"  mean solves, monotone half only: {mono:.1f}  "
          f"({1 - mono / enum:.0%} saving)")
    print(f"  mean solves, plus the structural attempt: {both:.1f}  "
          f"({1 - both / enum:.0%}) -- NOT A SAVING, the attempt is")
    print(f"      unsound on {struct_unsound} of the {struct_fires} instances "
          f"it fires on, so this row is what the\n      wrong answer would "
          f"have cost, shown only to price the temptation.")

    print()
    if mono_unsound == 0 and struct_unsound > 0:
        print(f"-> THE MONOTONE HALF TRANSFERS AND THE STRUCTURAL HALF DOES "
              f"NOT. Infeasible instances\n   are safe for free and sound on "
              f"all {mono_fires}, exactly as flood's non-qualifying "
              f"vehicles\n   were. The structural attempt is UNSOUND on "
              f"{struct_unsound} instances: two capable machines\n   per job "
              f"guarantees the capability survives and says nothing about "
              f"whether the\n   PACKING still fits, which is where bin-packing "
              f"bites.")
        print(f"\n   So the pattern's reach is set by the COMPLEXITY OF THE "
              f"UNDERLYING DECISION.\n   Reachability characterises 'a route "
              f"survives' in polynomial time; nothing\n   characterises 'a "
              f"feasible packing survives' without solving it.")
    elif mono_unsound == 0 and struct_unsound == 0 and struct_fires:
        print(f"-> BOTH HALVES TRANSFER. The structural attempt is sound on all "
              f"{struct_fires} instances it\n   fires on, so NP-hardness does "
              f"not block the pattern -- it only makes the invariant\n   "
              f"weaker. That is the better outcome and it was the stated way to "
              f"change my mind.")
    else:
        print(f"-> the monotone half fires {mono_fires} times with "
              f"{mono_unsound} unsound.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n": N, "decided": dec, "infeasible": infeasible,
         "monotone_fires": mono_fires, "monotone_unsound": mono_unsound,
         "structural_fires": struct_fires,
         "structural_unsound": struct_unsound,
         "mean_enum": enum, "mean_monotone": mono, "mean_both": both},
        indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
