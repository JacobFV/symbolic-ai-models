"""Execution traces before any router, and the threshold they imply.

The programme's routing directive is explicit about order: **collect traces where
multiple valid strategies actually differ, use explicit heuristics, and learn a
policy only after that.** It also gives the rule to derive against — escalate
when

    p * L  >  c1 - c0

for cheap cost `c0`, expensive cost `c1`, cheap-arm error probability `p` and
loss `L` from a wrong answer.

So this collects the traces and derives the threshold, rather than assuming a
router is wanted. Four strategies over the same queries, each a real
configuration of the flow rather than a hypothetical:

    full            datalog reachability + ASP routing + SMT load checking
    no ASP search   first candidate route only
    no datalog      route over raw links, ignoring derived reachability
    no SMT          skip the load constraints

Per case and per strategy: cost, latency, success, and the world features a
router could actually see **before** running anything.

Run: uv run python -u scripts/routing_traces.py
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve

OUT = Path("runs/routing_traces.json")
N_CASES = 40

STRATEGIES = (
    ("full", {}),
    ("no ASP search", {"first_route_only": True}),
    ("no datalog", {"ignore_flooding": True}),
    ("no SMT", {"ignore_bridge_limits": True}),
)


def cost_of(outputs) -> float:
    total = 0.0
    for artifact in outputs.values():
        value = getattr(artifact, "value", None)
        if not isinstance(value, dict):
            continue
        c = value.get("cost")
        if isinstance(c, dict) and "usd" in c:
            total += float(c["usd"] or 0.0)
        elif "usd" in value:
            total += float(value["usd"] or 0.0)
    return total


def features(case) -> dict:
    """What a router could see before running anything."""
    kinds: dict[str, int] = {}
    for c in case.world.claims:
        kinds[c.predicate] = kinds.get(c.predicate, 0) + 1
    return {"links": kinds.get("link", 0), "bridges": kinds.get("bridge_on", 0),
            "flooded": kinds.get("flooded", 0),
            "vehicles": kinds.get("mass", 0),
            "claims": len(case.world.claims)}


def main() -> None:
    cases = [generate(s) for s in range(N_CASES)]
    truth = [solve(c.world)[0] for c in cases]
    rows = []
    print(f"{N_CASES} cases, {len(STRATEGIES)} strategies\n", flush=True)
    for case, want in zip(cases, truth):
        rec = {"seed": case.seed, "non_empty": bool(want),
               **features(case), "arms": {}}
        for name, abl in STRATEGIES:
            t0 = time.perf_counter_ns()
            try:
                answer, outs, _ = solve(case.world, **abl)
                usd = cost_of(outs)
            except Exception:
                answer, usd = (), float("nan")
            rec["arms"][name] = {"usd": usd,
                                 "ns": time.perf_counter_ns() - t0,
                                 "ok": answer == want}
        rows.append(rec)

    hdr = (f"{'strategy':<16} {'success':>8} {'success|ne':>11} {'$/case':>11} "
           f"{'ms/case':>9} {'$ vs full':>10}")
    print(hdr)
    print("-" * len(hdr))
    ne = [r for r in rows if r["non_empty"]]
    full_usd = statistics.mean(r["arms"]["full"]["usd"] for r in rows)
    summary = {}
    for name, _ in STRATEGIES:
        succ = statistics.mean(r["arms"][name]["ok"] for r in rows)
        succ_ne = statistics.mean(r["arms"][name]["ok"] for r in ne)
        usd = statistics.mean(r["arms"][name]["usd"] for r in rows)
        ms = statistics.mean(r["arms"][name]["ns"] for r in rows) / 1e6
        summary[name] = {"success": succ, "success_non_empty": succ_ne,
                         "usd": usd, "ms": ms, "usd_ratio": usd / full_usd}
        print(f"{name:<16} {succ:>8.3f} {succ_ne:>11.3f} {usd:>11.3e} "
              f"{ms:>9.2f} {usd/full_usd:>9.2f}x")

    # --- the derived threshold, per the directive's own rule
    print(f"\nescalation threshold, p*L > c1 - c0:\n")
    c1 = summary["full"]["usd"]
    for name, _ in STRATEGIES:
        if name == "full":
            continue
        c0 = summary[name]["usd"]
        p = 1.0 - summary[name]["success_non_empty"]
        gap = c1 - c0
        L = (gap / p) if p > 0 else float("inf")
        summary[name]["loss_threshold_usd"] = L
        print(f"  {name:<16} c1-c0 = {gap:>10.3e}   p = {p:>5.3f}   "
              f"escalate when a wrong answer costs > {L:.3e} USD")

    # --- does the per-case spread hide an opportunity the aggregate does not?
    print(f"\nper-case cost spread (full / cheapest arm):")
    ratios = []
    for r in rows:
        cheapest = min(r["arms"][n]["usd"] for n, _ in STRATEGIES)
        if cheapest > 0:
            ratios.append(r["arms"]["full"]["usd"] / cheapest)
    print(f"  p50 {statistics.median(ratios):.2f}x   "
          f"max {max(ratios):.2f}x   "
          f"share above 2x: {sum(x > 2 for x in ratios)/len(ratios):.1%}")

    worst = min(summary[n]["loss_threshold_usd"]
                for n, _ in STRATEGIES if n != "full")
    print(f"\n-> the LOWEST threshold across arms is {worst:.3e} USD. A wrong "
          f"answer would have to\n   cost less than that for any cheap arm to "
          f"be worth taking.")
    if worst < 1e-6 and max(ratios) < 3:
        print(f"   It does not, for any plausible use, and no case shows a "
              f"large cost spread\n   (max {max(ratios):.2f}x). ALWAYS TAKE THE "
              f"FULL FLOW. Routing is not worth learning\n   here -- the "
              f"strategies differ in SUCCESS but not in COST, and the "
              f"directive's\n   precondition is only half met.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n_cases": N_CASES, "summary": summary,
                               "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
