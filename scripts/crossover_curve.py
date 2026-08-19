"""The crossover, measured on a curve instead of two points.

`notes/findings/...-ten-times-the-text...` extrapolates that matching four
hand-written patterns needs **10⁵–10⁶ articles**, from classifier recall growing
**1.54x per decade** between two corpora: 0.256 at 168 articles and 0.395 at
1,661. That is a two-point fit — which `CLAUDE.md` names as a thing to distrust —
and the two points came from *different files*, the smaller of which is a
relevance-ordered prefix of the same search.

This measures the curve inside one code path at four sizes, on **shuffled**
subsamples of the closed corpus, because a prefix is not a sample
(`notes/lessons/2026-08-19-a-prefix-is-not-a-sample.md`). The reader is fitted
and cross-validated **within** each subsample, so a smaller corpus means less
training data as well as fewer test articles — which is the thing being measured.

Predicted before running: the fitted exponent comes out **below** 1.54x per
decade, because the 168-article corpus was the head of a relevance ranking and
its articles are the canonical ones — a small corpus that is easier than a random
small corpus makes the growth look steeper than it is. If so the crossover moves
*further away* than 10⁵–10⁶, which is the uncomfortable direction.

Run: uv run python -u scripts/crossover_curve.py
"""

from __future__ import annotations

import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
OUT = Path("runs/crossover_curve.json")
SIZES = (200, 500, 1000, 2502)
SEEDS = (11, 12, 13)
FOLDS = 4
#: What the hand-written state-first reader scores on `parent`, the target.
HAND_TARGET = 0.393


def measure(docs) -> tuple[float, int, int]:
    """Cross-validated `parent` accuracy on this subsample. Returns (rate, k, n)."""
    ok = n = 0
    for fold in range(FOLDS):
        te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        reader = LearnedSpanReader(
            mentions=CapitalisedMentions(), extra_features=R.extra(),
            extra_role_features=R.role_frame_features).fit(
            [R.supervise_distant(d) for d in tr])
        for d in te:
            gold = [norm(x) for x in (d.get("parent") or [])]
            if not gold:
                continue
            n += 1
            res = reader.run(d["intro"], query=d.get("title", ""))
            best = None
            for i, c in enumerate(res.claims):
                v = c.roles.get("value")
                if c.predicate == "parent" and isinstance(v, EntityRef):
                    if best is None or res.confidence_of(i) > best[0]:
                        best = (res.confidence_of(i), v.id)
            ok += bool(best) and norm(best[1]) in gold
    return ok / max(1, n), ok, n


def main() -> None:
    R.PARENTS = CORPUS
    R.RELATIONS = Path("data/artifacts/company_relations_scale.jsonl")
    all_docs = R.corpus()
    print(f"{len(all_docs)} articles; {len(SEEDS)} shuffles x {len(SIZES)} sizes")

    curves = []
    print(f"\n    {'articles':>9}" + "".join(f"{'seed ' + str(s):>14}"
                                             for s in SEEDS) + f"{'mean':>9}")
    by_size: dict[int, list[float]] = {}
    for n in SIZES:
        row = []
        for seed in SEEDS:
            order = list(all_docs)
            random.Random(seed).shuffle(order)
            rate, k, tot = measure(order[:n])
            row.append(rate)
            curves.append({"n": n, "seed": seed, "rate": rate, "k": k,
                           "tested": tot})
        by_size[n] = row
        print(f"    {n:9d}" + "".join(f"{r:>9.3f} ({c['k']:3d})"
                                      for r, c in zip(row, curves[-len(SEEDS):]))
              + f"{statistics.mean(row):9.3f}")

    # Power law through the means: rate = a * n^b
    xs = [math.log(n) for n in SIZES]
    ys = [math.log(statistics.mean(by_size[n])) for n in SIZES]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    b = (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
         / sum((x - mx) ** 2 for x in xs))
    a = math.exp(my - b * mx)
    per_decade = 10 ** b
    need = (HAND_TARGET / a) ** (1 / b) if b > 0 else float("inf")
    print(f"\n    fitted rate = {a:.4f} * n^{b:.3f}   "
          f"({per_decade:.2f}x per decade of text)")
    print(f"    published two-point fit: 1.54x per decade")
    print(f"    articles needed to reach the hand reader's {HAND_TARGET}: "
          f"{need:,.0f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"points": curves, "a": a, "b": b,
                               "per_decade": per_decade,
                               "articles_to_match_hand": need}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
