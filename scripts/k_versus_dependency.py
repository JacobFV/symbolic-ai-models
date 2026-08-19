"""Is `k` a count, or a fitted constant?

`notes/findings/2026-08-18-the-reader-survival-law-and-the-98-percent-recall-it-demands.md`
fitted `S = F + (1-F) q^k` to the flood pipeline's parse-fidelity sweep and got
`k = 9.35` with rmse 0.015. It labelled itself an *empirical scaling law* and
named its own promotion test:

> If `k` is a real count of required claims, it should be derivable from the
> answer's dependency set. Agreement would promote this toward a mechanistic
> model; disagreement would kill it.

**The dependency set is directly measurable.** Drop one claim, re-solve, and see
whether the answer moves. The number of claims that individually move it is `d`,
the answer's dependency size, and it needs no fitting at all.

**A refinement registered before running.** The law fits `E[q^d]` across cases,
and Jensen gives `E[q^d] >= q^E[d]` whenever `d` varies. So the fitted exponent
should land **below** mean `d`, with the gap growing in `Var(d)` -- equality only
if every case depends on the same number of claims. A naive "k should equal d"
would read that gap as a failure.

The honest comparison is therefore against the **effective exponent**

    k_eff(q)  =  log E[q^d] / log q

computed from the measured distribution of `d` at the same `q` range the sweep
used, which is what the law actually fitted.

Run: uv run python -u scripts/k_versus_dependency.py
"""

from __future__ import annotations

import collections
import json
import math
import statistics
import time
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_core.world import WorldSnapshot

OUT = Path("runs/k_versus_dependency.json")
N_CASES = 40
FITTED_K = 9.35
#: the drop rates the sweep used, where the law was fitted
SWEEP_Q = (0.98, 0.95, 0.92, 0.90, 0.88, 0.85, 0.80)


def without(world: WorldSnapshot, idx: int) -> WorldSnapshot:
    """The same world with claim ``idx`` removed."""
    import dataclasses
    kept = tuple(c for i, c in enumerate(world.claims) if i != idx)
    return dataclasses.replace(world, claims=kept)


def main() -> None:
    t0 = time.perf_counter()
    per_case, per_kind = [], collections.Counter()
    kind_total = collections.Counter()
    print(f"{N_CASES} cases, one solve per claim\n", flush=True)
    for s in range(N_CASES):
        case = generate(s)
        base, _, _ = solve(case.world)
        d = 0
        for i, claim in enumerate(case.world.claims):
            kind_total[claim.predicate] += 1
            try:
                got, _, _ = solve(without(case.world, i))
            except Exception:
                got = None                      # a world the flow refuses
            if got != base:
                d += 1
                per_kind[claim.predicate] += 1
        per_case.append({"seed": s, "claims": len(case.world.claims),
                         "d": d, "answer_size": len(base)})
        if s % 10 == 0:
            print(f"  seed {s:>3}  claims {len(case.world.claims):>3}  "
                  f"d {d:>3}  answer {len(base)}", flush=True)

    ds = [r["d"] for r in per_case]
    mean_d, var_d = statistics.mean(ds), statistics.pvariance(ds)
    print(f"\nmeasured dependency size over {len(ds)} cases:")
    print(f"  mean {mean_d:.2f}   sd {math.sqrt(var_d):.2f}   "
          f"min {min(ds)}   max {max(ds)}   "
          f"claims/world {statistics.mean(r['claims'] for r in per_case):.1f}")

    # --- the honest comparison: the exponent the law would have fitted, given
    # this distribution of d, at the q range the sweep covered.
    print(f"\n  {'q':>6} {'E[q^d]':>10} {'k_eff':>8}")
    keffs = []
    for q in SWEEP_Q:
        e = sum(q ** d for d in ds) / len(ds)
        keff = math.log(e) / math.log(q)
        keffs.append(keff)
        print(f"  {q:>6.2f} {e:>10.4f} {keff:>8.2f}")
    keff = statistics.mean(keffs)
    print(f"\n  mean k_eff = {keff:.2f}   against mean d = {mean_d:.2f} "
          f"(Jensen gap {mean_d - keff:+.2f})")
    print(f"  fitted k   = {FITTED_K:.2f}")
    err = abs(keff - FITTED_K) / FITTED_K
    print(f"  |k_eff - k| / k = {err:.1%}")

    verdict = ("PROMOTED: k is a count" if err < 0.25 else
               "KILLED: k is not the dependency size")
    print(f"\n-> {verdict}")
    if err < 0.25:
        print(f"   The exponent fitted to a corruption sweep equals the "
              f"dependency size measured\n   by ablation, so required recall is "
              f"PREDICTABLE for a new task from its own\n   dependency "
              f"structure, with no sweep.")
    else:
        print(f"   The exponent does not count claims. The fit reproduces the "
              f"curve without\n   the mechanism it was read as having.")

    print(f"\nper kind: how often dropping one claim of this kind moved the "
          f"answer\n")
    print(f"  {'kind':<12} {'critical':>9} {'present':>8} {'share':>7} "
          f"{'per case':>9} {'law k_kind':>11}")
    LAW = {"mass": 2.31, "capacity": 2.16, "link": 1.61, "demand": 0.73,
           "load_limit": 0.68, "flooded": 0.28}
    measured_kind = {}
    for kind in sorted(kind_total, key=lambda k: -per_kind[k]):
        crit, tot = per_kind[kind], kind_total[kind]
        per = crit / len(ds)
        measured_kind[kind] = per
        print(f"  {kind:<12} {crit:>9,} {tot:>8,} {crit/tot:>6.1%} "
              f"{per:>9.2f} {LAW.get(kind, float('nan')):>11.2f}")

    shared = [k for k in LAW if k in measured_kind]
    order_law = sorted(shared, key=lambda k: -LAW[k])
    order_meas = sorted(shared, key=lambda k: -measured_kind[k])
    print(f"\n  law order:      {' > '.join(order_law)}")
    print(f"  measured order: {' > '.join(order_meas)}")
    print(f"  {'SAME ORDER' if order_law == order_meas else 'ORDERS DIFFER'}")

    print(f"\n{time.perf_counter()-t0:.0f}s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n_cases": len(ds), "mean_d": mean_d, "sd_d": math.sqrt(var_d),
         "k_eff": keff, "fitted_k": FITTED_K, "rel_error": err,
         "per_case": per_case, "per_kind_critical": dict(per_kind),
         "per_kind_present": dict(kind_total),
         "per_kind_per_case": measured_kind, "law_k_kind": LAW}, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
