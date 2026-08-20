"""Acting on the diagnostic: does fixing a flagged lexicon problem pay?

The lexicon-gap diagnostic flagged `industry` at **0.416** — gold `automotive
industry` against text *automotive company* — while calling every other relation
a model problem. A triage rule is only worth having if acting on it pays, so this
acts on it.

Two changes, both induced from the gold alone:

1. **The proposer normalises.** `PhraseMentions(alias_heads=True)` strips the head
   noun shared by the gold values (`… industry`) and maps the remainder back:
   seeing *automotive* anywhere, it proposes the span and reports the canonical
   `automotive industry`.
2. **Supervision goes through the proposer.** Distant supervision labels a
   sentence when it *contains the gold string*, which skips every sentence whose
   answer the proposer could produce but whose literal form is absent. Labelling
   instead when **the proposer can produce the gold from that sentence** aligns
   the two: the reader trains on exactly the sentences it can answer.

The second is the more general point and it is not specific to `industry`. A
sentence that cannot yield the answer is a bad positive; a sentence that can and
is unlabelled is a wasted one.

Predicted before running: `industry` rises from **0.025** toward its prefix-gap
figure — 0.08 to 0.15 — because both changes attack the same 0.416. `parent`
should be **flat**, since company names have no head to strip and no alias is
induced, which is the control that the change is not a general accuracy knob.

Run: uv run python -u scripts/supervise_through_proposer.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (LearnedSpanReader, PhraseMentions,
                                             _units)
from symbolic_ai_core.world import Claim, EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v2.jsonl")
OUT = Path("runs/supervise_through_proposer.json")
FOLDS = 4
RELATIONS = ("industry", "parent")


def supervise_via(doc, proposer, relations):
    """Label a sentence when the PROPOSER can produce a gold value from it."""
    units = _units(doc["intro"])
    for u in units:
        u.query = doc.get("title", "")
        produced = {m.text.lower() for m in proposer.find(u)}
        best = None
        for r_ in relations:
            for g in (doc.get(r_) or []):
                if g and g.lower() in produced:
                    if best is None or len(g) > len(best[1]):
                        best = (r_, g)
        if best:
            u.claim = Claim(predicate=best[0],
                            roles={"value": EntityRef(best[1])})
    return units


def main() -> None:
    R.PARENTS, R.RELATIONS = CORPUS, RELS
    docs = R.corpus()
    rel = {json.loads(x)["qid"]: json.loads(x)
           for x in RELS.read_text().splitlines() if x.strip()}
    for d in docs:
        for r_ in RELATIONS:
            if r_ != "parent":
                d[r_] = rel.get(d["qid"], {}).get(r_) or []
    R.RELS = RELATIONS
    print(f"{len(docs)} articles")

    out = {}
    for relation in RELATIONS:
        print(f"\n=== {relation}")
        print(f"    {'arm':<34}{'coverage':>10}{'correct':>9}"
              f"{'precision':>11}{'k/n':>12}")
        for arm in ("phrase + literal supervision",
                    "alias proposer + literal sup.",
                    "alias proposer + PROPOSER sup."):
            ok = ans = n = 0
            for fold in range(FOLDS):
                te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
                tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
                fillers = [v for d in tr for v in (d.get(relation) or [])]
                prop = PhraseMentions.induce(
                    fillers, alias_heads=(arm != "phrase + literal supervision"))
                sup = ([supervise_via(d, prop, RELATIONS) for d in tr]
                       if arm.endswith("PROPOSER sup.")
                       else [R.supervise_distant(d) for d in tr])
                reader = LearnedSpanReader(
                    mentions=prop, extra_features=R.frame_features,
                    extra_role_features=R.role_frame_features).fit(sup)
                for d in te:
                    gold = [norm(x) for x in (d.get(relation) or [])]
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
            print(f"    {arm:<34}{ans / n:10.3f}{ok / n:9.3f}"
                  f"{ok / max(1, ans):11.3f}{f'{ok}/{n}':>12}")
            out[f"{relation}:{arm}"] = {"coverage": ans / n, "correct": ok / n,
                                        "precision": ok / max(1, ans),
                                        "k": ok, "n": n}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
