"""Carried ambiguity: a derivation instead of a fourth slogan.

Three formulations of *when is carried ambiguity cheap* have now failed or been
thinned -- hypothesis size (wrong), collision cost (a different quantity that
agreed by accident), and dependency under the carried perturbation (right
variable, two data points, no form).

There is a derivation available. Carrying **at most one spurious claim of kind
K** decides exactly when no single deletion of a K claim changes the answer. So
with ``d`` the per-deletion dependency and ``n`` the number of K claims:

    decided  =  P(all n deletions inert)  =  (1 - d)^n   under independence

No free parameter: ``d`` and ``n`` are both measured. **This is a test of
independence, not a fit** -- the identity is exact given it, so the residual
means something specific, namely correlation between deletions of the same kind.

Measured on the true world, so it stays computable offline like the rest of the
audit -- no reader involved.

Run: uv run python -u scripts/decidedness_law.py
"""

from __future__ import annotations

import json
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve

OUT = Path("runs/decidedness_law.json")
N = 60


def measure(kind: str, non_empty_only: bool) -> dict | None:
    """(d, n, observed decided) for one claim kind, over the true worlds.

    ``non_empty_only`` is not a refinement, it is the correct population. On a
    case whose answer is already empty almost every deletion is inert, so a
    pooled decidedness floors at the empty-answer share -- 45% here -- and
    measures the case mix rather than the kind. Five kinds read exactly 0.433
    pooled, which is that share, and it was nearly reported as a result.
    """
    per_case_d, per_case_n, decided = [], [], []
    for s in range(N):
        case = generate(s)
        base = solve(case.world)[0]
        if non_empty_only and not base:
            continue
        idx = [i for i, c in enumerate(case.world.claims)
               if c.predicate == kind]
        if not idx:
            continue
        hits = []
        for i in idx:
            trimmed = replace(case.world, claims=tuple(
                c for j, c in enumerate(case.world.claims) if j != i))
            hits.append(solve(trimmed)[0] != base)
        per_case_d.append(statistics.mean(hits))
        per_case_n.append(len(idx))
        decided.append(not any(hits))
    if not decided:
        return None
    return {"d": statistics.mean(per_case_d),
            "n": statistics.mean(per_case_n),
            "decided": statistics.mean(decided),
            "cases": len(decided)}


def main() -> None:
    kinds = ("link", "bridge_on", "load_limit", "mass", "capacity",
             "flooded", "depot", "needs", "demand")
    print("NON-EMPTY cases only. Pooled, five kinds read exactly 0.433 -- the "
          "empty-answer\nshare -- because almost every deletion is inert once "
          "the answer is already empty.\n")
    print(f"{'kind':<12} {'n':>5} {'d':>7} {'predicted':>10} {'observed':>9} "
          f"{'residual':>9}")
    print("-" * 56)
    rows, resid = {}, []
    for kind in kinds:
        m = measure(kind, non_empty_only=True)
        if m is None:
            continue
        pred = (1.0 - m["d"]) ** m["n"]
        r = m["decided"] - pred
        rows[kind] = {**m, "predicted": pred, "residual": r}
        resid.append(r)
        print(f"{kind:<12} {m['n']:>5.1f} {m['d']:>7.3f} {pred:>10.3f} "
              f"{m['decided']:>9.3f} {r:>+9.3f}", flush=True)

    multi = {k: v for k, v in rows.items() if v["n"] > 1.5}
    single = {k: v for k, v in rows.items() if v["n"] <= 1.5}
    print(f"\n  mean |residual| overall:              "
          f"{statistics.mean(abs(x) for x in resid):.3f}")
    if single:
        print(f"  singleton kinds (n=1, exact by construction): "
              f"{', '.join(sorted(single))}")
        print(f"    mean |residual| there:              "
              f"{statistics.mean(abs(v['residual']) for v in single.values()):.3f}")
    if multi:
        mr = statistics.mean(v["residual"] for v in multi.values())
        print(f"  multi-claim kinds:                    "
              f"{', '.join(sorted(multi))}")
        print(f"    mean SIGNED residual there:         {mr:+.3f}")

    print()
    if multi and statistics.mean(v["residual"] for v in multi.values()) > 0.05:
        print(f"-> INDEPENDENCE FAILS, AND IN THE DIRECTION PREDICTED. Observed "
              f"decidedness exceeds\n   (1-d)^n on the multi-claim kinds by "
              f"{statistics.mean(v['residual'] for v in multi.values()):+.3f}: "
              f"deletions of the same kind are POSITIVELY\n   CORRELATED, "
              f"because the structural redundancy that makes one claim inert "
              f"makes\n   several inert at once. The product of marginals is a "
              f"LOWER BOUND on how often\n   carrying that kind will decide.")
        print(f"\n   That is the usable form: (1-d)^n is a floor, computable "
              f"offline from the world\n   alone, and the true decidedness is "
              f"at least that.")
    elif multi:
        print(f"-> independence holds to "
              f"{statistics.mean(abs(v['residual']) for v in multi.values()):.3f} "
              f"mean absolute error, so (1-d)^n is\n   a usable point estimate "
              f"rather than a bound.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n_cases": N, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
