"""Train where the errors are expensive: in-degree as a supervision weight.

`in-degree` — how many corpus articles name this entity as their parent — is the
only actionable signal any arm in this session produced. It predicts where an
error is expensive **before any reading**, from link structure alone. Two uses
have been tried and both failed: cheap corroboration (co-occurrence measures
topic, AUC 0.503) and selective ingestion (no interior maximum at any threshold).

This is the third and it is different in kind. Not a verification step and not a
decision rule — **which documents to train on**. Hub articles are consulted most
and read worst (0.126 against 0.197), so their sentences are duplicated in the
training set in proportion to in-degree.

The metric is the one the blast-radius finding established, not raw accuracy:
**consultation-weighted accuracy**, where each article counts once per query that
depends on it. Raw accuracy is what a leaf-heavy corpus rewards; a persistent
world is judged on what it is asked.

Predicted before running: hub accuracy rises and leaf accuracy falls, raw
accuracy is roughly flat, and **consultation-weighted accuracy rises** — because
the weighting moves capacity toward the articles the queries actually touch. If
consultation-weighted accuracy does *not* rise, in-degree is not usable for
anything, which would close the last signal this session found.

Run: uv run python -u scripts/indegree_weighted_training.py
"""

from __future__ import annotations

import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
OUT = Path("runs/indegree_weighted_training.json")
SPLITS = (41, 42, 43)
FOLDS = 4
#: Extra copies of a hub article's supervision, capped so one giant hub cannot
#: become the training set.
MAX_COPIES = 4


def main() -> None:
    rows = [json.loads(x) for x in CORPUS.read_text().splitlines() if x.strip()]
    by_qid = {r["qid"]: r for r in rows}
    indeg: Counter = Counter()
    for r in rows:
        for pid in (r.get("current_ids") or [])[:1]:
            indeg[pid] += 1

    R.PARENTS = CORPUS
    R.RELATIONS = Path("data/artifacts/company_relations_scale.jsonl")
    docs = R.corpus()

    #: A query touches an article once for its own question and once more for
    #: every chain that passes through it, which is its in-degree.
    consult = {d["qid"]: 1 + indeg.get(d["qid"], 0) for d in docs}
    print(f"{len(docs)} articles; {sum(1 for d in docs if indeg.get(d['qid'])) } "
          f"hubs; {sum(consult.values()):,} consultations")

    out = []
    for split in SPLITS:
        order = list(docs)
        random.Random(split).shuffle(order)      # a prefix is not a sample
        arms = {}
        for arm in ("uniform", "in-degree weighted"):
            ok_by_q: dict[str, bool] = {}
            for fold in range(FOLDS):
                te = [d for i, d in enumerate(order) if i % FOLDS == fold]
                tr = [d for i, d in enumerate(order) if i % FOLDS != fold]
                sup = []
                for d in tr:
                    units = R.supervise_distant(d)
                    copies = (1 if arm == "uniform"
                              else min(1 + indeg.get(d["qid"], 0), MAX_COPIES))
                    sup.extend([units] * copies)
                reader = LearnedSpanReader(
                    mentions=CapitalisedMentions(), extra_features=R.extra(),
                    extra_role_features=R.role_frame_features).fit(sup)
                for d in te:
                    gold = [norm(x) for x in (d.get("parent") or [])]
                    if not gold:
                        continue
                    res = reader.run(d["intro"], query=d.get("title", ""))
                    best = None
                    for i, c in enumerate(res.claims):
                        v = c.roles.get("value")
                        if c.predicate == "parent" and isinstance(v, EntityRef):
                            if best is None or res.confidence_of(i) > best[0]:
                                best = (res.confidence_of(i), v.id)
                    ok_by_q[d["qid"]] = bool(best) and norm(best[1]) in gold

            raw = statistics.mean(ok_by_q.values())
            served = sum(consult[q] for q in ok_by_q)
            weighted = sum(consult[q] for q, v in ok_by_q.items() if v) / served
            hub = [v for q, v in ok_by_q.items() if indeg.get(q, 0) >= 1]
            leaf = [v for q, v in ok_by_q.items() if indeg.get(q, 0) == 0]
            arms[arm] = {"raw": raw, "weighted": weighted,
                         "hub": statistics.mean(hub) if hub else float("nan"),
                         "leaf": statistics.mean(leaf), "n_hub": len(hub),
                         "n": len(ok_by_q)}
        out.append({"split": split, **arms})

    print(f"\n    {'arm':<20}{'raw acc':>9}{'WEIGHTED':>10}{'hub':>8}"
          f"{'leaf':>8}{'n hub':>7}")
    for arm in ("uniform", "in-degree weighted"):
        m = {k: statistics.mean(o[arm][k] for o in out)
             for k in ("raw", "weighted", "hub", "leaf")}
        print(f"    {arm:<20}{m['raw']:9.3f}{m['weighted']:10.3f}"
              f"{m['hub']:8.3f}{m['leaf']:8.3f}{out[0][arm]['n_hub']:7d}")
    d_w = statistics.mean(o["in-degree weighted"]["weighted"] - o["uniform"]["weighted"]
                          for o in out)
    d_r = statistics.mean(o["in-degree weighted"]["raw"] - o["uniform"]["raw"]
                          for o in out)
    print(f"    delta   raw {d_r:+.3f}   consultation-weighted {d_w:+.3f}   "
          f"({sum(1 for o in out if o['in-degree weighted']['weighted'] > o['uniform']['weighted'])}/{len(out)} splits up)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
