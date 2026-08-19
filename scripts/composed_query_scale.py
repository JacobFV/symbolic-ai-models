"""The composed query at scale: which groups control companies in X?

`scripts/multi_relation_world.py` ran `parent(c,p) JOIN country(c,X)` on **168**
articles and reported macro F1 **0.138** with hand-written readers. The corpus is
now 2,502 articles with country and headquarters gold on 94% and 96% of them, so
the same query can be asked on fifteen times the world — and with the learned
reader, the union, and the character-only reader beside the patterns.

The query's answer is stated in no article: `parent` comes from the subsidiary's
page and `country` from the same page, but the *set* of groups controlling
anything in a country exists only after both relations are read across the whole
corpus and joined.

Two things are measured that the 168-article version could not separate:

- **per-relation reading at scale**, so the join's loss can be attributed;
- **the join under each reader**, macro-averaged over countries with a non-empty
  gold answer, with `|gold|` printed beside every row because a rate without its
  numerator is not a result.

Predicted before running: the join is **limited by `parent`**, not by `country`.
The hand reader reads country at 0.711 and parent at 0.171 on the chain
population, and a join needs both — so macro recall should track parent's rate
and macro precision should be higher than the 168-article run's 0.207, because a
fifteen-fold larger world makes each country's gold set larger and a few correct
parents easier to hit.

Run: uv run python -u scripts/composed_query_scale.py
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (CapitalisedMentions,
                                             LearnedSpanReader, char_features)
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm, read_country, read_parent
from scripts.neighbour_correlation import char_role_features

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale.jsonl")
OUT = Path("runs/composed_query_scale.json")
FOLDS = 4


def main() -> None:
    rows = [json.loads(x) for x in CORPUS.read_text().splitlines() if x.strip()]
    by_qid = {r["qid"]: r for r in rows}
    rel = {json.loads(x)["qid"]: json.loads(x)
           for x in RELS.read_text().splitlines() if x.strip()}

    R.PARENTS, R.RELATIONS = CORPUS, RELS
    docs = R.corpus()
    print(f"{len(docs)} articles; "
          f"{sum(1 for d in docs if rel.get(d['qid'], {}).get('country'))} "
          f"with a country")

    read: dict[str, dict[str, str | None]] = defaultdict(dict)
    for fold in range(FOLDS):
        te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        sup = [R.supervise_distant(d) for d in tr]
        fits = {
            "learned": LearnedSpanReader(
                mentions=CapitalisedMentions(), extra_features=R.extra(),
                extra_role_features=R.role_frame_features).fit(sup),
            "char": LearnedSpanReader(
                mentions=CapitalisedMentions(), base_features=False,
                extra_features=char_features,
                extra_role_features=char_role_features).fit(sup),
        }
        for arm, reader in fits.items():
            for d in te:
                res = reader.run(d["intro"], query=d.get("title", ""))
                for r_ in ("parent", "country"):
                    b = None
                    for i, c in enumerate(res.claims):
                        v = c.roles.get("value")
                        if c.predicate == r_ and isinstance(v, EntityRef):
                            if b is None or res.confidence_of(i) > b[0]:
                                b = (res.confidence_of(i), v.id)
                    read[d["qid"]][f"{arm}:{r_}"] = b[1] if b else None
    for d in docs:
        read[d["qid"]]["hand:parent"] = read_parent(d["intro"])
        read[d["qid"]]["hand:country"] = read_country(d["intro"])
        for r_ in ("parent", "country"):
            read[d["qid"]][f"union:{r_}"] = (read[d["qid"]][f"hand:{r_}"]
                                             or read[d["qid"]].get(f"learned:{r_}"))

    arms = ("learned", "char", "hand", "union")
    print(f"\n    {'arm':<9}{'parent':>9}{'country':>9}   "
          f"{'JOIN prec':>10}{'recall':>8}{'F1':>8}{'countries':>10}")
    out = {}
    for arm in arms:
        def hit(q, r_):
            a = read[q].get(f"{arm}:{r_}")
            gold = (by_qid[q].get("current") if r_ == "parent"
                    else rel.get(q, {}).get("country")) or []
            return bool(a) and norm(a) in [norm(x) for x in gold]

        pr = statistics.mean(hit(d["qid"], "parent") for d in docs)
        co = statistics.mean(hit(d["qid"], "country") for d in docs)

        def groups(country, source):
            got = set()
            for d in docs:
                q = d["qid"]
                if source == "gold":
                    ok = any(norm(country) == norm(g)
                             for g in (rel.get(q, {}).get("country") or []))
                    ps = by_qid[q].get("current") or []
                else:
                    a = read[q].get(f"{arm}:country")
                    ok = bool(a) and norm(a) == norm(country)
                    p = read[q].get(f"{arm}:parent")
                    ps = [p] if p else []
                if ok:
                    got |= {norm(p) for p in ps if p}
            return got

        scored = []
        countries = sorted({norm(c) for q in rel
                            for c in (rel[q].get("country") or [])})
        for c in countries:
            gold = groups(c, "gold")
            if len(gold) < 3:          # a country with one company is not a query
                continue
            got = groups(c, "read")
            tp = len(gold & got)
            p_ = tp / len(got) if got else 0.0
            r_ = tp / len(gold)
            scored.append({"country": c, "gold": len(gold), "precision": p_,
                           "recall": r_,
                           "f1": 2 * p_ * r_ / (p_ + r_) if p_ + r_ else 0.0})
        m = {k: statistics.mean(s[k] for s in scored)
             for k in ("precision", "recall", "f1")}
        print(f"    {arm:<9}{pr:9.3f}{co:9.3f}   {m['precision']:10.3f}"
              f"{m['recall']:8.3f}{m['f1']:8.3f}{len(scored):10d}")
        out[arm] = {"parent": pr, "country": co, "macro": m,
                    "n_countries": len(scored),
                    "median_gold": statistics.median(s["gold"] for s in scored)}

    print(f"\n    the 168-article run with hand readers: macro F1 0.138 "
          f"(precision 0.207, recall 0.119)")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
