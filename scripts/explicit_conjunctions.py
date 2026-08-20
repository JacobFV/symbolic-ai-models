"""Conditioning, written out by hand — the decisive test of the model-class claim.

Four representations bought at most half a point each, and the conclusion drawn
was about the **model class**: *"a linear model over sparse indicators has one way
of using evidence — each feature votes and the votes add — and what the task needs
is for the trigger's identity to select which positional evidence matters."*

That claim has an obvious escape and it deserves to be tried. **A linear model can
express conditioning**, if the conjunctions are constructed explicitly:
`trigger=subsidiary AND candidate-after-trigger` is one indicator, and it fires
only when both hold. Conjunctions are precisely how a bag of features encodes "one
piece of evidence selects another", and nobody had written them.

So this writes them: the trigger word and the trigger's bucket crossed with the
order of subject and candidate, with whether the trigger lies between them, with
same-clause, and with the candidate's index. Everything the previous two arms
supplied separately, now supplied *jointly*.

Predicted before running: **more than the parts bought separately** — 0.01 to
0.02, because conjunctions are the missing operation rather than another
indicator — but still modest, because a conjunction is rarer than either of its
parts and the long tail returns one level up. If conjunctions buy as little as the
parts did, the model-class claim survives the one attack available from inside the
scope, and it survives having been attacked with its own preferred escape.

Run: uv run python -u scripts/explicit_conjunctions.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.argument_structure import structural_features, subject_spans
from scripts.label_aware_groups import BUCKETS, induce
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
OUT = Path("runs/explicit_conjunctions.json")
FOLDS = 4


def conjunction_features(pred, role, cands, j, u, groups):
    """The structural features, plus every one of them crossed with the trigger.

    A cross is the linear model's only way to say *this evidence matters BECAUSE
    that evidence holds*. Both halves were already present as separate votes; the
    question is whether the product is worth more than the sum.
    """
    base = structural_features(pred, role, cands, j, u, groups)
    t = cands[j]
    words = [w for w in u.tokens if w.kind == "word"]
    trig = [w for w in words if groups.get(w.text.lower(), 0) >= BUCKETS - 2]
    if not trig:
        return base + ["cj=no-trigger"]

    # The trigger nearest the candidate is the one most likely to govern it.
    near = min(trig, key=lambda w: abs(w.start - t.start))
    word = near.text.lower()
    bucket = groups.get(word, 0)
    subs = subject_spans(u, cands)
    order = "none"
    between = 0
    if subs:
        s = min(subs, key=lambda m: m.start)
        if s.start != t.start:
            order = "S-C" if s.start < t.start else "C-S"
            lo, hi = (s, t) if s.start < t.start else (t, s)
            between = int(any(lo.end <= w.start < hi.start for w in trig))
    after = int(near.start < t.start)
    seg = u.text[min(near.end, t.start) - u.start:
                 max(near.start, t.end) - u.start]
    clause = int(not any(ch in seg for ch in ",;:"))

    return base + [
        f"cj={word}|{order}",
        f"cj={word}|after={after}",
        f"cj={word}|between={between}",
        f"cj={word}|clause={clause}",
        f"cj={word}|idx={min(j, 3)}",
        f"cjb={bucket}|{order}|after={after}",
        f"cjb={bucket}|between={between}|clause={clause}",
        f"cj3={word}|{order}|after={after}",
    ]


def main() -> None:
    R.PARENTS = CORPUS
    R.RELATIONS = Path("data/artifacts/company_relations_scale.jsonl")
    docs = R.corpus()
    print(f"{len(docs)} articles")

    arms = ("baseline", "+ structure", "+ CONJUNCTIONS")
    results = {}
    for arm in arms:
        ok = ans = n = 0
        for fold in range(FOLDS):
            te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
            tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
            groups = induce(tr) if arm != "baseline" else {}
            if arm == "baseline":
                erf = R.role_frame_features
            elif arm == "+ structure":
                erf = (lambda p, r, c, j, u, g=groups:
                       structural_features(p, r, c, j, u, g))
            else:
                erf = (lambda p, r, c, j, u, g=groups:
                       conjunction_features(p, r, c, j, u, g))
            reader = LearnedSpanReader(
                mentions=CapitalisedMentions(),
                extra_features=R.frame_features,
                extra_role_features=erf).fit(
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

    print(f"\n    {'arm':<18}{'coverage':>10}{'correct':>9}{'precision':>11}"
          f"{'k/n':>12}")
    for arm in arms:
        r = results[arm]
        print(f"    {arm:<18}{r['coverage']:10.3f}{r['correct']:9.3f}"
              f"{r['precision']:11.3f}{f'{r[chr(107)]}/{r[chr(110)]}':>12}")
    b = results["baseline"]["correct"]
    print(f"    delta over baseline:  structure "
          f"{results['+ structure']['correct'] - b:+.3f}   "
          f"conjunctions {results['+ CONJUNCTIONS']['correct'] - b:+.3f}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
