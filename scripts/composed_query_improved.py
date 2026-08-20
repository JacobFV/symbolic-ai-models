"""The composed query, re-run with everything the reading arm learned.

`parent(c,p) JOIN country(c,X)` — *which groups control companies in X?* — is the
north-star shape: stated in no article, existing only in a world assembled from
all of them. It was last measured at macro F1 **0.109** (union) and **0.036**
(learned), when the learned reader read `parent` at 0.081 and `country` at 0.148.

Since then the same reader reads `parent` at **0.144** and `country` at **0.390**,
through a phrase proposer, supervision routed through it, and aliases induced by
label association. **Composition multiplies**, so the join should move more than
either factor did — or fail to, which would say the improvements are concentrated
on articles that do not co-occur.

Predicted before running: the learned arm improves **more than proportionally**.
`country` rose 2.6x and `parent` 1.8x, so a join needing both right on the same
article should rise toward 4x, from 0.036 to roughly **0.12-0.16**. The union
should improve less, because its `country` half was already carried by the
hand-written nationality map at 0.650.

Run: uv run python -u scripts/composed_query_improved.py
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import LearnedSpanReader, PhraseMentions
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.induced_aliases import induce_aliases
from scripts.multi_relation_world import norm, read_country, read_parent
from scripts.supervise_through_proposer import supervise_via

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v3.jsonl")
OUT = Path("runs/composed_query_improved.json")
FOLDS = 4
PAIR = ("parent", "country")


def main() -> None:
    R.PARENTS, R.RELATIONS = CORPUS, RELS
    docs = R.corpus()
    rel = {json.loads(x)["qid"]: json.loads(x)
           for x in RELS.read_text().splitlines() if x.strip()}
    for d in docs:
        d["country"] = rel.get(d["qid"], {}).get("country") or []
    R.RELS = PAIR
    by_qid = {d["qid"]: d for d in docs}

    read: dict[str, dict[str, str | None]] = defaultdict(dict)
    for fold in range(FOLDS):
        te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        # One reader per relation, because the proposer and its aliases are
        # relation-specific -- which is itself a finding: a shared proposer
        # cannot serve values of different kinds.
        readers = {}
        for r_ in PAIR:
            prop = PhraseMentions.induce(
                [v for d in tr for v in (d.get(r_) or [])], alias_heads=True)
            al = induce_aliases(tr, r_)
            if al:
                prop.aliases = {**prop.aliases, **al}
            readers[r_] = (prop, LearnedSpanReader(
                mentions=prop, extra_features=R.frame_features,
                extra_role_features=R.role_frame_features).fit(
                [supervise_via(d, prop, PAIR) for d in tr]))
        for d in te:
            for r_ in PAIR:
                prop, reader = readers[r_]
                res = reader.run(d["intro"], query=d.get("title", ""))
                best = None
                for i, c in enumerate(res.claims):
                    v = c.roles.get("value")
                    if c.predicate == r_ and isinstance(v, EntityRef):
                        if best is None or res.confidence_of(i) > best[0]:
                            best = (res.confidence_of(i), v.id)
                read[d["qid"]][f"learned:{r_}"] = best[1] if best else None
    for d in docs:
        read[d["qid"]]["hand:parent"] = read_parent(d["intro"])
        read[d["qid"]]["hand:country"] = read_country(d["intro"])
        for r_ in PAIR:
            read[d["qid"]][f"union:{r_}"] = (read[d["qid"]][f"hand:{r_}"]
                                             or read[d["qid"]].get(f"learned:{r_}"))

    print(f"{len(docs)} articles\n")
    print(f"    {'arm':<9}{'parent':>8}{'country':>9}   {'JOIN prec':>10}"
          f"{'recall':>8}{'F1':>8}   {'was':>7}")
    was = {"learned": 0.036, "hand": 0.089, "union": 0.109}
    out = {}
    for arm in ("learned", "hand", "union"):
        def hit(q, r_):
            a = read[q].get(f"{arm}:{r_}")
            gold = (by_qid[q].get("parent") if r_ == "parent"
                    else by_qid[q].get("country")) or []
            return bool(a) and norm(a) in [norm(x) for x in gold]

        pr = statistics.mean(hit(d["qid"], "parent") for d in docs)
        co = statistics.mean(hit(d["qid"], "country") for d in docs)

        def groups(country, source):
            got = set()
            for d in docs:
                q = d["qid"]
                if source == "gold":
                    ok = any(norm(country) == norm(g)
                             for g in (d.get("country") or []))
                    ps = by_qid[q].get("parent") or []
                else:
                    a = read[q].get(f"{arm}:country")
                    ok = bool(a) and norm(a) == norm(country)
                    p = read[q].get(f"{arm}:parent")
                    ps = [p] if p else []
                if ok:
                    got |= {norm(x) for x in ps if x}
            return got

        scored = []
        for c in sorted({norm(x) for d in docs for x in (d.get("country") or [])}):
            gold = groups(c, "gold")
            if len(gold) < 3:
                continue
            got = groups(c, "read")
            tp = len(gold & got)
            p_ = tp / len(got) if got else 0.0
            r_2 = tp / len(gold)
            scored.append({"p": p_, "r": r_2,
                           "f1": 2 * p_ * r_2 / (p_ + r_2) if p_ + r_2 else 0.0})
        m = {k: statistics.mean(s[k] for s in scored) for k in ("p", "r", "f1")}
        print(f"    {arm:<9}{pr:8.3f}{co:9.3f}   {m['p']:10.3f}{m['r']:8.3f}"
              f"{m['f1']:8.3f}   {was[arm]:7.3f}")
        out[arm] = {"parent": pr, "country": co, "macro": m,
                    "previous_f1": was[arm], "countries": len(scored)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
