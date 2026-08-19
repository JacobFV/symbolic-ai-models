"""Where the advantage lives: it tracks how many identity boundaries a query crosses.

`notes/findings/2026-08-18-the-million-fold-advantage-is-8x-the-moment-you-escalate-anything.md`
closed the cost arc with a hard negative: the advantage is `1/f`, neither the
extractor's accuracy nor the escalated prompt moves it, and at 0.85 quality the
symbolic layer buys **1.8×**.

That finding named its own escape hatch in one clause — *a task where `f` is
naturally small, regulatory data, where structure is already filed* — and this
tests it, from numbers that were already on disk before the session began.

**`f` is the fraction of queries the symbolic system cannot settle**, and for a
filed domain it is not "everything the extractor got wrong". It is the queries
the *data itself* leaves undetermined, which `HANDOVER.md` §3 records at
**0.216%** (filed-vs-filed conflicts) and **4.274%** (once closure-vs-filed
conflicts are counted). There is no extraction step to fail, because the
regulator already did it and is legally accountable for it.

**And "filed" is not one regime.** A query that stays inside one source, using
that source's own identifiers, has nothing to contest but genuine real-world
disputes. A query that crosses two *filed* sources with no shared identifier has
to join through names, and `notes/findings/...alignment-not-merge-is-load-bearing...`
measured **14.7%** of matched SEC filers as having more than one GLEIF candidate.
That is a third rung, sitting 68x below the single-source number and 8x above the
derived one.

Same arithmetic, same technology, same price sheet. What changes is how many
identity boundaries the query crosses.

Run: uv run python -u scripts/regime_dichotomy.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path("runs/regime_dichotomy.json")

#: HANDOVER.md §3, the retrieval-rounds and scoped-ambiguity findings: necessary
#: context for one GLEIF point query, mean over 117,129 queries.
GLEIF_DEPENDENCY_TOKENS = 41.0
#: the same section: 2.8 µs per scoped point query at $0.02/core-hour
GLEIF_OURS_USD = 1.56e-11
#: scripts/first_arrow_prose.py and session_ledger.py, for the derived regime
DERIVED_DEPENDENCY_TOKENS = 302.3
DERIVED_OURS_USD = 2.2e-09
FRONTIER_USD_PER_MTOK = 15.0

REGIMES = [
    # name, f, quality, dependency tokens, our cost, where the numbers come from
    ("FILED   GLEIF ultimate_parent, filed-vs-filed", 0.00216, 1.00,
     GLEIF_DEPENDENCY_TOKENS, GLEIF_OURS_USD,
     "HANDOVER §3: 253 of 117,129 answers undetermined"),
    ("FILED   same, incl. closure-vs-filed conflicts", 0.04274, 1.00,
     GLEIF_DEPENDENCY_TOKENS, GLEIF_OURS_USD,
     "HANDOVER §3: 5,006 of 117,129 undetermined"),
    ("FILED   SEC -> GLEIF alignment, CROSS-SOURCE", 0.147, 1.00,
     GLEIF_DEPENDENCY_TOKENS, GLEIF_OURS_USD,
     "notes/findings/...alignment-not-merge-is-load-bearing...: 598 of 4,068 "
     "matched filers have more than one GLEIF candidate"),
    ("DERIVED OpenAlex affiliation -> ROR", 0.560, 0.85,
     DERIVED_DEPENDENCY_TOKENS, DERIVED_OURS_USD,
     "escalation_frontier.py: f needed for 0.85 quality"),
]


def main() -> None:
    print("advantage = model / (f x model + (1-f) x ours), the same formula in "
          "both regimes\n")
    hdr = (f"{'regime':<48} {'f':>8} {'quality':>8} {'model $':>10} "
           f"{'ours $':>10} {'advantage':>11}")
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    for name, f, q, tok, ours, src in REGIMES:
        model = tok / 1e6 * FRONTIER_USD_PER_MTOK
        adv = model / (f * model + (1 - f) * ours)
        rows[name.strip()] = {"f": f, "quality": q, "model_usd": model,
                              "ours_usd": ours, "advantage": adv, "source": src}
        print(f"{name:<48} {f:>7.3%} {q:>8.2f} {model:>10.2e} {ours:>10.2e} "
              f"{adv:>10.0f}x")

    filed = rows["FILED   GLEIF ultimate_parent, filed-vs-filed"]["advantage"]
    cross = rows["FILED   SEC -> GLEIF alignment, CROSS-SOURCE"]["advantage"]
    derived = rows["DERIVED OpenAlex affiliation -> ROR"]["advantage"]
    print(f"\nbetween regimes: {filed/cross:,.0f}x from single-source to "
          f"cross-source, {cross/derived:,.0f}x from cross-source to derived, "
          f"{filed/derived:,.0f}x end to end")
    print("\nSame formula, same technology, same price sheet. What changes is "
          "HOW MANY\nIDENTITY BOUNDARIES THE QUERY CROSSES:")
    print("  within one source, using its own identifiers -- nothing to contest "
          "but\n    genuine real-world disputes (contested ownership)")
    print("  across two FILED sources with no shared identifier -- the join goes "
          "through\n    names, and one filer in seven matches more than one "
          "entity")
    print("  from unstructured text -- the whole structure has to be derived")

    print("\nTwo caveats that belong next to the number:")
    print("  * quality 1.0 in the filed regime is relative to THE FILING, the "
          "same anchor\n    circularity as OpenAlex being its own ground truth "
          "— though a legally\n    accountable filer is a better anchor than an "
          "automated extractor.")
    print("  * f counts UNDETERMINED answers as escalations. A caller that can "
          "act on a\n    retained mixture — which this repo's ambiguity "
          "machinery returns, with the\n    alternatives enumerated — escalates "
          "none of them, and f is lower still.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rows": rows,
                               "between_regimes": {
                                   "single_to_cross_source": filed / cross,
                                   "cross_source_to_derived": cross / derived,
                                   "end_to_end": filed / derived}},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
