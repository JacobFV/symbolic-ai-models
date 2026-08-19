"""Like for like: fit the survival exponent on the same cases the ablation used.

`scripts/k_versus_dependency.py` measured the flood answer's dependency size by
single-claim ablation -- mean `d` = 6.95 over 40 cases -- and the exponent that
distribution implies, `k_eff` = 5.76, against the **9.35** fitted to the
published sweep. A 38% gap, in the opposite direction from the Jensen
correction registered beforehand.

Two explanations, and they have opposite consequences:

**Interactions.** Single-claim ablation sees only claims that *individually*
move the answer. Random dropping removes several at once, so a pair that is
harmless alone and fatal together is invisible to ablation, and `d` is a lower
bound on the effective exponent. If so, dependency-weighted recall computed by
ablation -- which is what a read set gives -- **understates what the reader must
recover**, and that matters directly for the reader programme.

**Population.** The published sweep used 300 seeds; the ablation used 40, and the
answer set is empty in a large share of them. A different mix of cases would
shift the fitted exponent with no interaction effect at all.

This separates them by running the drop sweep on **the same 40 cases** and
fitting `k` to that curve. Same cases, same metric, so any remaining gap against
`k_eff` is interaction.

Run: uv run python -u scripts/k_same_population.py
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read import corrupt

OUT = Path("runs/k_same_population.json")
N_CASES = 40
RATES = (0.0, 0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.30, 0.50)
REPEATS = 5
PUBLISHED_K, ABLATION_K_EFF = 9.35, 5.76


def fit(curve) -> tuple[float, float, float]:
    best = (math.inf, 1.0, 0.0)
    for Fi in range(0, 201):
        F = Fi / 500
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
    cases = [generate(s) for s in range(N_CASES)]
    truth = [solve(c.world)[0] for c in cases]
    empty = sum(1 for t in truth if not t)
    print(f"{N_CASES} cases; {empty} have an EMPTY answer "
          f"({empty/N_CASES:.0%}) -- those survive corruption for free\n",
          flush=True)

    curve, curve_ne = [], []
    print(f"  {'p':>6} {'all cases':>10} {'non-empty':>10}")
    for p in RATES:
        hits = hits_ne = n_ne = 0
        for r in range(REPEATS if p else 1):
            for c, want in zip(cases, truth):
                w = corrupt(c.world, seed=1000 * r + c.seed, rate=p) if p else c.world
                try:
                    got = solve(w)[0]
                except Exception:
                    got = ()
                ok = got == want
                hits += ok
                if want:
                    hits_ne += ok
                    n_ne += 1
        n = len(cases) * (REPEATS if p else 1)
        curve.append((p, hits / n))
        curve_ne.append((p, hits_ne / max(1, n_ne)))
        print(f"  {p:>6.2f} {hits/n:>10.3f} {hits_ne/max(1,n_ne):>10.3f}",
              flush=True)

    rmse, k, F = fit(curve)
    rmse_ne, k_ne, F_ne = fit(curve_ne)
    print(f"\nfitted on THESE cases:")
    print(f"  all cases      k = {k:>5.2f}  F = {F:.3f}  rmse {rmse:.4f}")
    print(f"  non-empty only k = {k_ne:>5.2f}  F = {F_ne:.3f}  rmse {rmse_ne:.4f}")
    print(f"\n  published fit (300 seeds)   k = {PUBLISHED_K:.2f}")
    print(f"  ablation on these 40 cases  k_eff = {ABLATION_K_EFF:.2f}")

    pop = abs(k - PUBLISHED_K) / PUBLISHED_K
    inter = (k - ABLATION_K_EFF) / ABLATION_K_EFF if ABLATION_K_EFF else float("nan")
    print(f"\n  population effect  |k_here - k_published|/k_published = {pop:.1%}")
    print(f"  interaction effect (k_here - k_eff)/k_eff             = {inter:+.1%}")
    if inter > 0.20:
        print(f"\n-> INTERACTIONS DOMINATE. The sweep's exponent exceeds what "
              f"single-claim\n   ablation predicts on the same cases, so the "
              f"answer depends on claim\n   COMBINATIONS. A read set, which is a "
              f"single-claim dependency, UNDERSTATES\n   what the reader must "
              f"recover by {inter:.0%}.")
    elif pop > 0.20:
        print(f"\n-> POPULATION, not interactions. The gap is the case mix.")
    else:
        print(f"\n-> neither effect is large; k is stable and close to the "
              f"ablation prediction.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n_cases": N_CASES, "empty_answers": empty, "repeats": REPEATS,
         "curve_all": curve, "curve_non_empty": curve_ne,
         "fit_all": {"k": k, "F": F, "rmse": rmse},
         "fit_non_empty": {"k": k_ne, "F": F_ne, "rmse": rmse_ne},
         "published_k": PUBLISHED_K, "ablation_k_eff": ABLATION_K_EFF,
         "population_effect": pop, "interaction_effect": inter}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
