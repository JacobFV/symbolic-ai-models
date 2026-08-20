"""Can a relation's readability be predicted before a reader is built?

`headquarters` reads at **0.264** and `parent` at **0.116** with the same reader,
the same corpus and the same supervision. The difference is not the reader; it is
the relation. And the two differ measurably *before any reading*: top-5 frame
share **0.274** against **0.179**.

If that generalises it is a **screening statistic** — a way to tell, from the
corpus alone, whether a relation is worth building an extractor for. This fits it
on five relations: `parent` (P749), `country` (P17), `headquarters` (P159),
`founder` (P112) and `industry` (P452), all with gold on the same 2,502 articles.

For each relation, measured independently of any model:

    containment    share of articles with a sentence containing the gold string
                   -- the ceiling distant supervision can reach
    top-5 share    how concentrated the content-word frames are
    singletons     share of frames occurring exactly once
    mean count     instances per distinct frame

and then, from the same reader on all five, the accuracy those predict or fail to.

Predicted before running: **top-5 frame share is the strongest single predictor**
and containment is second, because one says how often the relation is *stated in
a learnable way* and the other how often it is stated at all. If neither predicts,
readability is a property of the relation that has to be measured by building the
reader, which is a much less useful answer and worth knowing.

Run: uv run python -u scripts/relation_readability.py
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (CapitalisedMentions,
                                             LearnedSpanReader, _units)
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v2.jsonl")
OUT = Path("runs/relation_readability.json")
FOLDS = 4
STOP = frozenset("a an the of in to for and or is was are were be been by on at "
                 "as its it his her their this that with from".split())
RELATIONS = ("parent", "country", "headquarters", "founder", "industry")


def gold(d, relation, rel):
    if relation == "parent":
        return d.get("parent") or []
    return rel.get(d["qid"], {}).get(relation) or []


def frame_stats(docs, relation, rel) -> dict:
    """Corpus-side statistics. No model, no supervision beyond the gold strings."""
    cm = CapitalisedMentions()
    frames: Counter = Counter()
    have = reach = 0
    for d in docs:
        g = gold(d, relation, rel)
        if not g:
            continue
        have += 1
        hit = False
        for u in _units(d["intro"]):
            f = next((x for x in g if x and x in u.text), None)
            if not f:
                continue
            hit = True
            ments = cm.find(u)
            tgt = next((m for m in ments if m.text == f), None)
            if tgt is None:
                continue
            words = [w for w in u.tokens if w.kind in ("word", "num")]
            prev = max((m.end for m in ments if m.end <= tgt.start),
                       default=u.start)
            gap = [w.text.lower() for w in words if prev <= w.start < tgt.start]
            content = [w for w in gap if w not in STOP]
            frames[content[-1] if content else ""] += 1
        reach += hit
    n = sum(frames.values())
    return {"articles_with_gold": have,
            "containment": reach / max(1, have),
            "instances": n,
            "types": len(frames),
            "top5": sum(v for _, v in frames.most_common(5)) / max(1, n),
            "singletons": sum(1 for v in frames.values() if v == 1) / max(1, len(frames)),
            "mean_count": n / max(1, len(frames))}


def read_accuracy(docs, relation, rel) -> dict:
    ok = ans = n = 0
    for fold in range(FOLDS):
        te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        reader = LearnedSpanReader(
            mentions=CapitalisedMentions(), extra_features=R.frame_features,
            extra_role_features=R.role_frame_features).fit(
            [R.supervise_distant(d) for d in tr])
        for d in te:
            g = [norm(x) for x in gold(d, relation, rel)]
            if not g:
                continue
            n += 1
            res = reader.run(d["intro"], query=d.get("title", ""))
            best = None
            for i, c in enumerate(res.claims):
                v = c.roles.get("value")
                if c.predicate == relation and isinstance(v, EntityRef):
                    if best is None or res.confidence_of(i) > best[0]:
                        best = (res.confidence_of(i), v.id)
            if best:
                ans += 1
                ok += norm(best[1]) in g
    return {"correct": ok / max(1, n), "coverage": ans / max(1, n),
            "k": ok, "n": n}


def pearson(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return num / den if den else float("nan")


def main() -> None:
    R.PARENTS, R.RELATIONS = CORPUS, RELS
    docs = R.corpus()
    rel = {json.loads(x)["qid"]: json.loads(x)
           for x in RELS.read_text().splitlines() if x.strip()}
    # `supervise_distant` labels from the doc dict, so every relation's gold has
    # to be on it or the reader is trained on nothing for that relation.
    for d in docs:
        for r_ in RELATIONS:
            if r_ != "parent":
                d[r_] = rel.get(d["qid"], {}).get(r_) or []
    # `supervise_distant` only labels the relations in `R.RELS`. Without this
    # `founder` and `industry` are never supervised and read 0.000 -- which looks
    # exactly like "these relations are unreadable" and is not.
    R.RELS = RELATIONS

    print(f"{len(docs)} articles\n")
    print(f"    {'relation':<14}{'gold':>7}{'contain':>9}{'top5':>7}"
          f"{'singl':>7}{'mean n':>8}   {'coverage':>9}{'CORRECT':>9}{'k/n':>11}")
    rows = {}
    for relation in RELATIONS:
        fs = frame_stats(docs, relation, rel)
        ra = read_accuracy(docs, relation, rel)
        rows[relation] = {**fs, **ra}
        print(f"    {relation:<14}{fs['articles_with_gold']:7d}"
              f"{fs['containment']:9.3f}{fs['top5']:7.3f}"
              f"{fs['singletons']:7.3f}{fs['mean_count']:8.2f}   "
              f"{ra['coverage']:9.3f}{ra['correct']:9.3f}"
              f"{f'{ra[chr(107)]}/{ra[chr(110)]}':>11}")

    ys = [rows[r]["correct"] for r in RELATIONS]
    print(f"\n    correlation with `correct` over {len(RELATIONS)} relations")
    for stat in ("containment", "top5", "singletons", "mean_count"):
        xs = [rows[r][stat] for r in RELATIONS]
        print(f"      {stat:<14} r = {pearson(xs, ys):+.3f}")
    print("\n    five points: a correlation here is a direction, not a law.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
