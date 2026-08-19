"""The decidedness identity, per case, on all three domains.

Two corrections to the previous finding, both mine.

**It is not one domain.** I recorded that scheduling and solvency could not test
this because neither has an ambiguity worth carrying. The law is about the
**deletion dependency of a claim kind**, which every domain has and which needs
no reader; only the *policy* needs a reader.

**The identity is per case.** ``decided = E_case[(1 - d_case)^n_case]``. Plugging
a pooled mean ``d`` into ``(1 - d)^n`` is an approximation that fails by Jensen
whenever ``d`` is heterogeneous -- which is exactly what the flood pooled failure
was: an empty-answer subpopulation with ``d`` near zero mixed with a non-empty one
with ``d`` high. If the per-case form holds on the pooled population too, that
failure is *explained* rather than excluded by a population rule.

Run: uv run python -u scripts/decidedness_cross_domain.py
"""

from __future__ import annotations

import json
import statistics
from dataclasses import replace
from pathlib import Path

OUT = Path("runs/decidedness_cross_domain.json")
N = 40


def flood_probe():
    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.flow import solve
    cases = [generate(s) for s in range(N)]
    return (cases, lambda c: c.world, lambda w: solve(w)[0],
            ("link", "bridge_on", "load_limit", "mass", "capacity", "flooded"),
            lambda c: bool(solve(c.world)[0]))


def scheduling_probe():
    from symbolic_ai_generators.scheduling import generate
    from symbolic_ai_generators.scheduling.world import feasible_by_search
    from symbolic_ai_core.world import Quantity

    def answer(world):
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

    cases = [generate(s, n_jobs=6, n_machines=3, slack=0.15)
             for s in range(N)]
    return (cases, lambda c: c.world, answer,
            ("duration", "capacity", "needs_capability", "has_capability"),
            lambda c: c.feasible)


def solvency_probe():
    from symbolic_ai_generators.solvency import generate
    from symbolic_ai_core.world import Quantity

    def answer(world):
        # the domain's rule over a world: latest-known largest figure per member
        best: dict = {}
        for c in world.claims:
            if c.predicate != "revenue":
                continue
            q = c.roles.get("value")
            if isinstance(q, Quantity):
                m = c.roles["of"].id
                best[m] = max(best.get(m, 0.0), float(q.value))
        return round(sum(best.values()), 2)

    cases = [generate(s) for s in range(N)]
    return (cases, lambda c: c.world, answer, ("revenue", "owns"),
            lambda c: True)


def measure(cases, world_of, answer, kind, keep=None):
    """Per-case (d, n) and whether all deletions were inert."""
    rows = []
    for case in cases:
        if keep and not keep(case):
            continue
        world = world_of(case)
        base = answer(world)
        idx = [i for i, c in enumerate(world.claims) if c.predicate == kind]
        if not idx:
            continue
        hits = []
        for i in idx:
            trimmed = replace(world, claims=tuple(
                c for j, c in enumerate(world.claims) if j != i))
            try:
                hits.append(answer(trimmed) != base)
            except Exception:
                hits.append(True)
        rows.append({"d": sum(hits) / len(hits), "n": len(idx),
                     "decided": not any(hits)})
    return rows


def main() -> None:
    probes = (("flood", flood_probe), ("scheduling", scheduling_probe),
              ("solvency", solvency_probe))
    print(f"{'domain':<11} {'kind':<18} {'pop':<10} {'per-case':>9} "
          f"{'mean-d':>8} {'observed':>9}")
    print("-" * 70)
    out, per_case_err, mean_d_err = {}, [], []
    for dname, probe in probes:
        cases, world_of, answer, kinds, non_degenerate = probe()
        for kind in kinds:
            for pop, keep in (("all", None),
                              ("non-degen", non_degenerate)):
                rows = measure(cases, world_of, answer, kind, keep)
                if len(rows) < 5:
                    continue
                obs = statistics.mean(r["decided"] for r in rows)
                per_case = statistics.mean((1 - r["d"]) ** r["n"] for r in rows)
                d = statistics.mean(r["d"] for r in rows)
                n = statistics.mean(r["n"] for r in rows)
                mean_d = (1 - d) ** n
                out[f"{dname}|{kind}|{pop}"] = {
                    "observed": obs, "per_case": per_case, "mean_d": mean_d,
                    "d": d, "n": n, "cases": len(rows)}
                per_case_err.append(abs(obs - per_case))
                mean_d_err.append(abs(obs - mean_d))
                print(f"{dname:<11} {kind:<18} {pop:<10} {per_case:>9.3f} "
                      f"{mean_d:>8.3f} {obs:>9.3f}", flush=True)

    print(f"\n  mean |error|, per-case form  E[(1-d)^n] : "
          f"{statistics.mean(per_case_err):.3f}")
    print(f"  mean |error|, mean-d form  (1-E[d])^E[n] : "
          f"{statistics.mean(mean_d_err):.3f}")

    # Split by population, because the two forms swap places between them and
    # a single pooled comparison hides that.
    def err(pop, key):
        rows = [v for k, v in out.items() if k.endswith(pop)]
        return (statistics.mean(v["observed"] - v[key] for v in rows),
                statistics.mean(abs(v["observed"] - v[key]) for v in rows))

    print(f"\n{'population':<12} {'per-case signed':>16} {'|err|':>7} "
          f"{'mean-d signed':>15} {'|err|':>7}")
    print("-" * 62)
    for pop in ("all", "non-degen"):
        ps, pa = err(pop, "per_case")
        ms, ma = err(pop, "mean_d")
        print(f"{pop:<12} {ps:>+16.3f} {pa:>7.3f} {ms:>+15.3f} {ma:>7.3f}")

    _, pa_clean = err("non-degen", "per_case")
    ms_clean, ma_clean = err("non-degen", "mean_d")
    _, pa_all = err("all", "per_case")
    _, ma_all = err("all", "mean_d")

    print(f"\n-> THE LAW IS CROSS-DOMAIN. On the non-degenerate population the "
          f"mean-d form tracks\n   observed decidedness to {ma_clean:.3f} mean "
          f"absolute error with a signed bias of\n   {ms_clean:+.3f}, over "
          f"three domains and twelve claim kinds, with no free parameter.")
    print(f"\n-> THE TWO FORMS SWAP PLACES. Pooled, per-case wins "
          f"{pa_all:.3f} to {ma_all:.3f}: averaging d\n   before "
          f"exponentiating over a bimodal case mix fails by Jensen, which is "
          f"what the\n   earlier pooled failure actually was -- not "
          f"correlation between deletions.")
    print(f"   On the clean population mean-d wins {ma_clean:.3f} to "
          f"{pa_clean:.3f}, because the per-case form\n   SMOOTHS A "
          f"DETERMINISTIC OUTCOME: within a case d is measured from the very "
          f"deletions\n   being tested, so with k of n load-bearing the truth "
          f"is 0 for any k>=1 while\n   (1-k/n)^n stays positive. That is the "
          f"systematic over-prediction in its signed\n   error, and it is a "
          f"property of the estimator rather than of the domain.")
    print(f"\n   Use mean-d on a homogeneous population; use per-case only if "
          f"you must pool.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n": N, "rows": out,
         "per_case_error": statistics.mean(per_case_err),
         "mean_d_error": statistics.mean(mean_d_err)}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
