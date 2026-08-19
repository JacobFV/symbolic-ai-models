"""A theory pass: fit `task_success ~ F + (1-F)q^k` to numbers already on disk.

`notes/findings/2026-08-18-what-parse-fidelity-a-multi-kernel-pipeline-needs.md`
swept a claim-drop rate through the flood pipeline and reported a curve. It read
the curve qualitatively -- "crosses its floor at p ~ 0.17", "roughly >= 90%
recall" -- and never fitted a form to it.

The user's standing theory mandate names the candidate:
`P(task success) ~ q^k`, with `q` the per-claim recall and `k` the number of
independently required claims. Adding the floor the curve visibly asymptotes to:

    S(q)  =  F + (1 - F) q^k

If that form survives, one number `k` replaces the whole sweep, the **required
reader recall** follows in closed form instead of by another sweep, and the
per-kind table becomes a decomposition of `k` rather than six separate facts.

No new measurement: every input here is read off the finding.

Run: uv run python -u scripts/reader_survival_law.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

OUT = Path("runs/reader_survival_law.json")

#: drop rate p -> exact-set agreement, from the finding's table, N = 300.
CURVE = ((0.00, 1.000), (0.02, 0.880), (0.05, 0.750), (0.08, 0.633),
         (0.10, 0.603), (0.12, 0.530), (0.15, 0.500), (0.20, 0.383),
         (0.30, 0.370), (0.50, 0.333))
#: the same finding, per kind, at p = 0.20.
PER_KIND = (("mass", 0.733), ("capacity", 0.747), ("link", 0.800),
            ("demand", 0.900), ("load_limit", 0.907), ("flooded", 0.960))
#: "always-none" -- the answer with no world at all. The curve's own asymptote.
FLOOR_REPORTED = 0.347


def fit(curve, floors=None) -> tuple[float, float, float]:
    """Least squares over (k, F) on a coarse grid, then refine. Returns rmse."""
    best = (math.inf, 1.0, 0.0)
    grid_F = floors if floors is not None else [i / 400 for i in range(0, 161)]
    for F in grid_F:
        if F >= 1.0:
            continue
        num = den = 0.0
        for p, s in curve:
            q = 1.0 - p
            if q <= 0 or q >= 1:
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
    rmse, k, F = fit(CURVE)
    print(f"S(q) = F + (1-F) q^k     fitted on the finding's 10 points\n")
    print(f"  k    = {k:.2f}   effective independently-required claims")
    print(f"  F    = {F:.3f}   floor  (finding reports always-none at "
          f"{FLOOR_REPORTED})")
    print(f"  rmse = {rmse:.4f}   against a reported +-0.029 at N = 300\n")
    print(f"  {'p':>6} {'q':>6} {'measured':>10} {'predicted':>10} {'resid':>8}")
    rows = []
    for p, s in CURVE:
        pred = F + (1 - F) * (1 - p) ** k
        rows.append({"p": p, "measured": s, "predicted": pred})
        print(f"  {p:>6.2f} {1-p:>6.2f} {s:>10.3f} {pred:>10.3f} "
              f"{pred-s:>+8.3f}")

    # --- the consequence that deletes a sweep: required reader recall.
    print(f"\nrequired per-claim recall, solved in closed form:\n")
    print(f"  {'target S':>9} {'q needed':>10} {'claims lost per 100':>21}")
    need = {}
    for target in (0.60, 0.70, 0.80, 0.90, 0.95, 0.99):
        y = (target - F) / (1 - F)
        if y <= 0 or y > 1:
            continue
        q = y ** (1.0 / k)
        need[target] = q
        print(f"  {target:>9.2f} {q:>10.4f} {100*(1-q):>20.1f}")
    print(f"\n  The finding's qualitative read was 'roughly >= 90% per-claim "
          f"recall'.\n  The fit says 90% recall buys S = "
          f"{F + (1-F)*0.90**k:.3f}, and reaching S = 0.90 needs "
          f"q = {need.get(0.90, float('nan')):.4f}.")

    # --- per-kind: k should DECOMPOSE, because dropping one kind at rate p is
    # dropping k_kind of the required claims.
    print(f"\nper-kind decomposition at p = 0.20, same F:\n")
    print(f"  {'kind':<12} {'agreement':>10} {'k_kind':>8}")
    total = 0.0
    kinds = {}
    for name, s in PER_KIND:
        y = (s - F) / (1 - F)
        kk = math.log(y) / math.log(0.80) if 0 < y <= 1 else float("nan")
        kinds[name] = kk
        total += kk
        print(f"  {name:<12} {s:>10.3f} {kk:>8.2f}")
    print(f"  {'SUM':<12} {'':>10} {total:>8.2f}   against the aggregate "
          f"k = {k:.2f}")
    print(f"\n  If the kinds were independent and the aggregate sweep dropped "
          f"all six at rate p,\n  the sum should equal k. It is "
          f"{total:.2f} against {k:.2f} -- "
          f"{'consistent' if abs(total-k)/k < 0.25 else 'NOT consistent'}, "
          f"so the law's\n  additivity across kinds is "
          f"{'supported' if abs(total-k)/k < 0.25 else 'not supported'}.")

    print(f"\nSTRATEGIC CONSEQUENCE")
    print(f"  Reader effort should go where k_kind is largest: "
          f"{', '.join(n for n,_ in sorted(kinds.items(), key=lambda kv: -kv[1])[:2])}"
          f" (k = "
          f"{', '.join(f'{v:.2f}' for _,v in sorted(kinds.items(), key=lambda kv: -kv[1])[:2])}),"
          f"\n  not where it is smallest: "
          f"{', '.join(n for n,_ in sorted(kinds.items(), key=lambda kv: kv[1])[:2])}. "
          f"That reproduces the finding's own\n  'domain facts, not constraints' "
          f"reading as a number rather than a story.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"k": k, "floor": F, "rmse": rmse,
                               "curve": rows, "required_recall": need,
                               "k_by_kind": kinds, "k_sum": total}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
