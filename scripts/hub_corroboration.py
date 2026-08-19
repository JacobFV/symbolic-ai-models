"""The liability and its cure may scale together.

An error about a hub entity is expensive because many queries pass through it —
measured: articles with in-degree ≥1 read at **0.126** against **0.197** for the
rest, and wrong articles carry 1.6x the in-degree of correct ones.

But an entity many companies belong to is also an entity many *articles mention*.
**The redundancy that makes a hub error expensive is the redundancy that makes it
checkable**, and the two grow together by construction. This asks whether that is
true in practice.

The check uses no new reading. For an article `X` whose extracted parent is `A`,
scan the other 1,660 intros for one that mentions **both** `X` and `A`. If a
second, independently written document puts those two names together, the claim
has outside support; if none does, it rests on one sentence in one article.

    corroborated       some other article names both X and A
    uncorroborated     no other article does

Predicted before running:

- **Corroboration is available in proportion to in-degree.** By construction: a
  hub is named more often, so a hub's claim has more chances to be corroborated.
  Expect the corroborated share to rise sharply with in-degree.
- **Corroboration predicts correctness**, and more strongly for hubs — the case
  where it matters. An earlier arm measured that corroboration transfers where
  agreement does not (0.718 against 0.346), on a different task.
- Refuted if corroborated and uncorroborated claims are equally accurate, in
  which case co-occurrence is measuring topic rather than support and the cure
  does not exist.

Run: uv run python -u scripts/hub_corroboration.py
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.learned_reader import auc
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_scale.jsonl")
OUT = Path("runs/hub_corroboration.json")
FOLDS = 4


def main() -> None:
    rows = [json.loads(x) for x in CORPUS.read_text().splitlines() if x.strip()]
    by_qid = {r["qid"]: r for r in rows}
    indeg: Counter = Counter()
    for r in rows:
        for pid in (r.get("current_ids") or [])[:1]:
            indeg[pid] += 1

    R.PARENTS = CORPUS
    docs = R.corpus()
    read: dict[str, str | None] = {}
    for fold in range(FOLDS):
        te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        reader = LearnedSpanReader(
            mentions=CapitalisedMentions(), extra_features=R.extra(),
            extra_role_features=R.role_frame_features).fit(
            [R.supervise_distant(d) for d in tr])
        for d in te:
            res = reader.run(d["intro"], query=d.get("title", ""))
            best = None
            for i, c in enumerate(res.claims):
                v = c.roles.get("value")
                if c.predicate == "parent" and isinstance(v, EntityRef):
                    if best is None or res.confidence_of(i) > best[0]:
                        best = (res.confidence_of(i), v.id)
            read[d["qid"]] = best[1] if best else None

    correct = {q: bool(a) and norm(a) in
               [norm(x) for x in (by_qid[q].get("current") or [])]
               for q, a in read.items()}

    # ---- who else names both? -------------------------------------------
    # An inverted index over article text, so the scan is over the articles
    # that could match rather than over all of them for every claim.
    mentions: dict[str, set[str]] = defaultdict(set)
    lowered = {r["qid"]: r["intro"].lower() for r in rows}
    for r in rows:
        mentions[norm(r["title"])].add(r["qid"])

    corr: dict[str, bool] = {}
    for q, a in read.items():
        if not a:
            continue
        subject = by_qid[q]["title"].lower()
        target = a.lower()
        hits = 0
        for other, text in lowered.items():
            if other == q:
                continue
            if subject in text and target in text:
                hits += 1
                if hits >= 1:
                    break
        corr[q] = hits >= 1

    answered = [q for q in corr]
    print(f"{len(rows)} articles; {len(answered)} answered by the reader")

    def rate(qs):
        return statistics.mean(correct[q] for q in qs) if qs else float("nan")

    yes = [q for q in answered if corr[q]]
    no = [q for q in answered if not corr[q]]
    print(f"\n    {'group':<22} {'claims':>7} {'precision':>10}")
    print(f"    {'corroborated':<22} {len(yes):7d} {rate(yes):10.3f}")
    print(f"    {'uncorroborated':<22} {len(no):7d} {rate(no):10.3f}")
    print(f"    AUC(corroborated -> correct) = "
          f"{auc([1.0 if corr[q] else 0.0 for q in answered if correct[q]], [1.0 if corr[q] else 0.0 for q in answered if not correct[q]]):.3f}")

    print(f"\n    {'in-degree':>10} {'answered':>9} {'corr. share':>12} "
          f"{'prec | corr':>12} {'prec | not':>11}")
    rowsout = {}
    for lo, hi, label in ((0, 0, "0"), (1, 2, "1-2"), (3, 99, "3+")):
        g = [q for q in answered if lo <= indeg.get(q, 0) <= hi]
        gy = [q for q in g if corr[q]]
        gn = [q for q in g if not corr[q]]
        if not g:
            continue
        print(f"    {label:>10} {len(g):9d} {len(gy) / len(g):12.3f} "
              f"{rate(gy):12.3f} {rate(gn):11.3f}")
        rowsout[label] = {"n": len(g), "corroborated_share": len(gy) / len(g),
                          "precision_corroborated": rate(gy),
                          "precision_uncorroborated": rate(gn)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "answered": len(answered),
        "precision_corroborated": rate(yes),
        "precision_uncorroborated": rate(no),
        "n_corroborated": len(yes), "by_indegree": rowsout}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
