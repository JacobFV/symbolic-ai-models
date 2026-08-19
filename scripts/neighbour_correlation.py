"""Does reading a child correctly predict reading its parent correctly?

The clumping claim — a hand-written pattern reader beats independence on two-hop
queries because pattern success clumps on canonically-phrased articles — rests on
**20 two-hop successes**, and the promotion queue says so. But the *mechanism* it
asserts is a correlation between neighbouring articles, and that can be measured
on **every chain pair**, whether or not both hops succeeded.

For each (child, parent) pair with both articles in the corpus, a 2x2 table of
child-read-correctly against parent-read-correctly. 415 pairs, of which 50-73
have a correct child depending on the reader — three times the events the ratio
test had, and it tests the mechanism rather than its consequence.

Predicted: the hand reader shows `P(parent ok | child ok) > P(parent ok)` and the
learned reader does not. Refuted if the hand reader's conditional matches its
marginal, which would mean the two-hop excess came from somewhere other than
neighbour correlation and the mechanism story was invention.

Run: uv run python -u scripts/neighbour_correlation.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (CapitalisedMentions,
                                             LearnedSpanReader, char_features)
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import (norm, read_country, read_hq,
                                          read_parent)

CORPUS = Path(sys.argv[sys.argv.index("--corpus") + 1]
              if "--corpus" in sys.argv
              else "data/artifacts/wikipedia_parents_closed.jsonl")
OUT = Path("runs/neighbour_correlation.json")
FOLDS = 4
#: The hand reader for each relation, and the gold field it is scored against.
#: `country` is the discriminating case: `read_country` keys on a CLOSED CLASS of
#: nationality adjectives applied uniformly, not on phrasing style, so if the
#: clumping story is right -- patterns succeed on a KIND of article -- it should
#: clump least here.
#: A third reader with a genuinely different inductive bias. It does not read at
#: all: among the capitalised mentions that are not the article's subject, it
#: names the one with the highest corpus-wide document frequency. A pure prior on
#: entity fame, no phrasing, no supervision, no features shared with anything
#: else here. If clumping is a property of PATTERN readers it should be absent;
#: if it is a property of the graph -- fame inherited up an ownership chain -- it
#: should be present, and the "patterns clump" story becomes "readers whose
#: success depends on an inherited entity property clump".
FAME = "fame"
#: The third arm the queue asked for: same mention proposer, same distant
#: supervision, and NOT ONE LEXICAL FEATURE -- character n-grams of the sentence
#: with names, numbers and dates replaced by sentinels, at the classifier and at
#: the ranker. If it clumps, the hand/learned split is not about being learned.
CHAR = "char"


def char_role_features(pred, role, cands, j, u):
    """The ranker's character view: n-grams of the gap before the candidate."""
    t = cands[j]
    words = [w for w in u.tokens if w.kind in ("word", "num")]
    prev = max((c.end for c in cands if c.end <= t.start), default=u.start)
    gap = " ".join(w.text.lower() for w in words if prev <= w.start < t.start)
    out = [f"idx={j}", f"n={len(cands)}", f"len={min(len(gap), 40) // 5}"]
    for k in (3, 4):
        out += [f"g{k}={gap[i:i + k]}" for i in range(len(gap) - k + 1)][-12:]
    return out
RELATIONS = {"parent": (read_parent, "current"),
             "country": (read_country, "country"),
             "headquarters": (read_hq, "headquarters")}


