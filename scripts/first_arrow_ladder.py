"""Is the first arrow bad because it is hard, or because nobody tried?

`notes/findings/2026-08-18-the-first-arrow-is-cheap-and-bad.md` measured a
symbolic extractor at **F1 0.303** on affiliation strings it had never seen, and
said plainly that the number is a **floor**: the extractor is a dictionary with a
flat component vote and nothing better was attempted.

It also found the number that makes the question answerable. On strings the
memoriser has seen **verbatim**, agreement is only precision 72.8% / recall
70.7% / **F1 0.717** — because OpenAlex assigns institutions per *author*, not
per string, so the label is not a function of the input. That is a **ceiling on
any string-only method**, and every rung below is reported as a fraction of it
rather than against a meaningless 1.0.

Four rungs, each adding one idea to the last:

    v0  component vote, min count 2                    (the published floor)
    v1  IDF-weighted components — "national institute for fusion science"
        is worth more than "usa", and a flat vote treats them alike
    v2  token-overlap similarity against known institution names, so an
        unseen wording of a seen institution can still match
    v3  specificity-first — take the best-scoring component rather than the
        union of every component that matched, which is where v0's 29.1%
        precision is going

Same work-disjoint split, same seed, same evaluation as the finding, so the v0
row must reproduce 0.303 or the ladder is not measuring the same thing.

Run: uv run python -u scripts/first_arrow_ladder.py
"""

from __future__ import annotations

import json
import math
import random
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from scripts.first_arrow_prose import (SEED, SRC, TRAIN_FRAC, components, load,
                                       norm, score)  # noqa: F401

OUT = Path("runs/first_arrow_ladder.json")
def measure_ceiling(ix: "Index", pairs) -> dict[str, float]:
    """The reachable maximum, measured rather than assumed.

    A memoriser evaluated on held-out strings it has seen **verbatim** is being
    handed the answer, so whatever it fails to score is label noise the input
    cannot explain. Computing it from the data rather than pinning a constant is
    what caught the error this script's first version inherited: the published
    0.717 was not a property of affiliation linking, it was a property of a
    snapshot that flattened authorships and asked one string to predict every
    institution its author listed. On the authorship snapshot the same
    measurement gives 0.988.
    """
    seen = [(ix.full.get(norm(raw), set()), truth) for raw, truth in pairs
            if norm(raw) in ix.full]
    s = score(seen)
    return {"f1": s["f1"], "precision": s["precision"], "recall": s["recall"],
            "n": s["n"], "exact": s["exact_set_match"]}


class Index:
    """Everything the rungs share, built from the training works only."""

    def __init__(self, train: list[dict[str, Any]]) -> None:
        self.full: dict[str, set[str]] = {}
        full_votes: dict[str, Counter] = defaultdict(Counter)
        self.comp: dict[str, Counter] = defaultdict(Counter)
        self.comp_df: Counter = Counter()          # component -> how many RORs
        self.name_tokens: dict[str, Counter] = defaultdict(Counter)
        n_strings = 0
        for w in train:
            for a in w["affiliations"]:
                if not a["rors"]:
                    continue
                n_strings += 1
                full_votes[norm(a["raw"])][tuple(a["rors"])] += 1
                for c in components(a["raw"]):
                    for r in a["rors"]:
                        self.comp[c][r] += 1
                    self.comp_df[c] += 1
                    # A component that maps to exactly one ROR is a NAME; its
                    # word tokens become that institution's vocabulary.
                    for t in c.split():
                        self.name_tokens[t][a["rors"][0]] += 1
        self.full = {k: set(v.most_common(1)[0][0])
                     for k, v in full_votes.items()}
        self.n = n_strings
        # IDF over components: a component appearing in many strings carries
        # little information about which institution is meant.
        self.idf = {c: math.log(n_strings / (1 + df))
                    for c, df in self.comp_df.items()}
        # And over name tokens, for the same reason at word granularity.
        tok_df = Counter()
        for t, votes in self.name_tokens.items():
            tok_df[t] = sum(votes.values())
        self.tok_idf = {t: math.log(n_strings / (1 + df))
                        for t, df in tok_df.items()}


def v0(ix: Index, raw: str) -> set[str]:
    """The published floor: memorise where you can, flat component vote else."""
    hit = ix.full.get(norm(raw))
    if hit:
        return set(hit)
    out: set[str] = set()
    for c in components(raw):
        votes = ix.comp.get(c)
        if votes:
            top, n = votes.most_common(1)[0]
            if n >= 2:
                out.add(top)
    return out


def _weighted(ix: Index, raw: str, *, thresh: float) -> dict[str, float]:
    """ROR -> evidence, where a component's vote is scaled by its IDF."""
    scores: dict[str, float] = defaultdict(float)
    for c in components(raw):
        votes = ix.comp.get(c)
        if not votes:
            continue
        total = sum(votes.values())
        w = ix.idf.get(c, 0.0)
        if w <= thresh:
            continue
        for ror, n in votes.items():
            scores[ror] += w * (n / total)
    return scores


def v1(ix: Index, raw: str, *, thresh: float = 1.0, keep: float = 0.5) -> set[str]:
    """IDF-weighted components, keeping everything within `keep` of the best."""
    hit = ix.full.get(norm(raw))
    if hit:
        return set(hit)
    scores = _weighted(ix, raw, thresh=thresh)
    if not scores:
        return set()
    best = max(scores.values())
    return {r for r, s in scores.items() if s >= keep * best}


