"""Argument structure, at the cheapest level: who comes before the trigger.

Perfect lexical knowledge of which words are triggers is worth **0.005**. So the
ceiling is not "which words signal ownership"; what is left is **structure** —
given a sentence containing `subsidiary`, deciding whether it states the relation
*about this subject* and *which mention fills the slot*.

The current ranker sees a candidate's index, the words either side, and the token
path back to the **previous mention**. It never sees the **subject**, which the
ABI has carried since `Reader.run(query=...)` was wired up, and it never sees
where the trigger sits relative to the two arguments. Those are argument
structure at the cheapest possible level, and they need no parser — none is
installed and none is being added.

    S T C     the subject, then a trigger, then the candidate
              "Hulu is a subsidiary of Disney"          -> candidate is parent
    C T S     the reverse
              "Disney acquired Hulu"                    -> candidate is parent
    T S C     trigger first
              "A subsidiary of Disney, Hulu was ..."    -> ambiguous

Predicted before running: this helps **more than the lexical grouping did**,
because it is the dimension the feature set is missing rather than one it already
covers. A gain of 0.01–0.03 on `parent`. If it buys as little as the lexical
grouping, then neither lexis nor cheap order is the missing thing, and the
argument for a representation that carries real syntax gets much stronger.

Run: uv run python -u scripts/argument_structure.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.label_aware_groups import BUCKETS, induce
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
OUT = Path("runs/argument_structure.json")
FOLDS = 4


def subject_spans(u, ments):
    """Mentions that are the article's subject, from the query the ABI carries."""
    q = (u.query or "").lower()
    if not q:
        return []
    return [m for m in ments
            if m.text.lower() in q or q in m.text.lower()]


def structural_features(pred, role, cands, j, u, groups):
    """Where the subject, the trigger and the candidate sit, in that order."""
    base = list(R.role_frame_features(pred, role, cands, j, u))
    t = cands[j]
    subs = subject_spans(u, cands)
    words = [w for w in u.tokens if w.kind == "word"]
    trig = [w for w in words
            if groups.get(w.text.lower(), 0) >= BUCKETS - 2]

    base.append(f"is.subj={int(bool(subs) and any(s.start == t.start for s in subs))}")
    base.append(f"n.trig={min(len(trig), 3)}")
    if not subs:
        base.append("order=no-subject")
        # A sentence that never names the subject is the pronoun case, and the
        # relation is about the document rather than about anything in view.
        base.append(f"trig.before={int(bool(trig) and trig[0].start < t.start)}")
        return base

    s = min(subs, key=lambda m: m.start)
    if s.start == t.start:
        base.append("order=self")
        return base
    lo, hi = (s, t) if s.start < t.start else (t, s)
    between = [w for w in trig if lo.end <= w.start < hi.start]
    base.append(f"order={'S-C' if s.start < t.start else 'C-S'}")
    base.append(f"trig.between={int(bool(between))}")
    if between:
        base.append(f"trig.mid={between[-1].text.lower()}")
        base.append(f"order3={'S-T-C' if s.start < t.start else 'C-T-S'}")
    base.append(f"gap.mentions={min(sum(1 for c in cands if lo.end <= c.start < hi.start), 3)}")
    # Same clause: no sentence-internal punctuation between the two, which is
    # the cheapest stand-in for "these two are arguments of one predicate".
    seg = u.text[lo.end - u.start:hi.start - u.start]
    base.append(f"same.clause={int(not any(ch in seg for ch in ',;:'))}")
    return base


def main() -> None:
    R.PARENTS = CORPUS
    R.RELATIONS = Path("data/artifacts/company_relations_scale.jsonl")
    docs = R.corpus()
    print(f"{len(docs)} articles")

    results = {}
    for arm in ("baseline", "+ argument structure"):
        ok = ans = n = 0
        for fold in range(FOLDS):
            te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
            tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
            groups = induce(tr) if arm != "baseline" else {}
            erf = (R.role_frame_features if arm == "baseline"
                   else (lambda p, r, c, j, u, g=groups:
                         structural_features(p, r, c, j, u, g)))
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

    print(f"\n    {'arm':<22}{'coverage':>10}{'correct':>9}{'precision':>11}"
          f"{'k/n':>12}")
    for arm, r in results.items():
        print(f"    {arm:<22}{r['coverage']:10.3f}{r['correct']:9.3f}"
              f"{r['precision']:11.3f}{f'{r[chr(107)]}/{r[chr(110)]}':>12}")
    d = results["+ argument structure"]["correct"] - results["baseline"]["correct"]
    print(f"    delta correct {d:+.3f}   "
          f"(lexical grouping bought +0.005 on the same split)")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