def main() -> None:
    rows = [json.loads(x) for x in CORPUS.read_text().splitlines() if x.strip()]
    by_qid = {r["qid"]: r for r in rows}
    edge = {r["qid"]: (r.get("current_ids") or [None])[0] for r in rows}
    pairs = [(q, edge[q]) for q in edge
             if edge.get(q) in by_qid and edge.get(edge[q])]

    R.PARENTS = CORPUS
    R.RELATIONS = Path("data/artifacts/company_relations_scale.jsonl")
    docs = R.corpus()
    gold = {d["qid"]: d for d in docs}

    # Corpus-wide document frequency of every proposed mention, for the fame
    # reader. Built once from the same proposer the learned reader uses, so the
    # two differ in what they DO with a mention and not in what counts as one.
    from collections import Counter as _C
    from symbolic_ai_core.reader.learned import _units as _u
    cm = CapitalisedMentions()
    df: _C = _C()
    for d in docs:
        seen = {m.text for un in _u(d["intro"]) for m in cm.find(un)}
        df.update(seen)

    def fame_read(d) -> str | None:
        subject = (d.get("title") or "").lower()
        best = None
        for un in _u(d["intro"]):
            for m in cm.find(un):
                if m.text.lower() in subject or subject in m.text.lower():
                    continue
                if best is None or df[m.text] > df[best]:
                    best = m.text
        return best
    read: dict[str, dict[str, str | None]] = {}
    for fold in range(FOLDS):
        te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        reader = LearnedSpanReader(
            mentions=CapitalisedMentions(), extra_features=R.extra(),
            extra_role_features=R.role_frame_features).fit(
            [R.supervise_distant(d) for d in tr])
        for d in te:
            res = reader.run(d["intro"], query=d.get("title", ""))
            best = None
            for i, c in enumerate(res.claims):
                v = c.roles.get("value")
                if c.predicate == "parent" and isinstance(v, EntityRef):
                    if best is None or res.confidence_of(i) > best[0]:
                        best = (res.confidence_of(i), v.id)
            for rel in RELATIONS:
                b = None
                for i, c in enumerate(res.claims):
                    v = c.roles.get("value")
                    if c.predicate == rel and isinstance(v, EntityRef):
                        if b is None or res.confidence_of(i) > b[0]:
                            b = (res.confidence_of(i), v.id)
                read.setdefault(d["qid"], {})[f"learned:{rel}"] = (
                    b[1] if b else None)
    char_reader_read: dict[str, dict[str, str | None]] = {}
    for fold in range(FOLDS):
        te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        cr = LearnedSpanReader(
            mentions=CapitalisedMentions(), base_features=False,
            extra_features=char_features,
            extra_role_features=char_role_features).fit(
            [R.supervise_distant(d) for d in tr])
        for d in te:
            res = cr.run(d["intro"], query=d.get("title", ""))
            for rel in RELATIONS:
                b = None
                for i, c in enumerate(res.claims):
                    v = c.roles.get("value")
                    if c.predicate == rel and isinstance(v, EntityRef):
                        if b is None or res.confidence_of(i) > b[0]:
                            b = (res.confidence_of(i), v.id)
                char_reader_read.setdefault(d["qid"], {})[rel] = (
                    b[1] if b else None)

    for d in docs:
        for rel in RELATIONS:
            read.setdefault(d["qid"], {})[f"{CHAR}:{rel}"] = (
                char_reader_read.get(d["qid"], {}).get(rel))
        for rel, (fn, _) in RELATIONS.items():
            read.setdefault(d["qid"], {})[f"hand:{rel}"] = fn(d["intro"])
            # The fame reader names one entity per article, so it answers every
            # relation with the same guess -- which is the point of a prior.
            read[d["qid"]][f"{FAME}:{rel}"] = fame_read(d)

    def ok(arm: str, rel: str, q: str) -> bool:
        a = read.get(q, {}).get(f"{arm}:{rel}")
        if not a:
            return False
        field = RELATIONS[rel][1]
        want = (by_qid[q].get(field) if rel == "parent"
                else (gold.get(q, {}).get(rel) or []))
        return norm(a) in [norm(x) for x in (want or [])]

    print(f"{len(pairs)} (child, parent) pairs with both articles present\n")
    print(f"    {'relation':<14}{'reader':<9}{'P(par)':>8}{'| child ok':>12}"
          f"{'| child bad':>13}{'odds':>7}{'chi2 p':>9}{'n both':>8}")
    out = {}
    for rel in RELATIONS:
      for arm in ("learned", "hand", CHAR):
        a = b = c = d = 0
        for q, p in pairs:
            ci, pi = ok(arm, rel, q), ok(arm, rel, p)
            a, b, c, d = (a + (ci and pi), b + (ci and not pi),
                          c + (not ci and pi), d + (not ci and not pi))
        n = a + b + c + d
        # Yates-corrected chi-square; the count of the smallest cell is printed
        # beside every row, because a rate here without its numerator is not a
        # result -- see notes/lessons/2026-08-19-a-rate-without-its-numerator.
        num = n * (abs(a * d - b * c) - n / 2) ** 2
        den = (a + b) * (c + d) * (a + c) * (b + d)
        chi = num / den if den else 0.0
        pv = math.erfc(math.sqrt(chi / 2)) if chi > 0 else 1.0
        odds = (a * d) / (b * c) if b * c else float("inf")
        print(f"    {rel:<14}{arm:<9}{(a + c) / n:8.3f}{a / max(1, a + b):12.3f}"
              f"{c / max(1, c + d):13.3f}{odds:7.2f}{pv:9.3f}{a:8d}")
        out[f"{rel}:{arm}"] = {
            "both": a, "child_only": b, "parent_only": c, "neither": d,
            "marginal": (a + c) / n, "cond_child_ok": a / max(1, a + b),
            "cond_child_bad": c / max(1, c + d), "odds_ratio": odds,
            "chi2_p": pv}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"pairs": len(pairs), "arms": out}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
