"""Does the model-class claim hold on a relation with a canonical frame?

Four representations were tried on `parent` and none reached half a point, and the
conclusion drawn was about the **model class**: a linear model over sparse
indicators adds votes and cannot let one piece of evidence condition another. That
finding names its own untested limit — **everything was measured on `parent`**.

`headquarters` is the relation that should disagree. It has a near-canonical frame
(*headquartered in X*, *based in X*): top-5 frame share **0.274** against
`parent`'s 0.179, and it was the one relation where role frames paid earlier
(+33% on the ranker). If the missing operation is conditioning, a relation whose
conditioning is *one frame* should be expressible by a linear model, and features
should pay there.

Both relations, same four arms, gold for all 2,502 articles from the P159 and
P749 fetches. `induce()` is parameterised by relation so the label-aware buckets
are the right ones for each.

Predicted before running: **features pay materially more on `headquarters` than on
`parent`** — the claim becomes "a linear model cannot condition when the frame
inventory is diverse", which is a real qualification rather than a retraction. If
`headquarters` behaves exactly like `parent`, the model-class claim survives its
own named limit and gets stronger.

Run: uv run python -u scripts/model_class_across_relations.py
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.argument_structure import structural_features
from scripts.explicit_conjunctions import conjunction_features
from scripts.label_aware_groups import BUCKETS, MIN_COUNT
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale.jsonl")
OUT = Path("runs/model_class_across_relations.json")
FOLDS = 4
_WORD = re.compile(r"[a-z][a-z'-]+")


def induce_for(train_docs, relation: str) -> dict[str, int]:
    """Label-aware buckets for one relation. Total order, so no hash dependence."""
    pos: Counter = Counter()
    neg: Counter = Counter()
    npos = nneg = 0
    for d in train_docs:
        for u in R.supervise_distant(d):
            words = set(_WORD.findall(u.text.lower()))
            if u.claim is not None and u.claim.predicate == relation:
                npos += 1
                pos.update(words)
            else:
                nneg += 1
                neg.update(words)
    if not npos or not nneg:
        return {}
    scores = {}
    for w in set(pos) | set(neg):
        c = pos[w] + neg[w]
        if c < MIN_COUNT:
            continue
        scores[w] = math.log(((pos[w] + 1) / (npos + 2))
                             / ((c + 1) / (npos + nneg + 2)))
    if not scores:
        return {}
    order = sorted(scores, key=lambda w: (scores[w], w))
    per = max(1, len(order) // BUCKETS)
    return {w: min(i // per, BUCKETS - 1) for i, w in enumerate(order)}


def gold_for(d, relation, rel):
    if relation == "parent":
        return [norm(x) for x in (d.get("parent") or [])]
    return [norm(x) for x in (rel.get(d["qid"], {}).get(relation) or [])]


def main() -> None:
    R.PARENTS, R.RELATIONS = CORPUS, RELS
    docs = R.corpus()
    rel = {json.loads(x)["qid"]: json.loads(x)
           for x in RELS.read_text().splitlines() if x.strip()}
    print(f"{len(docs)} articles")

    results = {}
    for relation in ("parent", "headquarters"):
        print(f"\n=== {relation}")
        print(f"    {'arm':<22}{'coverage':>10}{'correct':>9}{'precision':>11}"
              f"{'k/n':>12}")
        base_k = None
        for arm in ("baseline", "+ structure", "+ conjunctions", "+ lexical"):
            ok = ans = n = 0
            for fold in range(FOLDS):
                te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
                tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
                groups = {} if arm == "baseline" else induce_for(tr, relation)
                if arm == "baseline":
                    erf, ef = R.role_frame_features, R.frame_features
                elif arm == "+ structure":
                    erf = (lambda p, r, c, j, u, g=groups:
                           structural_features(p, r, c, j, u, g))
                    ef = R.frame_features
                elif arm == "+ conjunctions":
                    erf = (lambda p, r, c, j, u, g=groups:
                           conjunction_features(p, r, c, j, u, g))
                    ef = R.frame_features
                else:
                    erf = R.role_frame_features

                    def ef(u, m, g=groups):
                        inside = {i for x in m for i in range(x.start, x.end)}
                        extra = [f"lg={g[t.text.lower()]}" for t in u.tokens
                                 if t.kind == "word" and t.start not in inside
                                 and t.text.lower() in g]
                        return list(R.frame_features(u, m)) + list(
                            dict.fromkeys(extra))

                reader = LearnedSpanReader(
                    mentions=CapitalisedMentions(), extra_features=ef,
                    extra_role_features=erf).fit(
                    [R.supervise_distant(d) for d in tr])
                for d in te:
                    gold = gold_for(d, relation, rel)
                    if not gold:
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
                        ok += norm(best[1]) in gold
            if base_k is None:
                base_k = ok
            print(f"    {arm:<22}{ans / n:10.3f}{ok / n:9.3f}"
                  f"{ok / max(1, ans):11.3f}{f'{ok}/{n}':>12}"
                  f"{'' if arm == 'baseline' else f'   {ok - base_k:+d}'}")
            results[f"{relation}:{arm}"] = {
                "coverage": ans / n, "correct": ok / n,
                "precision": ok / max(1, ans), "k": ok, "n": n,
                "delta_articles": 0 if arm == "baseline" else ok - base_k}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
