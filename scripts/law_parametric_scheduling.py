"""Does the law's F track a task knob, or is it a per-domain constant?

`S = F + (1-F) q^k` now holds on two domains with both parameters predicted from
structure. Scheduling adds something neither had: a **tunable decision margin**.
So the question stops being *does it hold a third time* and becomes *what governs
its parameters*.

`F = P(truth == the degenerate answer)` is the referent under test. Here the
degenerate answer is whatever the ASP kernel says on an **empty world** -- no
jobs, so every job is vacuously assignable, so `True`. If the referent is real,
`F` must equal the **feasible share**, which `slack` controls directly and which
is readable off the generator with no corruption at all.

`k` is the ablation dependency on the **non-trivial** population -- here the
*infeasible* cases, since the degenerate answer is True. That population flips
sign relative to solvency, which is the point: the law does not know which value
is "trivial", only which one the kernels produce on nothing.

Run: uv run python -u scripts/law_parametric_scheduling.py
"""

from __future__ import annotations

import dataclasses
import json
import math
import random
import statistics
from pathlib import Path

from symbolic_ai_generators.scheduling import generate
from symbolic_ai_generators.scheduling.ops import build_program
from symbolic_ai_kernels import KernelRequest, get_kernel

OUT = Path("runs/law_parametric_scheduling.json")
N_CASES = 40
SLACKS = (0.05, 0.15, 0.30, 0.60)
RATES = (0.0, 0.05, 0.10, 0.20, 0.35, 0.50, 0.80)
REPEATS = 3
ASP = get_kernel("asp@1")


def solve(world) -> bool:
    program, _ = build_program(world)
    req = KernelRequest(params={"program": program, "max_models": 1})
    return ASP.run(ASP.project(world, req), req).ok


def drop(world, *, rng, rate):
    return dataclasses.replace(
        world, claims=tuple(c for c in world.claims if rng.random() >= rate))


def fit(curve):
    best = (math.inf, 1.0, 0.0)
    for Fi in range(0, 396):
        F = Fi / 400
        num = den = 0.0
        for p, s in curve:
            q = 1.0 - p
            if not 0 < q < 1:
                continue
            y = (s - F) / (1.0 - F)
            if y <= 0:
                continue
            num += math.log(q) * math.log(y)
            den += math.log(q) ** 2
        if den == 0:
            continue
        k = num / den
        rmse = math.sqrt(sum((F + (1 - F) * (1 - p) ** k - s) ** 2
                             for p, s in curve) / len(curve))
        if rmse < best[0]:
            best = (rmse, k, F)
    return best


def main() -> None:
    probe = generate(0, slack=0.15)
    degenerate = solve(dataclasses.replace(probe.world, claims=()))
    print(f"the degenerate answer (empty world) is {degenerate}\n", flush=True)

    hdr = (f"{'slack':>6} {'feasible':>9} {'F pred':>8} {'F fit':>7} "
           f"{'err':>6} {'d(non-triv)':>12} {'k pred':>7} {'k fit':>7} "
           f"{'err':>6} {'rmse':>7}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for slack in SLACKS:
        cases = [generate(s, slack=slack) for s in range(N_CASES)]
        truth = [c.feasible for c in cases]
        f_pred = sum(t == degenerate for t in truth) / len(truth)

        nontrivial = [c for c, t in zip(cases, truth) if t != degenerate]
        ds = []
        for c in nontrivial:
            want = c.feasible
            d = 0
            for i in range(len(c.world.claims)):
                w = dataclasses.replace(
                    c.world, claims=tuple(x for j, x in enumerate(c.world.claims)
                                          if j != i))
                d += (solve(w) != want)
            ds.append(d)
        qs = [1 - p for p in RATES if 0 < p < 1]
        k_pred = (statistics.mean(
            math.log(sum(q ** d for d in ds) / len(ds)) / math.log(q)
            for q in qs) if ds else float("nan"))

        curve = []
        for p in RATES:
            hits = n = 0
            for r in range(REPEATS if p else 1):
                rng = random.Random(4200 + 17 * r)
                for c, want in zip(cases, truth):
                    hits += solve(drop(c.world, rng=rng, rate=p)) == want
                    n += 1
            curve.append((p, hits / n))
        rmse, k_fit, f_fit = fit(curve)
        ef = abs(f_fit - f_pred) / max(f_pred, 1e-9)
        ek = (abs(k_fit - k_pred) / max(k_pred, 1e-9)
              if k_pred == k_pred and k_pred > 0 else float("nan"))
        rows.append({"slack": slack, "feasible_share": sum(truth) / len(truth),
                     "F_pred": f_pred, "F_fit": f_fit, "F_err": ef,
                     "n_nontrivial": len(ds),
                     "d_nontrivial": statistics.mean(ds) if ds else None,
                     "k_pred": k_pred, "k_fit": k_fit, "k_err": ek,
                     "rmse": rmse, "curve": curve})
        print(f"{slack:>6.2f} {sum(truth)/len(truth):>9.3f} {f_pred:>8.3f} "
              f"{f_fit:>7.3f} {ef:>5.1%} "
              f"{statistics.mean(ds) if ds else float('nan'):>12.2f} "
              f"{k_pred:>7.2f} {k_fit:>7.2f} {ek:>5.1%} {rmse:>7.4f}",
              flush=True)

    fs = [r["F_pred"] for r in rows]
    print(f"\nF moves {min(fs):.3f} -> {max(fs):.3f} across the slack sweep, "
          f"predicted with no corruption at all.")
    worst_f = max(r["F_err"] for r in rows)
    print(f"  worst F error: {worst_f:.1%}")
    ks = [r["k_pred"] for r in rows if r["k_pred"] == r["k_pred"]]
    if len(ks) > 1:
        print(f"  k(slack): " + ", ".join(
            f"{r['slack']:.2f}->{r['k_pred']:.1f}" for r in rows))
    if worst_f < 0.15:
        print(f"\n-> F IS PARAMETRIC. It is not a per-domain constant: it "
              f"tracks a task knob,\n   and it is readable off the generator "
              f"before any sweep is run.")
    else:
        print(f"\n-> F does not track the knob; the referent fails its first "
              f"parametric test.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"degenerate": degenerate, "rows": rows},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
