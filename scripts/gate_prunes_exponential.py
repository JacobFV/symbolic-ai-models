"""What the cheap kernel buys the expensive one, as a function of size.

Flood established the inversion: dropping datalog made the flow **1.78x more
expensive**, so its escalation threshold is negative and the cheap kernel is
strictly dominated to skip. That is a constant factor. Scheduling has the same
shape with a sharper mechanism and a size knob:

``capacity_gate`` is **sound and one-sided** -- it only ever proves infeasible,
never feasible. And infeasible is exactly the side ASP must **exhaust** the
search space to establish. So the gate should prune precisely the instances that
cost the most, and its value should grow with ``n_jobs`` rather than sit at a
constant.

Unless clingo finds the global capacity argument itself. Each machine's ``#sum``
is a separate propagator; concluding "total demand exceeds total capacity" means
aggregating across all of them. If the solver does that on its own, the gate is
redundant. That is the open question here.

Run: uv run python -u scripts/gate_prunes_exponential.py
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from symbolic_ai_kernels import KernelRequest, get_kernel
from symbolic_ai_generators.scheduling.ops import build_program, capacity_gate
from symbolic_ai_generators.scheduling.world import generate

OUT = Path("runs/gate_prunes_exponential.json")
SIZES = (6, 9, 12, 15, 18)
#: Negative slack puts capacity below demand, which is the only regime where a
#: sound capacity bound can fire at all.
SLACKS = (-0.25, -0.10, 0.10, 0.30)
SEEDS = 12


def run_asp(world) -> tuple[float, float, bool, bool]:
    program, _ = build_program(world)
    asp = get_kernel("asp@1")
    req = KernelRequest(params={"program": program, "max_models": 1})
    t0 = time.perf_counter_ns()
    proj = asp.project(world, req)
    res = asp.run(proj, req)
    return ((time.perf_counter_ns() - t0) / 1e6, float(res.cost.usd or 0.0),
            bool(res.ok), bool(res.conclusive))


def main() -> None:
    rows = []
    print(f"{'n_jobs':>7} {'slack':>7} {'gate fires':>11} {'SAT':>6} "
          f"{'ms|gated':>10} {'ms|passed':>10} {'saved x':>9}")
    print("-" * 66)
    for n in SIZES:
        for slack in SLACKS:
            fired, sat, ms_fired, ms_passed = 0, 0, [], []
            for s in range(SEEDS):
                case = generate(s, n_jobs=n, n_machines=3, slack=slack)
                need, _ = capacity_gate(case.world)
                ms, usd, ok, conclusive = run_asp(case.world)
                rec = {"n_jobs": n, "slack": slack, "seed": s,
                       "gate_fires": not need, "sat": ok,
                       "conclusive": conclusive, "asp_ms": ms, "asp_usd": usd}
                rows.append(rec)
                if ok:
                    sat += 1
                if need:
                    ms_passed.append(ms)
                else:
                    fired += 1
                    ms_fired.append(ms)
            mf = statistics.mean(ms_fired) if ms_fired else float("nan")
            mp = statistics.mean(ms_passed) if ms_passed else float("nan")
            ratio = (mf / mp) if (ms_fired and ms_passed and mp > 0) else float("nan")
            print(f"{n:>7} {slack:>7.2f} {fired:>7}/{SEEDS} {sat:>6} "
                  f"{mf:>10.2f} {mp:>10.2f} {ratio:>9.2f}")

    # --- the mechanism: is UNSAT the expensive side, and does it widen?
    print(f"\nASP cost by OUTCOME, which is the mechanism claim:\n")
    print(f"{'n_jobs':>7} {'ms|UNSAT':>10} {'ms|SAT':>10} {'unsat/sat':>10} {'n':>5}")
    print("-" * 46)
    law = {}
    for n in SIZES:
        at = [r for r in rows if r["n_jobs"] == n]
        u = [r["asp_ms"] for r in at if not r["sat"]]
        v = [r["asp_ms"] for r in at if r["sat"]]
        mu = statistics.mean(u) if u else float("nan")
        mv = statistics.mean(v) if v else float("nan")
        ratio = (mu / mv) if (u and v and mv > 0) else float("nan")
        law[n] = {"unsat_ms": mu, "sat_ms": mv, "ratio": ratio,
                  "n_unsat": len(u), "n_sat": len(v)}
        print(f"{n:>7} {mu:>10.2f} {mv:>10.2f} {ratio:>10.2f} {len(at):>5}")

    # --- what the gate actually saves, end to end
    print(f"\nend to end, gate-then-solve against always-solve:\n")
    tot_always = sum(r["asp_ms"] for r in rows)
    tot_gated = sum(r["asp_ms"] for r in rows if not r["gate_fires"])
    n_fired = sum(r["gate_fires"] for r in rows)
    print(f"  always solve   {tot_always:>9.1f} ms over {len(rows)} instances")
    print(f"  gate then solve{tot_gated:>9.1f} ms  ({n_fired} of {len(rows)} "
          f"never reached the solver)")
    if tot_gated > 0:
        print(f"  -> the gate removes {1 - tot_gated/tot_always:.1%} of solver "
              f"time for {n_fired/len(rows):.1%} of instances, at zero accuracy "
              f"cost\n     because the bound is sound.")

    ratios = [law[n]["ratio"] for n in SIZES
              if law[n]["ratio"] == law[n]["ratio"]]
    if len(ratios) >= 2:
        if ratios[-1] > ratios[0] * 1.3:
            print(f"\n-> UNSAT/SAT widens {ratios[0]:.2f}x -> {ratios[-1]:.2f}x "
                  f"across n_jobs {SIZES[0]}->{SIZES[-1]}.\n   clingo does NOT "
                  f"aggregate the per-machine sums, so the gate converts a "
                  f"growing\n   exponential into arithmetic. Its value is not a "
                  f"constant factor.")
        elif max(ratios) < 1.3:
            print(f"\n-> UNSAT costs about the same as SAT (ratios "
                  f"{min(ratios):.2f}-{max(ratios):.2f}).\n   clingo FINDS the "
                  f"global capacity argument itself. The gate is redundant on "
                  f"cost,\n   and flood's 1.78x was datalog shrinking the "
                  f"GROUNDING, not pruning search.")
        else:
            print(f"\n-> UNSAT/SAT sits at {min(ratios):.2f}-{max(ratios):.2f} "
                  f"and does not widen with n.\n   Real but constant: the gate "
                  f"pays a fixed multiple, like flood's datalog.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"sizes": SIZES, "slacks": SLACKS,
                               "law": {str(k): v for k, v in law.items()},
                               "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
