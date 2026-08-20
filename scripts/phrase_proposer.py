"""Does a phrase proposer make an unanswerable relation answerable?

`industry` reads **0.000** — not because it is hard, but because
`CapitalisedMentions` proposes runs of capitalised words and 97.9% of `industry`
values are lowercase. The reader is structurally incapable of producing a
candidate, and it says so by returning nothing.

`PhraseMentions` proposes from a **learned phrase inventory** — the fillers seen
in training, plus any productive suffix they share (`… industry`, `… services`),
so an unseen `pharmaceutical industry` is proposable from a suffix — and keeps
capitalised runs alongside, so proper-noun relations are unaffected.

Both proposers, both relation kinds, so the change is measured where it should
help *and* where it should not.

Predicted before running: `industry` moves from 0.000 to something real but
**capped by containment at 0.241** — its gold string appears in only a quarter of
articles — so expect 0.08–0.18. And `parent` should be **unchanged**, because a
phrase inventory learned from company names adds candidates a capitalised run
already proposed. If `parent` degrades, the extra candidates are noise and the
proposer is not free.

Run: uv run python -u scripts/phrase_proposer.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (CapitalisedMentions,
                                             LearnedSpanReader, PhraseMentions)
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v2.jsonl")
OUT = Path("runs/phrase_proposer.json")
FOLDS = 4
RELATIONS = ("industry", "parent")


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

    results = {}
    for relation in RELATIONS:
        print(f"\n=== {relation}")
        print(f"    {'proposer':<24}{'coverage':>10}{'correct':>9}"
              f"{'precision':>11}{'k/n':>12}")
        for name in ("CapitalisedMentions", "PhraseMentions"):
            ok = ans = n = 0
            for fold in range(FOLDS):
                te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
                tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
                if name == "CapitalisedMentions":
                    prop = CapitalisedMentions()
                else:
                    # The inventory is induced from TRAINING fillers only.
                    fillers = [v for d in tr
                               for v in (d.get(relation) or [])]
                    prop = PhraseMentions.induce(fillers)
                reader = LearnedSpanReader(
                    mentions=prop, extra_features=R.frame_features,
                    extra_role_features=R.role_frame_features).fit(
                    [R.supervise_distant(d) for d in tr])
                for d in te:
                    g = [norm(x) for x in (d.get(relation) or [])]
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
            print(f"    {name:<24}{ans / n:10.3f}{ok / n:9.3f}"
                  f"{ok / max(1, ans):11.3f}{f'{ok}/{n}':>12}")
            results[f"{relation}:{name}"] = {
                "coverage": ans / n, "correct": ok / n,
                "precision": ok / max(1, ans), "k": ok, "n": n}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
