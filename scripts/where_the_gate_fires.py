"""Does the cheap sound gate fire where the expensive kernel's cost is?

The routing directive wants paths compared on measured cost before any policy is
learned. Scheduling offers the cleanest instance of the question, because its
cheap path is **sound and one-sided**: ``capacity_gate`` proves infeasible or
says nothing, so escalating past it costs no accuracy at all. The only question
is economic -- how much solver time does it remove?

The answer is not the fire rate. What matters is whether the instances it fires
on are the **expensive** ones. It can only fire where capacity is below demand,
i.e. ``slack < 0``, and hardness in packing problems concentrates at the
feasibility boundary. So the gate might be structurally aimed away from the cost.

This sweeps slack finely across the boundary at sizes the domain could not reach
until the oracle was fixed (see the 2026-08-19 finding; it was 53s per 18-job
instance before, 0.0002s now).

Run: uv run python -u scripts/where_the_gate_fires.py
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from symbolic_ai_kernels import KernelRequest, get_kernel
from symbolic_ai_generators.scheduling.ops import build_program, capacity_gate
from symbolic_ai_generators.scheduling.world import generate

OUT = Path("runs/where_the_gate_fires.json")
BUDGET_NS = 3_000_000_000
#: 0.0 exactly is deliberately absent. There the oracle's capacity bound is
#: tight and generating one case costs 1.6s at 30 jobs; +/-0.005 is the same
#: regime and four orders cheaper. See ``feasible_by_search``.
SLACKS = (-0.20, -0.08, -0.03, -0.005, 0.005, 0.03, 0.08, 0.20)
SHAPES = ((20, 3), (30, 4), (40, 5))
SEEDS = 10


def run(world) -> tuple[float, bool, bool]:
    prog, _ = build_program(world)
    asp = get_kernel("asp@1")
    req = KernelRequest(params={"program": prog, "max_models": 1},
                        budget_ns=BUDGET_NS)
    t0 = time.perf_counter()
    proj = asp.project(world, req)
    res = asp.run(proj, req)
    return time.perf_counter() - t0, bool(res.ok), bool(res.conclusive)


def main() -> None:
    rows = []
    for n_jobs, n_machines in SHAPES:
        print(f"\n=== {n_jobs} jobs, {n_machines} machines "
              f"({n_machines**n_jobs:.1e} assignments) ===")
        print(f"{'slack':>7} {'gate':>7} {'sat':>5} {'mean s':>9} {'max s':>9} "
              f"{'hit budget':>11}")
        print("-" * 52)
        for slack in SLACKS:
            secs, fired, sat, censored = [], 0, 0, 0
            for s in range(SEEDS):
                case = generate(s, n_jobs=n_jobs, n_machines=n_machines,
                                slack=slack)
                need, _ = capacity_gate(case.world)
                el, ok, conclusive = run(case.world)
                secs.append(el)
                fired += (not need)
                sat += ok
                censored += (not conclusive)
                rows.append({"n_jobs": n_jobs, "n_machines": n_machines,
                             "slack": slack, "seed": s, "gate_fires": not need,
                             "sat": ok, "conclusive": conclusive, "secs": el})
            print(f"{slack:>+7.2f} {fired:>4}/{SEEDS} {sat:>5} "
                  f"{statistics.mean(secs):>9.3f} {max(secs):>9.3f} "
                  f"{censored:>8}/{SEEDS}", flush=True)

    # --- the question: is the gate aimed at the cost, or away from it?
    print(f"\n\nthe gate against the cost, pooled over shapes:\n")
    print(f"{'population':<28} {'n':>5} {'mean s':>9} {'total s':>10} {'share of cost':>14}")
    print("-" * 70)
    total = sum(r["secs"] for r in rows)
    fired = [r for r in rows if r["gate_fires"]]
    passed = [r for r in rows if not r["gate_fires"]]
    for label, pop in (("gate FIRES (solver skipped)", fired),
                       ("gate passes (solver runs)", passed)):
        if not pop:
            continue
        t = sum(r["secs"] for r in pop)
        print(f"{label:<28} {len(pop):>5} {statistics.mean(r['secs'] for r in pop):>9.3f} "
              f"{t:>10.2f} {t/total:>13.1%}")

    print(f"\nwhere the cost concentrates, by slack (pooled):\n")
    print(f"{'slack':>7} {'total s':>10} {'share':>8} {'gate fires':>11}")
    print("-" * 40)
    peak, peak_slack = -1.0, None
    for slack in SLACKS:
        at = [r for r in rows if r["slack"] == slack]
        t = sum(r["secs"] for r in at)
        f = sum(r["gate_fires"] for r in at)
        if t > peak:
            peak, peak_slack = t, slack
        print(f"{slack:>+7.2f} {t:>10.2f} {t/total:>7.1%} {f:>7}/{len(at)}")

    saved = sum(r["secs"] for r in fired)
    print(f"\n-> the gate removes {saved/total:.1%} of solver time on "
          f"{len(fired)/len(rows):.1%} of instances, at zero accuracy cost.")
    peak_rows = [r for r in rows if r["slack"] == peak_slack]
    peak_fire = sum(r["gate_fires"] for r in peak_rows) / len(peak_rows)
    print(f"   Cost peaks at slack {peak_slack:+.2f} ({peak/total:.1%} of all "
          f"solver time), where the gate\n   fires on {peak_fire:.0%} of "
          f"instances.")
    if saved / total > len(fired) / len(rows) * 1.2:
        print(f"   The gate is aimed AT the cost: it removes a larger share of "
              f"time than of instances.")
    elif saved / total < len(fired) / len(rows) * 0.8:
        print(f"   The gate is aimed AWAY from the cost: a sound cheap check "
              f"fires where the\n   problem is easy, and buys LESS than its "
              f"fire rate suggests.")
    else:
        print(f"   The gate is aimed NEITHER way: it removes time in proportion "
              f"to instances,\n   so its value is its fire rate and nothing "
              f"more.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"budget_ns": BUDGET_NS, "shapes": SHAPES,
                               "slacks": SLACKS, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
