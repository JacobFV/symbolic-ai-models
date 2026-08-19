"""Pricing the first arrow: what it costs to turn prose into a typed world.

Every cost number this repo has published begins at the *second* arrow of
`APPROACH.md`'s thesis, because all 19 catalogued sources arrive already
structured. `scripts/fetch_openalex_prose.py` put 5,000 OpenAlex works on disk —
5,992,167 characters of real abstracts, 44,446 raw affiliation strings, and the
ROR institution ids OpenAlex resolved them to — so the arrow can be measured.

Two halves, and only one of them needs an anchor.

**A. The crossover, on prose.** `corpus_tokens / dependency_tokens` is the number
of queries a symbolic system must answer before it has paid for extracting the
world (`notes/findings/2026-08-18-the-framing-factor-we-retracted-is-the-amortisation-constant.md`).
On GLEIF it is 99,512. No ground truth is involved; it is a property of the text.

**B. Extraction agreement.** The first accuracy number this repo has ever had for
the extraction step, obtainable **without API credentials** because the opponent
is not a language model — it is OpenAlex's own resolver, whose output is on disk.

Three things this reports that the naive version would hide:

* **The anchor is agreement, not truth.** OpenAlex's institution resolution is
  itself an automated extractor. Every number in half B is *agreement with
  OpenAlex* and saying otherwise would repeat the `airport_country` circularity,
  where a task's ground truth turned out to be one side of the disagreement it
  was scored against.
* **The floor is a memoriser and it is strong.** Bibliographic text repeats
  itself, so an exact normalised-string lookup will do well. That is this repo's
  oldest trap, so the result is reported **split**: on held-out strings whose
  exact form was seen in training, and on strings never seen. Only the second
  says anything about extraction.
* **The split is by work**, so no string from an evaluated work contributed to
  the dictionary.

Run: uv run python -u scripts/first_arrow_prose.py
"""

from __future__ import annotations

import json
import os
import random
import re
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

#: Which snapshot to read. The default is the one today's published numbers came
#: from, so they stay reproducible; ``SYMBOLIC_AI_PROSE_SNAPSHOT`` selects
#: another. The `-authorship` snapshot groups an author's raw strings instead of
#: flattening them, which is the difference between a reachable label and one no
#: string-only method can reach.
_SNAP = os.environ.get("SYMBOLIC_AI_PROSE_SNAPSHOT", "openalex-prose-2026-08-18")
SRC = Path(f"data/sources/openalex-prose/{_SNAP}/works_p0.jsonl")
OUT = Path("runs/first_arrow_prose.json")
SEED = 20260818
TRAIN_FRAC = 0.7
FRONTIER_USD_PER_MTOK = 15.0
USD_PER_CORE_HOUR = 0.02

#: GLEIF's, for the comparison that is the point of half A.
GLEIF_CROSSOVER = 99_512


def norm(s: str) -> str:
    """Casefold, strip accents, collapse punctuation and whitespace.

    Deliberately dumb. A normaliser that knew about institutions would be doing
    the extraction, and the floor would stop being a floor.
    """
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.casefold()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def components(s: str) -> list[str]:
    """An affiliation string is a comma-joined path from lab to country."""
    return [norm(p) for p in re.split(r"[,;]", s) if norm(p)]


def tokens(text: str) -> float:
    """Characters over four. The same convention as every other cost row here."""
    return len(text) / 4.0


def load() -> list[dict[str, Any]]:
    return [json.loads(l) for l in SRC.read_text().splitlines() if l.strip()]


# --------------------------------------------------------------------------
# A. the crossover


