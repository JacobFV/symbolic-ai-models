"""Is the hand reader's correctness concentrated? The interpretation, measured.

The composed-query note explains the hand reader tying on the join while behind on
both its parts by saying its **correct answers concentrate on a subgraph** — the
same clumping that helps a two-hop chain (ratio 1.56) hurting a set-valued join.
That note flags the explanation as *"an interpretation consistent with the earlier
measurement, not a fresh measurement of it."* This measures it.

For each country with a non-empty gold answer set, how many of its groups each arm
recovers. Concentration is then read three ways:

    Gini            over per-country recall, 0 = spread evenly, 1 = all in one
    top-10 share    of all correct (country, group) pairs
    countries hit   how many countries get at least one right

Predicted: the hand reader is **more concentrated** on every measure — higher
Gini, higher top-10 share, fewer countries hit — despite recovering a similar
total. If the two are equally concentrated, the subgraph story is wrong and the
join result needs a different explanation.

Run: uv run python -u scripts/answer_concentration.py
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
OUT = Path("runs/answer_concentration.json")
FOLDS = 4
PAIR = ("parent", "country")


def gini(xs: list[float]) -> float:
    """0 when every country is served equally, 1 when one country has it all."""
    xs = sorted(xs)
    n = len(xs)
    total = sum(xs)
    if n == 0 or total == 0:
        return float("nan")
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * cum) / (n * total) - (n + 1) / n


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
        readers = {}
        for r_ in PAIR:
            prop = PhraseMentions.induce(
                [v for d in tr for v in (d.get(r_) or [])], alias_heads=True)
            al = induce_aliases(tr, r_)
            if al:
                prop.aliases = {**prop.aliases, **al}
            readers[r_] = LearnedSpanReader(
                mentions=prop, extra_features=R.frame_features,
                extra_role_features=R.role_frame_features).fit(
                [supervise_via(d, prop, PAIR) for d in tr])
        for d in te:
            for r_ in PAIR:
                res = readers[r_].run(d["intro"], query=d.get("title", ""))
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

    countries = sorted({norm(x) for d in docs for x in (d.get("country") or [])})
    print(f"{len(docs)} articles, {len(countries)} countries\n")
    print(f"    {'arm':<9}{'correct':>9}{'hit':>8}{'GINI':>7}"
          f"{'MACRO F1':>10}{'MICRO F1':>10}{'micro P':>9}{'micro R':>9}")
    out = {}
    for arm in ("learned", "hand", "union"):
        per: dict[str, float] = {}
        total = 0
        f1s: list[float] = []
        tp_all = got_all = gold_all = 0
        for c in countries:
            gold = set()
            got = set()
            for d in docs:
                q = d["qid"]
                if any(norm(c) == norm(g) for g in (d.get("country") or [])):
                    gold |= {norm(p) for p in (d.get("parent") or []) if p}
                a = read[q].get(f"{arm}:country")
                if a and norm(a) == norm(c):
                    p = read[q].get(f"{arm}:parent")
                    if p:
                        got.add(norm(p))
            if len(gold) < 3:
                continue
            hit = len(gold & got)
            per[c] = hit / len(gold)
            total += hit
            tp_all += hit
            got_all += len(got)
            gold_all += len(gold)
            pc = hit / len(got) if got else 0.0
            rc = hit / len(gold)
            f1s.append(2 * pc * rc / (pc + rc) if pc + rc else 0.0)
        vals = list(per.values())
        served = sum(1 for v in vals if v > 0)
        # Macro averages countries equally -- Belgium counts as much as the
        # United States. Micro pools the pairs, which is the measure a user of
        # the world experiences. Every composed-query number in this session was
        # macro and none said so.
        macro = statistics.mean(f1s) if f1s else 0.0
        mp = tp_all / got_all if got_all else 0.0
        mr = tp_all / gold_all if gold_all else 0.0
        micro = 2 * mp * mr / (mp + mr) if mp + mr else 0.0
        print(f"    {arm:<9}{total:9d}{f'{served}/{len(vals)}':>8}"
              f"{gini(vals):7.3f}{macro:10.3f}{micro:10.3f}{mp:9.3f}{mr:9.3f}")
        out[arm] = {"correct_pairs": total, "countries_served": served,
                    "countries": len(vals), "gini": gini(vals),
                    "macro_f1": macro, "micro_f1": micro,
                    "micro_precision": mp, "micro_recall": mr}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