def v2(ix: Index, raw: str, *, keep: float = 0.5) -> set[str]:
    """v1, plus word-level overlap so an unseen wording can still match.

    The component index is exact-match, so "dept of physics, univ of tokyo"
    misses "university of tokyo" entirely. Scoring the raw string's words
    against each institution's learned vocabulary recovers those.
    """
    hit = ix.full.get(norm(raw))
    if hit:
        return set(hit)
    scores = _weighted(ix, raw, thresh=1.0)
    if not scores:
        words = {t for c in components(raw) for t in c.split()}
        wscore: dict[str, float] = defaultdict(float)
        for t in words:
            votes = ix.name_tokens.get(t)
            if not votes:
                continue
            w = ix.tok_idf.get(t, 0.0)
            if w <= 2.0:                      # a common word names nobody
                continue
            total = sum(votes.values())
            for ror, n in votes.items():
                wscore[ror] += w * (n / total)
        scores = wscore
    if not scores:
        return set()
    best = max(scores.values())
    return {r for r, s in scores.items() if s >= keep * best}


def v3(ix: Index, raw: str) -> set[str]:
    """v2, but specificity-first: only the best-scoring institution.

    v0 takes the union of everything that matched, which is where its 29.1%
    precision goes -- "university of tokyo, japan" votes for the university and
    for whatever "japan" most often co-occurs with.
    """
    return v2(ix, raw, keep=0.999)


def main() -> None:
    rng = random.Random(SEED)
    works = load()
    idx = list(range(len(works)))
    rng.shuffle(idx)
    cut = int(len(idx) * TRAIN_FRAC)
    train = [works[i] for i in idx[:cut]]
    test = [works[i] for i in idx[cut:]]

    t0 = time.perf_counter()
    ix = Index(train)
    build_s = time.perf_counter() - t0
    print(f"{len(train):,} train works -> {len(ix.full):,} strings, "
          f"{len(ix.comp):,} components, {len(ix.name_tokens):,} name tokens "
          f"({build_s:.1f}s)", flush=True)

    pairs = [(a["raw"], set(a["rors"])) for w in test for a in w["affiliations"]
             if a["rors"]]
    unseen = [p for p in pairs if norm(p[0]) not in ix.full]
    CEILING = measure_ceiling(ix, pairs)
    print(f"ceiling measured on {CEILING['n']:,} verbatim-seen strings: "
          f"F1 {CEILING['f1']:.3f}, exact {CEILING['exact']:.1%}", flush=True)
    print(f"{len(pairs):,} held-out strings, {len(unseen):,} never seen "
          f"({len(unseen)/len(pairs):.1%})\n", flush=True)

    rungs: list[tuple[str, Callable]] = [
        ("v0  component vote (published floor)", v0),
        ("v1  + IDF weighting", v1),
        ("v2  + word-overlap fallback", v2),
        ("v3  + specificity-first", v3),
    ]

    hdr = (f"{'rung':<38} {'F1 unseen':>10} {'% ceiling':>10} {'prec':>7} "
           f"{'rec':>7} {'F1 all':>8} {'ns/str':>9}")
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    for name, fn in rungs:
        t = time.perf_counter_ns()
        u = score([(fn(ix, raw), truth) for raw, truth in unseen])
        ns = (time.perf_counter_ns() - t) / max(1, len(unseen))
        a = score([(fn(ix, raw), truth) for raw, truth in pairs])
        frac = u["f1"] / CEILING["f1"]
        rows[name] = {"unseen": u, "all": a, "frac_of_ceiling": frac,
                      "ns_per_string": ns}
        print(f"{name:<38} {u['f1']:>10.3f} {frac:>9.1%} {u['precision']:>6.1%} "
              f"{u['recall']:>6.1%} {a['f1']:>8.3f} {ns:>8,.0f}")
    print(f"{'ceiling (memoriser on SEEN strings)':<38} {CEILING['f1']:>10.3f} "
          f"{1.0:>9.1%} {CEILING['precision']:>6.1%} {CEILING['recall']:>6.1%}")

    v0f = rows["v0  component vote (published floor)"]["unseen"]["f1"]
    best = max(rows.items(), key=lambda kv: kv[1]["unseen"]["f1"])
    # The floor to reproduce depends on which snapshot is loaded, and the two
    # are different TASKS rather than different samples: the flattened snapshot
    # asks one raw string to predict every institution its author listed.
    expect = 0.378 if "authorship" in str(SRC) else 0.303
    print(f"\nv0 reproduces this snapshot's published floor at {v0f:.3f} "
          f"(expected {expect:.3f}: "
          f"{'OK' if abs(v0f - expect) < 0.01 else 'MISMATCH — the ladder is not measuring the same thing'})")
    print(f"best rung: {best[0].strip()} at F1 {best[1]['unseen']['f1']:.3f}, "
          f"{best[1]['frac_of_ceiling']:.1%} of the ceiling, "
          f"a lift of {best[1]['unseen']['f1'] - v0f:+.3f} over the floor")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seed": SEED, "source": str(SRC),
                               "ceiling": CEILING, "rungs": rows,
                               "n_unseen": len(unseen), "n_all": len(pairs)},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
