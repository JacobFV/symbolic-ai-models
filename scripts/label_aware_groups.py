"""Group words by what they predict, not by where they occur — the prediction test.

The clustering finding ends on a falsifiable claim: *any representation induced
from this corpus alone will fail the same way, however it is induced.* The
failure was specific — distributional similarity put `subsidiary`, `division` and
`owned` in one cluster with `is`, `by` and `company`, because in this genre they
share contexts by construction.

So this induces a grouping that **cannot** fail that way: words are scored by
their association with the *label* rather than by their contexts. `subsidiary`
fires in sentences that state a parent relation; `is` fires in all of them.
Pointwise mutual information with the positive class separates exactly the two
things distributional clustering merged.

Computed **per fold, on training sentences only**, because a word-to-label
statistic fitted on the evaluation is the oldest mistake in this repo.

The point is not that the classifier lacks the words — it has them as features
already. The point is **sharing**: a trigger seen twice sits in the same bucket
as one seen 157 times and borrows its weight, which is the only mechanism by
which a representation can help a long tail.

Predicted before running: the grouping is **clean where clustering was not** —
`subsidiary` and `division` in a high bucket, `is` and `company` in the middle —
and it buys **little or nothing** end to end, because what it shares is a weight
the classifier can already fit for any trigger it has seen twice. If it buys
nothing, the structural claim survives its own test: corpus-internal
representations do not move this ceiling, and the failure is not about *how* they
are induced.

Run: uv run python -u scripts/label_aware_groups.py
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
OUT = Path("runs/label_aware_groups.json")
FOLDS = 4
BUCKETS = 8
MIN_COUNT = 3
_WORD = re.compile(r"[a-z][a-z'-]+")


def induce(train_docs) -> dict[str, int]:
    """word -> bucket, by PMI with the positive class. Training sentences only."""
    pos: Counter = Counter()
    neg: Counter = Counter()
    npos = nneg = 0
    for d in train_docs:
        for u in R.supervise_distant(d):
            words = {w for w in _WORD.findall(u.text.lower())}
            if u.claim is not None and u.claim.predicate == "parent":
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
        # Smoothed PMI with the positive class: +1 keeps a word seen twice in
        # one class from scoring infinitely.
        p_wp = (pos[w] + 1) / (npos + 2)
        p_w = (c + 1) / (npos + nneg + 2)
        scores[w] = math.log(p_wp / p_w)
    if not scores:
        return {}
    order = sorted(scores, key=lambda w: scores[w])
    per = max(1, len(order) // BUCKETS)
    return {w: min(i // per, BUCKETS - 1) for i, w in enumerate(order)}


def main() -> None:
    R.PARENTS = CORPUS
    R.RELATIONS = Path("data/artifacts/company_relations_scale.jsonl")
    docs = R.corpus()
    print(f"{len(docs)} articles")

    shown = False
    results = {}
    for arm in ("baseline", "+ label groups"):
        ok = ans = n = 0
        for fold in range(FOLDS):
            te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
            tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
            groups = induce(tr) if arm != "baseline" else {}
            if groups and not shown:
                shown = True
                print(f"    {len(groups)} words in {BUCKETS} buckets "
                      f"(fold 0, training sentences only)")
                for probe in ("subsidiary", "division", "unit", "owned",
                              "acquired", "is", "company", "the"):
                    if probe in groups:
                        print(f"      {probe:<11} bucket {groups[probe]}"
                              f"{'  <- trigger' if groups[probe] >= BUCKETS - 2 else ''}")

            def unit_feats(u, m, g=groups):
                inside = {i for x in m for i in range(x.start, x.end)}
                out = []
                for t in u.tokens:
                    if t.kind == "word" and t.start not in inside:
                        b = g.get(t.text.lower())
                        if b is not None:
                            out.append(f"lg={b}")
                return list(R.frame_features(u, m)) + list(dict.fromkeys(out))

            def role_feats(pred, role, cands, j, u, g=groups):
                base = list(R.role_frame_features(pred, role, cands, j, u))
                t = cands[j]
                words = [w for w in u.tokens if w.kind == "word"]
                prev = max((c.end for c in cands if c.end <= t.start),
                           default=u.start)
                bs = [g.get(w.text.lower()) for w in words
                      if prev <= w.start < t.start]
                bs = [b for b in bs if b is not None]
                if bs:
                    base += [f"lgw={bs[-1]}", f"lgmax={max(bs)}"]
                return base

            reader = LearnedSpanReader(
                mentions=CapitalisedMentions(),
                extra_features=R.frame_features if arm == "baseline" else unit_feats,
                extra_role_features=(R.role_frame_features if arm == "baseline"
                                     else role_feats)).fit(
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
                if best:
                    ans += 1
                    ok += norm(best[1]) in gold
        results[arm] = {"coverage": ans / n, "correct": ok / n,
                        "precision": ok / max(1, ans), "k": ok, "n": n}

    print(f"\n    {'arm':<16}{'coverage':>10}{'correct':>9}{'precision':>11}"
          f"{'k/n':>12}")
    for arm, r in results.items():
        print(f"    {arm:<16}{r['coverage']:10.3f}{r['correct']:9.3f}"
              f"{r['precision']:11.3f}{f'{r[chr(107)]}/{r[chr(110)]}':>12}")
    d = results["+ label groups"]["correct"] - results["baseline"]["correct"]
    print(f"    delta correct {d:+.3f}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
