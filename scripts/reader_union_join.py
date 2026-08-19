"""Is the learned reader's value in beating the patterns, or in covering them?

The learned reader loses to four hand-written patterns on every relation
(`parent` 0.113 against 0.327 as `multi_relation_world.py` measures it). That is
settled. The question this asks is different and more useful: the two readers
fail on **different articles**, so a system that uses both should answer more of
them than either — and the composed query is recall-bound, macro recall 0.24 with
precision 0.42, so recall is exactly what it is short of.

The composed query is the north-star capability and is unchanged:

    parent(c, p) JOIN country(c, X)  ->  which groups control companies in X?

No sentence in any article states it; it exists only in the world assembled from
all of them.

Four arms, each building the same world a different way:

    hand        the pattern readers, as published
    learned     the learned reader, 4-fold cross-validated so no article is
                read by a model fitted on it
    union       hand where it answers, learned where it abstains
    union+      union, but learned also overrides hand where hand abstains OR
                the two disagree and learned is more confident

Predicted before running:

- **The learned reader's correct answers are NOT a subset of the hand reader's.**
  They key on different things — patterns on a handful of high-frequency frames,
  the classifier on content words across the tail — so expect 20-40% of the
  learned reader's correct answers to be on articles the patterns got wrong or
  skipped.
- **Union raises macro recall on the composed query** from 0.24 toward 0.30 at
  some precision cost, and macro F1 from 0.138 toward 0.16-0.20.
- Refuted if the learned reader's correct set is essentially contained in the
  hand reader's, which would mean it has learned the same few frames and adds
  nothing but noise.

Run: uv run python -u scripts/reader_union_join.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

from scripts.multi_relation_world import (RELS as RELS_PATH, norm, read_country,
                                          read_hq, read_parent, matches)
from scripts.real_text_reader import (RELS, extra, role_frame_features,
                                      supervise_distant)

OUT = Path("runs/reader_union_join.json")
#: With a calibrated belief this is a real accuracy threshold: override the
#: pattern reader only where the classifier has historically been right more
#: often than the patterns are (0.556 precision on `parent`).
OVERRIDE_AT = 0.6
PARENTS = Path("data/artifacts/wikipedia_parents.jsonl")
FOLDS = 4
#: Fit a held-out score->accuracy map per predicate, so a belief is a probability
#: rather than a squashed margin. Costs a quarter of the training articles.
CALIBRATE = "--calibrate" in sys.argv
#: The learned reader's relation names, mapped onto this script's.
AS = {"parent": "parent", "country": "country", "headquarters": "hq"}


def corpus() -> list[dict]:
    parents = {json.loads(x)["qid"]: json.loads(x)
               for x in PARENTS.read_text().splitlines() if x.strip()}
    rows = []
    for line in RELS_PATH.read_text().splitlines():
        rec = json.loads(line)
        p = parents.get(rec["qid"])
        if not p:
            continue
        rec["intro"] = p["intro"]
        rec["parent"] = p.get("current") or [p["parent"]]
        rec["headquarters"] = rec.get("headquarters") or []
        rec["country"] = rec.get("country") or []
        rows.append(rec)
    return rows


def learned_answers(docs) -> dict[str, dict[str, tuple[str, float]]]:
    """Cross-validated, so no article is read by a model that saw it."""
    out: dict[str, dict[str, tuple[str, float]]] = {}
    for fold in range(FOLDS):
        test = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        train = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        # A quarter of the training articles are held back from the FIT so the
        # calibrator sees scores the model did not learn from. Calibrating on
        # the fitting set is the failure the calibrator's own docstring names.
        fit_part = [d for i, d in enumerate(train) if i % 4]
        cal_part = [d for i, d in enumerate(train) if not i % 4]
        reader = LearnedSpanReader(
            mentions=CapitalisedMentions(), extra_features=extra(),
            extra_role_features=role_frame_features).fit(
            [supervise_distant(d) for d in (fit_part if CALIBRATE else train)])
        if CALIBRATE:
            reader.calibrate([supervise_distant(d) for d in cal_part])
        for d in test:
            res = reader.run(d["intro"])
            best: dict[str, tuple[str, float]] = {}
            for i, c in enumerate(res.claims):
                v = c.roles.get("value")
                if not isinstance(v, EntityRef):
                    continue
                b = res.confidence_of(i)
                if c.predicate not in best or b > best[c.predicate][1]:
                    best[c.predicate] = (v.id, b)
            out[d["qid"]] = best
    return out


def build(docs, learned, arm: str) -> list[dict]:
    """One reading per article, from whichever reader(s) the arm allows."""
    read = []
    for d in docs:
        h = {"parent": read_parent(d["intro"]), "country": read_country(d["intro"]),
             "hq": read_hq(d["intro"])}
        l_ = {AS[k]: v[0] for k, v in learned.get(d["qid"], {}).items()
              if k in AS}
        lc = {AS[k]: v[1] for k, v in learned.get(d["qid"], {}).items()
              if k in AS}
        if arm == "hand":
            got = h
        elif arm == "learned":
            got = {k: l_.get(k) for k in h}
        elif arm == "union":
            got = {k: (h[k] or l_.get(k)) for k in h}
        else:                                   # union+
            got = {}
            for k in h:
                if not h[k]:
                    got[k] = l_.get(k)
                elif l_.get(k) and norm(l_[k]) != norm(h[k]) \
                        and lc.get(k, 0) > OVERRIDE_AT:
                    got[k] = l_[k]
                else:
                    got[k] = h[k]
        read.append({"qid": d["qid"], **got,
                     "parent_gold": d["parent"], "country_gold": d["country"],
                     "hq_gold": d["headquarters"]})
    return read


def per_relation(read) -> dict:
    out = {}
    for rel, gk in (("parent", "parent_gold"), ("country", "country_gold"),
                    ("hq", "hq_gold")):
        known = [x for x in read if x[gk]]
        ans = [x for x in known if x[rel]]
        cor = [x for x in ans if matches(x[rel], x[gk])]
        out[rel] = {"answered": len(ans) / max(1, len(known)),
                    "correct": len(cor) / max(1, len(known)),
                    "precision": len(cor) / max(1, len(ans))}
    return out


def join_scores(read) -> dict:
    def groups_in(country, source):
        out = set()
        for x in read:
            if source == "gold":
                ok = any(norm(country) == norm(g) for g in x["country_gold"])
                ps = x["parent_gold"]
            else:
                ok = x["country"] and norm(x["country"]) == norm(country)
                ps = [x["parent"]] if x["parent"] else []
            if ok:
                out |= {norm(p) for p in ps if p}
        return out

    scored = []
    for c in sorted({norm(g) for x in read for g in x["country_gold"]}):
        gold = groups_in(c, "gold")
        if not gold:
            continue
        got = groups_in(c, "read")
        tp = len(gold & got)
        prec = tp / len(got) if got else 0.0
        rec = tp / len(gold)
        scored.append({"country": c, "precision": prec, "recall": rec,
                       "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0})
    return {k: statistics.mean(s[k] for s in scored)
            for k in ("precision", "recall", "f1")} | {"n": len(scored)}


def main() -> None:
    docs = corpus()
    print(f"{len(docs)} companies with prose and ground truth")
    learned = learned_answers(docs)

    arms = {a: build(docs, learned, a)
            for a in ("hand", "learned", "union", "union+")}

    # -- is the learned reader's correct set contained in the hand reader's? --
    h, l_ = per_relation(arms["hand"]), per_relation(arms["learned"])
    print(f"\n{'relation':<10} {'hand ok':>8} {'learned ok':>11} "
          f"{'learned-only':>13} {'hand-only':>10} {'both':>6}")
    overlap = {}
    for rel, gk in (("parent", "parent_gold"), ("country", "country_gold"),
                    ("hq", "hq_gold")):
        hs = {x["qid"] for x in arms["hand"]
              if x[gk] and x[rel] and matches(x[rel], x[gk])}
        ls = {x["qid"] for x in arms["learned"]
              if x[gk] and x[rel] and matches(x[rel], x[gk])}
        overlap[rel] = {"hand": len(hs), "learned": len(ls),
                        "learned_only": len(ls - hs), "hand_only": len(hs - ls),
                        "both": len(hs & ls),
                        "learned_only_share": len(ls - hs) / max(1, len(ls))}
        print(f"{rel:<10} {len(hs):>8} {len(ls):>11} {len(ls - hs):>13} "
              f"{len(hs - ls):>10} {len(hs & ls):>6}")

    print(f"\n{'arm':<10} {'parent':>8} {'country':>8} {'hq':>8}   "
          f"{'JOIN prec':>10} {'recall':>8} {'F1':>8}")
    rows = {}
    for a, read in arms.items():
        pr, j = per_relation(read), join_scores(read)
        rows[a] = {"per_relation": pr, "join": j}
        print(f"{a:<10} {pr['parent']['correct']:>8.3f} "
              f"{pr['country']['correct']:>8.3f} {pr['hq']['correct']:>8.3f}   "
              f"{j['precision']:>10.3f} {j['recall']:>8.3f} {j['f1']:>8.3f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    (OUT.with_name("reader_union_join_calibrated.json") if CALIBRATE
     else OUT).write_text(json.dumps({"n": len(docs), "overlap": overlap,
                               "arms": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