def half_a(works: list[dict[str, Any]]) -> dict[str, Any]:
    corpus_chars = sum(len(w["abstract"]) + len(w["title"]) for w in works)
    corpus_tok = tokens("x" * corpus_chars)
    # The dependency of "which institutions does this work involve": its own
    # affiliation strings, and nothing else in the corpus.
    dep = [sum(len(a["raw"]) for a in w["affiliations"]) for w in works
           if w["affiliations"]]
    dep_tok = sum(dep) / len(dep) / 4.0
    facts = sum(len(a["rors"]) for w in works for a in w["affiliations"])
    crossover = corpus_tok / dep_tok
    return {
        "works": len(works), "corpus_chars": corpus_chars,
        "corpus_tokens": corpus_tok,
        "dependency_tokens_mean": dep_tok,
        "facts": facts,
        "tokens_per_fact": corpus_tok / max(1, facts),
        "crossover_queries": crossover,
        "gleif_crossover": GLEIF_CROSSOVER,
        "ratio_to_gleif": crossover / GLEIF_CROSSOVER,
        "extract_corpus_usd": corpus_tok / 1e6 * FRONTIER_USD_PER_MTOK,
    }


# --------------------------------------------------------------------------
# B. extraction agreement


def build_dictionary(train: list[dict[str, Any]]):
    """normalised string -> ROR set, at two granularities.

    ``full`` is the memoriser: the whole affiliation string, verbatim.
    ``comp`` is the extractor: each comma-separated component, which is what
    lets an unseen string be assembled from parts that were seen.
    """
    full: dict[str, Counter] = defaultdict(Counter)
    comp: dict[str, Counter] = defaultdict(Counter)
    for w in train:
        for a in w["affiliations"]:
            if not a["rors"]:
                continue
            full[norm(a["raw"])][tuple(a["rors"])] += 1
            for c in components(a["raw"]):
                for r in a["rors"]:
                    comp[c][r] += 1
    return ({k: set(v.most_common(1)[0][0]) for k, v in full.items()},
            comp)


def predict_full(full, raw: str) -> set[str]:
    return set(full.get(norm(raw), ()))


def predict_comp(full, comp, raw: str, *, min_count: int = 2) -> set[str]:
    """Memorise where you can, assemble from components where you cannot.

    A component votes for a ROR only if it did so at least ``min_count`` times
    in training — a component seen once is a coincidence, and letting it vote
    turns the extractor into a lookup of typos.
    """
    hit = predict_full(full, raw)
    if hit:
        return hit
    out: set[str] = set()
    for c in components(raw):
        votes = comp.get(c)
        if not votes:
            continue
        top, n = votes.most_common(1)[0]
        if n >= min_count:
            out.add(top)
    return out


def score(pairs) -> dict[str, Any]:
    """Exact set match, Jaccard, and per-id precision/recall."""
    exact = tp = fp = fn = 0
    jac = 0.0
    for pred, truth in pairs:
        exact += pred == truth
        tp += len(pred & truth)
        fp += len(pred - truth)
        fn += len(truth - pred)
        u = pred | truth
        jac += len(pred & truth) / len(u) if u else 1.0
    n = max(1, len(pairs))
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    return {"n": len(pairs), "exact_set_match": exact / n, "jaccard": jac / n,
            "precision": prec, "recall": rec,
            "f1": 2 * prec * rec / max(1e-9, prec + rec)}


