"""One reader for seven relations, or seven readers for one each?

`owned_by` reads **0.006** when fitted with all seven relations competing and
**0.058** when fitted with two — a **10x** swing from nothing but how the
supervision is shared. Distant supervision labels a sentence for whichever gold
string it contains, and when two relations are both present the longest match
wins, so a sentence naming a parent *and* an owner is a positive for one and a
**false negative** for the other.

That is a practical question nobody here has measured: extracting seven relations,
do you fit **one multi-class reader** or **seven binary ones**? The joint reader
shares its feature space and costs one fit; the binary readers cost seven and
cannot starve each other.

Predicted before running: **binary wins everywhere, and wins most on the relations
that overlap most**. `owned_by` and `parent` compete directly — both take company
names in ownership sentences — so both should gain, `owned_by` far more since it
loses the tie-break. `industry` and `legal_form` take disjoint value types and
should barely move. If binary does *not* win, the joint reader's shared features
are worth more than the label collisions cost, which would be the more
interesting outcome.

Run: uv run python -u scripts/relation_competition.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import LearnedSpanReader, PhraseMentions
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm
from scripts.supervise_through_proposer import supervise_via

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v3.jsonl")
OUT = Path("runs/relation_competition.json")
FOLDS = 4
ALL = ("parent", "country", "headquarters", "founder", "industry",
       "owned_by", "legal_form")


def measure(docs, relation, supervised_with, *, multilabel=False
            ) -> tuple[float, int, int]:
    """Fit with `supervised_with` competing for labels; score `relation`."""
    ok = n = 0
    for fold in range(FOLDS):
        te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        prop = PhraseMentions.induce(
            [v for d in tr for v in (d.get(relation) or [])], alias_heads=True)
        reader = LearnedSpanReader(
            mentions=prop, extra_features=R.frame_features,
            extra_role_features=R.role_frame_features).fit(
            [supervise_via(d, prop, supervised_with, multilabel=multilabel)
             for d in tr])
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
            ok += bool(best) and norm(best[1]) in gold
    return ok / max(1, n), ok, n


def main() -> None:
    R.PARENTS, R.RELATIONS = CORPUS, RELS
    docs = R.corpus()
    rel = {json.loads(x)["qid"]: json.loads(x)
           for x in RELS.read_text().splitlines() if x.strip()}
    for d in docs:
        for r_ in ALL:
            if r_ != "parent":
                d[r_] = rel.get(d["qid"], {}).get(r_) or []
    print(f"{len(docs)} articles, {len(ALL)} relations\n")
    print(f"    {'relation':<14}{'joint':>8}{'binary':>8}"
          f"{'JOINT+MULTILABEL':>18}{'vs joint':>10}{'vs binary':>11}")

    out = {}
    for relation in ALL:
        R.RELS = ALL
        j, jk, n = measure(docs, relation, ALL)
        m, mk, _ = measure(docs, relation, ALL, multilabel=True)
        R.RELS = (relation,)
        b, bk, _ = measure(docs, relation, (relation,))
        print(f"    {relation:<14}{j:8.3f}{b:8.3f}{m:18.3f}"
              f"{(m / j if j else float('inf')):9.1f}x"
              f"{(m / b if b else float('inf')):10.1f}x")
        out[relation] = {"joint": j, "binary": b, "joint_multilabel": m,
                         "k_joint": jk, "k_binary": bk, "k_multilabel": mk,
                         "n": n}

    tot_j = sum(v["k_joint"] for v in out.values())
    tot_b = sum(v["k_binary"] for v in out.values())
    tot_m = sum(v["k_multilabel"] for v in out.values())
    print(f"\n    total correct: joint {tot_j}, binary {tot_b} "
          f"({tot_b / max(1, tot_j):.2f}x at SEVEN fits), "
          f"joint+multilabel {tot_m} ({tot_m / max(1, tot_j):.2f}x at ONE)")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
