"""Does the NP-hardness actually bite on the instances we generate?

Flood's decision turned out to be a widest path -- in P, behind three kernels.
Solvency's is a sum against a threshold, openly polynomial. Scheduling is the one
domain whose decision is genuinely NP-hard: bin-packing with capability
constraints.

But **NP-hard in principle is not hard on this distribution**, and that had not
been checked. So: a two-sided *polynomial* procedure, neither half of which can
be wrong.

- ``capacity_gate`` proves **infeasible** when total demand exceeds total
  capacity -- sound, one pass.
- greedy placement (longest job first onto the capable machine with the most
  room) proves **feasible** when it succeeds -- sound, since it exhibits an
  assignment.

Together they are inconclusive only in the middle. What share of the generator's
instances actually reaches that middle is what this measures, and it is the
programme-level version of the flood finding.

Run: uv run python -u scripts/does_hardness_bite.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_generators.scheduling import generate
from symbolic_ai_generators.scheduling.ops import capacity_gate

OUT = Path("runs/does_hardness_bite.json")
N = 60
SLACKS = (-0.10, -0.02, 0.0, 0.02, 0.05, 0.15, 0.40)
SHAPES = ((6, 3), (12, 4), (20, 5))


def greedy_feasible(jobs, machines) -> bool:
    """Longest job first onto the capable machine with the most room.

    Sound in one direction only: success exhibits an assignment, failure proves
    nothing.
    """
    room = {m: cap for m, (cap, _) in machines.items()}
    caps = {m: set(cs) for m, (_, cs) in machines.items()}
    for job in sorted(jobs, key=lambda j: -jobs[j][0]):
        dur, need = jobs[job]
        able = [m for m in room if need in caps[m] and room[m] + 1e-9 >= dur]
        if not able:
            return False
        best = max(able, key=lambda m: room[m])
        room[best] -= dur
    return True


def main() -> None:
    print(f"{'shape':<10} {'slack':>7} {'gate proves':>12} {'greedy proves':>14} "
          f"{'INCONCLUSIVE':>13} {'true feasible':>14}")
    print("-" * 76)
    rows = {}
    for n_jobs, n_machines in SHAPES:
        for slack in SLACKS:
            gate = greedy = mid = feas = 0
            mid_feasible = 0
            for s in range(N):
                case = generate(s, n_jobs=n_jobs, n_machines=n_machines,
                                slack=slack)
                feas += case.feasible
                need_search, _ = capacity_gate(case.world)
                if not need_search:
                    gate += 1                    # proved infeasible
                elif greedy_feasible(case.jobs, case.machines):
                    greedy += 1                  # proved feasible
                else:
                    mid += 1
                    mid_feasible += case.feasible
            rows[f"{n_jobs}x{n_machines}|{slack}"] = {
                "gate": gate / N, "greedy": greedy / N, "inconclusive": mid / N,
                "feasible": feas / N,
                "inconclusive_feasible": (mid_feasible / mid) if mid else 0.0}
            print(f"{f'{n_jobs}x{n_machines}':<10} {slack:>+7.2f} "
                  f"{gate / N:>12.2f} {greedy / N:>14.2f} {mid / N:>13.2f} "
                  f"{feas / N:>14.2f}", flush=True)
        print()

    settled = statistics.mean(1 - v["inconclusive"] for v in rows.values())
    default = rows["6x3|0.15"]
    worst = max(rows.items(), key=lambda kv: kv[1]["inconclusive"])
    print(f"  polynomial procedure settles, averaged over the grid: "
          f"{settled:.1%}")
    print(f"  at the DEFAULT (6x3, slack 0.15):                    "
          f"{1 - default['inconclusive']:.1%}")
    print(f"  worst cell: {worst[0]} at "
          f"{worst[1]['inconclusive']:.1%} inconclusive")

    # What is actually IN the inconclusive band -- the number that says what
    # search is buying.
    band = [(k, v) for k, v in rows.items() if v["inconclusive"] > 0.2]
    share = statistics.mean(v["inconclusive_feasible"] for _, v in band)
    print(f"\n  of the inconclusive band, the share that is FEASIBLE: "
          f"{share:.1%}")
    print(f"  (so {1 - share:.0%} of it is INFEASIBLE instances awaiting a "
          f"proof)")

    print()
    if 1 - default["inconclusive"] > 0.85:
        print(f"-> THE HARDNESS DOES NOT BITE WHERE WE GENERATE. At the default "
              f"settings a sound\n   polynomial pair settles "
              f"{1 - default['inconclusive']:.0%} of instances: the capacity "
              f"bound proves the infeasible ones\n   and a greedy packing "
              f"exhibits an assignment for the feasible ones. Search is "
              f"needed\n   on the remainder only.")
        print(f"\n   Combined with flood being a widest path and solvency a sum "
              f"against a threshold,\n   NO DOMAIN IN THIS SUITE SUPPORTS "
              f"'heterogeneous kernels are necessary' on its own\n   "
              f"distribution. The benchmark needs a hard regime; the kernels do "
              f"not need a defence.")
        print(f"\n   The hard regime is identifiable rather than hypothetical: "
              f"the inconclusive share\n   peaks at {worst[0]} "
              f"({worst[1]['inconclusive']:.0%}), which is where a generator "
              f"should sample if the\n   question is what search buys.")
    else:
        print(f"-> SCHEDULING GENUINELY EXERCISES SEARCH: "
              f"{default['inconclusive']:.0%} inconclusive at the default, so "
              f"the suite has one\n   honest hard domain after all -- unlike "
              f"flood, whose decision is a widest path,\n   and solvency, whose "
              f"decision is a sum against a threshold.")
        print(f"\n-> AND THE SEARCH IS BUYING INFEASIBILITY PROOFS. Only "
              f"{share:.0%} of the inconclusive band\n   is feasible: greedy "
              f"placement exhibits an assignment for nearly every instance "
              f"that\n   has one, so what nothing polynomial provides is a "
              f"CERTIFICATE THAT NO ASSIGNMENT\n   EXISTS. That is exactly the "
              f"side ASP has to exhaust, and exactly what the capacity\n   "
              f"gate buys cheaply where the arithmetic happens to settle it.")
        print(f"\n   It also says where a generator should sample to study "
              f"search: the band is widest\n   just above slack 0, where "
              f"capacity is sufficient but capabilities do not line up.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