def main() -> None:
    rng = random.Random(SEED)
    works = load()
    print(f"{len(works):,} works from {SRC}", flush=True)

    a = half_a(works)
    print("\nA. the crossover, on prose")
    print(f"  corpus            {a['corpus_chars']:,} chars = "
          f"{a['corpus_tokens']:,.0f} tokens (${a['extract_corpus_usd']:.2f} to "
          f"read once at $15/Mtok)")
    print(f"  dependency        {a['dependency_tokens_mean']:.1f} tokens per "
          f"query (the work's own affiliation strings)")
    print(f"  facts extracted   {a['facts']:,}  =>  "
          f"{a['tokens_per_fact']:.1f} corpus tokens per fact")
    print(f"  CROSSOVER         {a['crossover_queries']:,.0f} queries, against "
          f"GLEIF's {GLEIF_CROSSOVER:,} — a factor of "
          f"{a['ratio_to_gleif']:.2f}")

    # --- B
    idx = list(range(len(works)))
    rng.shuffle(idx)
    cut = int(len(idx) * TRAIN_FRAC)
    train = [works[i] for i in idx[:cut]]
    test = [works[i] for i in idx[cut:]]
    full, comp = build_dictionary(train)
    seen_strings = set(full)
    print(f"\nB. extraction agreement — {len(train):,} train works, "
          f"{len(test):,} test works, {len(full):,} distinct normalised "
          f"strings and {len(comp):,} components in the dictionary")

    eval_pairs = []
    for w in test:
        for aff in w["affiliations"]:
            if not aff["rors"]:
                continue
            eval_pairs.append((aff["raw"], set(aff["rors"])))
    was_seen = [p for p in eval_pairs if norm(p[0]) in seen_strings]
    unseen = [p for p in eval_pairs if norm(p[0]) not in seen_strings]
    print(f"   {len(eval_pairs):,} held-out affiliation strings; "
          f"{len(was_seen):,} ({len(was_seen)/max(1,len(eval_pairs)):.1%}) "
          f"appear verbatim in training, {len(unseen):,} never do")

    t0 = time.perf_counter_ns()
    rows = {}
    for name, slice_, fn in (
            ("memoriser  (full-string)      ALL", eval_pairs, predict_full),
            ("extractor  (components)       ALL", eval_pairs, predict_comp),
            ("memoriser  (full-string)     SEEN", was_seen, predict_full),
            ("extractor  (components)      SEEN", was_seen, predict_comp),
            ("memoriser  (full-string)   UNSEEN", unseen, predict_full),
            ("extractor  (components)   UNSEEN", unseen, predict_comp)):
        preds = [(fn(full, raw) if fn is predict_full
                  else fn(full, comp, raw), truth) for raw, truth in slice_]
        rows[name] = score(preds)
    extract_ns = time.perf_counter_ns() - t0

    print()
    hdr = (f"{'':<36} {'n':>7} {'exact':>8} {'jaccard':>9} {'prec':>7} "
           f"{'rec':>7} {'f1':>7}")
    print(hdr)
    print("-" * len(hdr))
    for name, r in rows.items():
        print(f"{name:<36} {r['n']:>7,} {r['exact_set_match']:>7.1%} "
              f"{r['jaccard']:>8.3f} {r['precision']:>6.1%} "
              f"{r['recall']:>6.1%} {r['f1']:>6.3f}")

    # --- what extraction costs, both ways
    n_str = len(eval_pairs)
    sym_ns_per = extract_ns / max(1, n_str * 6)          # six passes above
    sym_usd = sym_ns_per * USD_PER_CORE_HOUR / 3600 / 1e9
    llm_tok = sum(tokens(raw) for raw, _ in eval_pairs) / max(1, n_str)
    llm_usd = llm_tok / 1e6 * FRONTIER_USD_PER_MTOK
    print(f"\ncost per affiliation string extracted")
    print(f"  symbolic  {sym_ns_per:>10,.0f} ns  ${sym_usd:.3e}")
    print(f"  model     {llm_tok:>10.1f} tok ${llm_usd:.3e}  "
          f"(input only, zero output, perfect extraction assumed — a lower "
          f"bound, as everywhere here)")
    print(f"  ratio     {llm_usd/max(1e-30, sym_usd):>10,.0f}x")

    unseen_gap = (rows["extractor  (components)   UNSEEN"]["f1"]
                  - rows["memoriser  (full-string)   UNSEEN"]["f1"])
    print(f"\nthe number a memoriser cannot buy: F1 on strings never seen in "
          f"training is {rows['extractor  (components)   UNSEEN']['f1']:.3f} "
          f"for the extractor against {rows['memoriser  (full-string)   UNSEEN']['f1']:.3f} "
          f"for the memoriser (+{unseen_gap:.3f})")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "seed": SEED, "source": str(SRC), "half_a": a,
        "half_b": {k: v for k, v in rows.items()},
        "seen_fraction": len(was_seen) / max(1, len(eval_pairs)),
        "cost": {"symbolic_ns_per_string": sym_ns_per,
                 "symbolic_usd_per_string": sym_usd,
                 "llm_tokens_per_string": llm_tok,
                 "llm_usd_per_string": llm_usd},
        "anchor_caveat": ("every agreement number is agreement with OpenAlex's "
                          "own automated resolver, not accuracy against truth"),
    }, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
