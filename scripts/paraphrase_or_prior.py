"""Which half of the alias gain is reading, and which half is guessing?

Induced aliases lifted `country` +0.207 and `industry` +0.124, and the note had to
admit the mechanism cannot tell a **paraphrase** (`french` → France: a form of the
value, appearing *instead of* it) from a **prior** (`ftse` → London: a correlated
but different entity, appearing *alongside* it or on its own).

They separate cleanly on where the gain lands. Split held-out articles by whether
the gold string appears **literally**:

    literal ABSENT   the alias is the only way to see the relation.
                     A gain here is READING a paraphrase.
    literal PRESENT  the canonical form is already there for the proposer.
                     A gain here is a PRIOR -- the alias is re-ranking, not
                     revealing.

Predicted before running: `country`'s gain concentrates in the **absent** half —
29.3% of its articles state the country only adjectivally, which is exactly the
paraphrase case. `headquarters` and `parent` should show any gain in the
**present** half, because `ftse→London` and `russian→Rostec` are correlations
rather than forms. If `country`'s gain is also in the present half, the whole
mechanism is a prior and the paraphrase story is wrong.

Run: uv run python -u scripts/paraphrase_or_prior.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import LearnedSpanReader, PhraseMentions
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.induced_aliases import induce_aliases
from scripts.multi_relation_world import norm
from scripts.supervise_through_proposer import supervise_via

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v2.jsonl")
OUT = Path("runs/paraphrase_or_prior.json")
FOLDS = 4
RELATIONS = ("parent", "country", "headquarters", "industry")


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
    print(f"{len(docs)} articles\n")
    print(f"    {'relation':<14}{'half':<10}{'n':>6}{'base':>8}{'induced':>9}"
          f"{'delta':>8}   where the gain is")

    out = {}
    for relation in RELATIONS:
        got = {("base", True): [0, 0], ("base", False): [0, 0],
               ("ind", True): [0, 0], ("ind", False): [0, 0]}
        for fold in range(FOLDS):
            te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
            tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
            fillers = [v for d in tr for v in (d.get(relation) or [])]
            al = induce_aliases(tr, relation)
            for arm, aliases in (("base", {}), ("ind", al)):
                prop = PhraseMentions.induce(fillers, alias_heads=True)
                if aliases:
                    prop.aliases = {**prop.aliases, **aliases}
                reader = LearnedSpanReader(
                    mentions=prop, extra_features=R.frame_features,
                    extra_role_features=R.role_frame_features).fit(
                    [supervise_via(d, prop, RELATIONS) for d in tr])
                for d in te:
                    gold = [x for x in (d.get(relation) or []) if x]
                    if not gold:
                        continue
                    present = any(g in d["intro"] for g in gold)
                    g_norm = [norm(x) for x in gold]
                    res = reader.run(d["intro"], query=d.get("title", ""))
                    best = None
                    for i, c in enumerate(res.claims):
                        v = c.roles.get("value")
                        if c.predicate == relation and isinstance(v, EntityRef):
                            if best is None or res.confidence_of(i) > best[0]:
                                best = (res.confidence_of(i), v.id)
                    cell = got[(arm, present)]
                    cell[1] += 1
                    cell[0] += bool(best) and norm(best[1]) in g_norm

        rows = {}
        for present, label in ((False, "ABSENT"), (True, "present")):
            bk, bn = got[("base", present)]
            ik, _ = got[("ind", present)]
            if bn == 0:
                continue
            d_ = (ik - bk) / bn
            rows[label] = {"n": bn, "base": bk / bn, "induced": ik / bn,
                           "delta": d_, "gained": ik - bk}
        tot = sum(r["gained"] for r in rows.values()) or 1
        for label, r in rows.items():
            share = r["gained"] / tot
            print(f"    {relation:<14}{label:<10}{r['n']:6d}{r['base']:8.3f}"
                  f"{r['induced']:9.3f}{r['delta']:+8.3f}   "
                  f"{share:+.0%} of the gain")
        out[relation] = rows

    print("\n    a gain in the ABSENT half is reading a paraphrase;")
    print("    a gain in the present half is a prior re-ranking what was there.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
