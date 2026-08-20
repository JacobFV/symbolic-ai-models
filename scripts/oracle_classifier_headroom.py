"""What would a perfect sentence classifier actually buy?

The decomposition says the classifier is the lowest factor in all five relations
— 0.158 to 0.536 — with the proposer at 0.735-0.937 and the ranker at 0.759-0.889
around it. The proposed critical path is to replace that one component with
something that can condition evidence on evidence.

**Its value can be bounded without building it.** Replace the classifier with an
oracle — a sentence is labelled for relation `R` exactly when it contains a gold
`R` filler — and leave the proposer, the ranker and the supervision untouched.
What comes out is the ceiling that fixing the classifier reaches, and it needs no
encoder, no dependency and no scope decision.

Three arms per relation: the learned classifier, the oracle, and the hand-written
reader where one exists, so the ceiling can be read against the thing it would
have to beat.

Predicted before running: the oracle lands near `contain × propose × ranker` —
about **0.36 for `parent`** and **0.42 for `headquarters`** — which would put a
perfect classifier just *below* the hand-written reader's 0.393 on `parent`. If
that holds it is the most consequential number in the arm: it says fixing the
binding factor completely still does not beat four regexes on this corpus, and
the ceiling is the corpus rather than the model.

Run: uv run python -u scripts/oracle_classifier_headroom.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (CapitalisedMentions,
                                             LearnedSpanReader, PhraseMentions,
                                             _units)
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm, read_country, read_hq, read_parent

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v2.jsonl")
OUT = Path("runs/oracle_classifier_headroom.json")
FOLDS = 4
RELATIONS = ("parent", "country", "headquarters", "founder", "industry")
HAND = {"parent": read_parent, "country": read_country, "headquarters": read_hq}


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
    print(f"    {'relation':<14}{'learned':>9}{'ORACLE clf':>12}{'hand':>8}"
          f"{'oracle/learned':>16}")

    out = {}
    for relation in RELATIONS:
        learned_ok = oracle_ok = n = 0
        for fold in range(FOLDS):
            te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
            tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
            prop = PhraseMentions.induce(
                [v for d in tr for v in (d.get(relation) or [])])
            reader = LearnedSpanReader(
                mentions=prop, extra_features=R.frame_features,
                extra_role_features=R.role_frame_features).fit(
                [R.supervise_distant(d) for d in tr])
            for d in te:
                gold = [x for x in (d.get(relation) or []) if x]
                if not gold:
                    continue
                n += 1
                g_norm = [norm(x) for x in gold]

                res = reader.run(d["intro"], query=d.get("title", ""))
                best = None
                for i, c in enumerate(res.claims):
                    v = c.roles.get("value")
                    if c.predicate == relation and isinstance(v, EntityRef):
                        if best is None or res.confidence_of(i) > best[0]:
                            best = (res.confidence_of(i), v.id)
                learned_ok += bool(best) and norm(best[1]) in g_norm

                # ORACLE: the classifier is replaced by the gold containment
                # test. Everything downstream -- proposer, ranker, role filling --
                # is the fitted reader's own.
                picked = None
                for u in _units(d["intro"]):
                    if not any(x in u.text for x in gold):
                        continue
                    u.query = d.get("title", "")
                    roles, _, _ = reader._fill(
                        u, relation, [], [m.text for m in prop.find(u)])
                    v = roles.get("value")
                    if isinstance(v, EntityRef):
                        picked = v.id
                        if norm(picked) in g_norm:
                            break
                oracle_ok += bool(picked) and norm(picked) in g_norm

        hand_txt = "-"
        if relation in HAND:
            fn = HAND[relation]
            hk = hn = 0
            for d in docs:
                gold = [norm(x) for x in (d.get(relation) or [])]
                if not gold:
                    continue
                hn += 1
                a = fn(d["intro"])
                hk += bool(a) and norm(a) in gold
            hand_txt = f"{hk / hn:.3f}"
        lr, orc = learned_ok / n, oracle_ok / n
        print(f"    {relation:<14}{lr:9.3f}{orc:12.3f}{hand_txt:>8}"
              f"{orc / max(1e-9, lr):15.1f}x")
        out[relation] = {"learned": lr, "oracle_classifier": orc,
                         "hand": hand_txt, "n": n}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
