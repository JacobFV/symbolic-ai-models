"""The prospective test: were the predictions written before fitting correct?

The triage statistics are three-for-three on the five relations they were derived
from, which is not a test. `legal_form` and `owned_by` were fetched afterwards,
their statistics computed, and the predictions recorded in
`notes/autonomy/predictions.jsonl` **before any reader was fitted on either**.

    relation      n     containment  lexicon gap  proposal|cap  positional
    legal_form   1832         0.054        0.150         0.076        7.0x
    owned_by     1199         0.547        0.012         0.657        1.8x

Predicted: `legal_form` is a proposer *and* lexicon *and* position case — its
model-free ceiling under the capitalised proposer is 0.054 x 0.076 = **0.004** —
and `owned_by` is a `parent`-shaped model problem where nothing cheap is
available.

Four arms, and the floor beside every one, because a floor inverted a ranking on
this corpus once already.

Run: uv run python -u scripts/prospective_triage.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (CapitalisedMentions,
                                             LearnedSpanReader, PhraseMentions)
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.induced_aliases import induce_aliases
from scripts.multi_relation_world import norm
from scripts.sentence_position import position_features
from scripts.supervise_through_proposer import supervise_via

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v3.jsonl")
OUT = Path("runs/prospective_triage.json")
FOLDS = 4
RELATIONS = ("legal_form", "owned_by")


def main() -> None:
    R.PARENTS, R.RELATIONS = CORPUS, RELS
    docs = R.corpus()
    rel = {json.loads(x)["qid"]: json.loads(x)
           for x in RELS.read_text().splitlines() if x.strip()}
    for d in docs:
        for r_ in RELATIONS:
            d[r_] = rel.get(d["qid"], {}).get(r_) or []
    R.RELS = RELATIONS
    print(f"{len(docs)} articles\n")
    print(f"    {'relation':<12}{'arm':<26}{'correct':>9}{'floor':>8}"
          f"{'above':>8}{'k/n':>11}")

    out = {}
    for relation in RELATIONS:
        vals = [[norm(x) for x in (d.get(relation) or [])] for d in docs
                if d.get(relation)]
        c = Counter(v for vs in vals for v in vs)
        top = c.most_common(1)[0][0]
        floor = sum(1 for vs in vals if top in vs) / len(vals)

        for arm in ("capitalised + literal sup.", "phrase + proposer sup.",
                    "+ induced aliases", "+ position"):
            ok = n = 0
            for fold in range(FOLDS):
                te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
                tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
                if arm == "capitalised + literal sup.":
                    prop = CapitalisedMentions()
                    sup = [R.supervise_distant(d) for d in tr]
                else:
                    fillers = [v for d in tr for v in (d.get(relation) or [])]
                    prop = PhraseMentions.induce(fillers, alias_heads=True)
                    if arm in ("+ induced aliases", "+ position"):
                        al = induce_aliases(tr, relation)
                        if al:
                            prop.aliases = {**prop.aliases, **al}
                    sup = [supervise_via(d, prop, RELATIONS) for d in tr]
                reader = LearnedSpanReader(
                    mentions=prop,
                    extra_features=(position_features if arm == "+ position"
                                    else R.frame_features),
                    extra_role_features=R.role_frame_features).fit(sup)
                for d in te:
                    gold = [norm(x) for x in (d.get(relation) or [])]
                    if not gold:
                        continue
                    n += 1
                    res = reader.run(d["intro"], query=d.get("title", ""))
                    best = None
                    for i, cl in enumerate(res.claims):
                        v = cl.roles.get("value")
                        if cl.predicate == relation and isinstance(v, EntityRef):
                            if best is None or res.confidence_of(i) > best[0]:
                                best = (res.confidence_of(i), v.id)
                    ok += bool(best) and norm(best[1]) in gold
            print(f"    {relation:<12}{arm:<26}{ok / n:9.3f}{floor:8.3f}"
                  f"{ok / n - floor:+8.3f}{f'{ok}/{n}':>11}")
            out[f"{relation}:{arm}"] = {"correct": ok / n, "floor": floor,
                                        "above_floor": ok / n - floor,
                                        "k": ok, "n": n}
        print()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
