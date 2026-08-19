"""The floors I should have computed before quoting five query classes.

`CLAUDE.md` carries a standing rule — *a lift is quoted against a floor or not
quoted at all* — and `symbolic_ai_core/cost.py` enforces it in code, dividing by
``accuracy - floor`` rather than by ``accuracy`` so that a system at its floor
reports infinite cost per unit of capability rather than a small one.

I quoted five end-to-end query classes across three findings this session with
**no floor at all**. This computes them.

**The floor**: return the `N` most frequent items in the reference world, where
`N` is the mean true answer size for that class. It uses **no per-query
information** beyond the answer size, so it is exactly the "memoriser of the
corpus distribution" that a real method has to beat. Collaboration is
heavy-tailed — large institutions co-occur with almost everyone — so this is not
a straw floor for `collaborators`, and that is the class it was expected to bite.

**What it does not change.** The *routing* deltas (+0.015 over the better single
world, −0.026 against the oracle) are differences between two systems on the same
classes, so a per-class floor subtracts from both equally and leaves them intact.
Only the absolute means move.

Run: SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \\
     uv run python -u scripts/query_floors.py
"""

from __future__ import annotations

import json
import random
import statistics
from collections import Counter
from pathlib import Path

from scripts.first_arrow_gazetteer import ROR, v4
from scripts.first_arrow_geo import GeoGazetteer
from scripts.first_arrow_prose import load, score
from scripts.two_arrows_end_to_end import build_worlds, collaborators, v4_recall

OUT = Path("runs/query_floors.json")
SEED = 20260818
N = 2000

#: What the two worlds scored, from the findings being audited, so the lift is
#: computed rather than eyeballed.
MEASURED = {
    "institutions_of(work)":         (0.576, 0.454),
    "collaborators(institution)":    (0.338, 0.417),
    "works_at(institution)":         (0.601, 0.671),
    "works_at_both(A,B)":            (0.282, 0.465),
    "institutions_unique_to(w1,w2)": (0.599, 0.473),
}


def main() -> None:
    rng = random.Random(SEED)
    gz = GeoGazetteer(ROR)
    works = load()
    ids = [w["id"] for w in works]
    ref, _, inv_ref, _, _ = build_worlds(works, gz, v4)
    real = sorted({i for v in ref.values() for i in v})

    inst_pop = [i for i, _ in
                Counter({i: len(v) for i, v in inv_ref.items()}).most_common()]
    work_pop = [w for w, _ in
                Counter({w: len(v) for w, v in ref.items()}).most_common()]

    insts = rng.sample(real, min(N, len(real)))
    inst_pairs = []
    while len(inst_pairs) < N:
        a = rng.choice(real)
        cos = sorted(collaborators(ref, inv_ref, a))
        if cos:
            inst_pairs.append((a, rng.choice(cos)))
    work_pairs = [(a, b) for a, b in
                  ((rng.choice(ids), rng.choice(ids)) for _ in range(N * 4))
                  if a != b][:N]

    def floor_for(truths, pool) -> tuple[float, int]:
        truths = [t for t in truths if t]
        n = int(statistics.mean(len(t) for t in truths)) or 1
        guess = set(pool[:n])
        return score([(guess, t) for t in truths])["f1"], n

    cases = {
        "institutions_of(work)": ([ref[w] for w in ids], inst_pop),
        "collaborators(institution)": (
            [collaborators(ref, inv_ref, i) for i in insts], inst_pop),
        "works_at(institution)": (
            [inv_ref.get(i, set()) for i in insts], work_pop),
        "works_at_both(A,B)": (
            [inv_ref.get(a, set()) & inv_ref.get(b, set())
             for a, b in inst_pairs], work_pop),
        "institutions_unique_to(w1,w2)": (
            [ref[a] - ref[b] for a, b in work_pairs], inst_pop),
    }

    hdr = (f"{'query class':<32} {'floor':>7} {'|ans|':>6} {'precise':>8} "
           f"{'complete':>9} {'best':>7} {'LIFT':>7} {'lost':>7}")
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    for name, (truths, pool) in cases.items():
        fl, n = floor_for(truths, pool)
        p, c = MEASURED[name]
        best = max(p, c)
        lift = best - fl
        rows[name] = {"floor": fl, "mean_answer_size": n, "precise": p,
                      "complete": c, "best": best, "lift": lift,
                      "fraction_of_score_that_was_floor": fl / best}
        print(f"{name:<32} {fl:>7.3f} {n:>6} {p:>8.3f} {c:>9.3f} {best:>7.3f} "
              f"{lift:>7.3f} {fl/best:>6.1%}")

    above = [n for n, r in rows.items() if r["floor"] >= r["best"]]
    print(f"\nclasses where the floor meets or beats the measured system: "
          f"{above if above else 'none — nothing retracts'}")
    worst = max(rows.items(), key=lambda kv: kv[1]["fraction_of_score_that_was_floor"])
    print(f"most affected: {worst[0]} — {worst[1]['fraction_of_score_that_was_floor']:.0%} "
          f"of its score was the floor, so its lift is "
          f"{worst[1]['lift']:.3f} rather than {worst[1]['best']:.3f}")
    print("\nrouting deltas are unaffected: a per-class floor subtracts equally "
          "from both\nsystems, so +0.015 over the better single world and "
          "-0.026 against the oracle stand.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seed": SEED, "n": N, "rows": rows}, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
