"""What the world costs to build, and how many queries it takes to pay for it.

`CLAUDE.md` states the rule this script exists to apply:

> Cost is charged to the **system**: if a reasoner only works because something
> upstream produced a graph, that upstream component is in the ledger whether or
> not it exists yet.

It is not in the ledger. Every advantage number this repo has published begins
at the *second* arrow of `APPROACH.md`'s own thesis — `typed world -> cost-aware
computation` — because all 19 catalogued sources arrive **already structured**.
Verified across the 14 GB: every table is either `(id, label, kind, body,
source_url)` or `(source_id, target_id, kind)`; the longest natural-language
field in the corpus is a **patent title**, mean 59.4 characters; `body` is
key-value metadata (`issued=1971-12-01 type=Text`) or empty; and courtlistener,
the one source whose name promises prose, is a 77M-edge citation map with no
text column at all.

So the first arrow — `arbitrary observations -> typed world` — has never been
priced, and there is nothing on disk on which it could be.

This does not need a new experiment. Both terms are already measured, and the
question is arithmetic:

    breakeven_queries  =  cost of extracting the corpus  /  saving per query

Everything is read from numbers already published rather than re-derived, and
every assumption is printed rather than assumed, because a ratio without its
price sheet is not a number.

Run: uv run python -u scripts/extraction_breakeven.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path("runs/extraction_breakeven.json")

# --- from notes/findings/2026-08-18-the-advantage-curve-was-mostly-the-framing
#     -and-what-is-left-is-a-constant.md, and HANDOVER.md section 3.
CORPUS_TOKENS = 4.08e6          #: the GLEIF ownership corpus, chars/4
DEPENDENCY_TOKENS = 41.0        #: mean necessary context for a point query
FRONTIER_USD_PER_MTOK = 15.0    #: the repo's published price sheet
CHEAP_USD_PER_MTOK = 1.0
SYMBOLIC_USD_PER_QUERY = 1.56e-11   #: 2.8 us at $0.02/core-hour

# --- from notes/findings/2026-08-18-a-query-pays-for-the-conflicts-it-reads...
#     and the 13F maintenance arm.
QUARTERLY_CHURN = 0.32          #: 744,136 of 2,282,570 13F edges moved in one quarter
FILINGS_PER_QUARTER = 8425


def usd(tokens: float, rate: float) -> float:
    return tokens / 1e6 * rate


def main() -> None:
    rows = []
    for label, rate in (("frontier", FRONTIER_USD_PER_MTOK),
                        ("cheap", CHEAP_USD_PER_MTOK)):
        # Extraction: a model must read the corpus once to turn it into facts.
        # Input tokens only, zero output, perfect extraction assumed — the same
        # lower-bound convention every other cost row here uses, and the same
        # reason none of them carries an equal-accuracy assumption.
        extract = usd(CORPUS_TOKENS, rate)
        # The opponent worth beating: an oracle retriever that already knows the
        # dependency and pays only for it. Beating the whole-corpus framing is
        # what cost this repo 99,738x of a published advantage.
        per_query_llm = usd(DEPENDENCY_TOKENS, rate)
        saving = per_query_llm - SYMBOLIC_USD_PER_QUERY
        breakeven = extract / saving
        rows.append({
            "price_sheet": label, "usd_per_mtok": rate,
            "extract_corpus_usd": extract,
            "llm_usd_per_query": per_query_llm,
            "symbolic_usd_per_query": SYMBOLIC_USD_PER_QUERY,
            "saving_per_query_usd": saving,
            "breakeven_queries": breakeven,
            # Facts change. If the corpus must be re-extracted as it churns, the
            # build cost recurs and the bar becomes a RATE rather than a total.
            "breakeven_queries_per_quarter_at_32pc_churn":
                breakeven * QUARTERLY_CHURN,
            "breakeven_queries_per_day":
                breakeven * QUARTERLY_CHURN / 91.0,
        })

    print("If the world must be EXTRACTED by a language model, how many queries "
          "does\nthe symbolic system have to answer before it has paid for "
          "building it?\n")
    hdr = (f"{'price sheet':<12} {'extract corpus':>15} {'LLM $/query':>13} "
           f"{'saving/query':>13} {'breakeven':>13} {'/quarter':>11} {'/day':>9}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['price_sheet']:<12} ${r['extract_corpus_usd']:>14,.2f} "
              f"${r['llm_usd_per_query']:>12.2e} "
              f"${r['saving_per_query_usd']:>12.2e} "
              f"{r['breakeven_queries']:>12,.0f} "
              f"{r['breakeven_queries_per_quarter_at_32pc_churn']:>10,.0f} "
              f"{r['breakeven_queries_per_day']:>8,.0f}")

    f = rows[0]
    print(f"\nAt the frontier price sheet the corpus costs "
          f"${f['extract_corpus_usd']:,.2f} to turn into facts, and each query "
          f"thereafter\nsaves ${f['saving_per_query_usd']:.2e}. So the symbolic "
          f"path pays for itself after "
          f"{f['breakeven_queries']:,.0f} queries —\nand if 32% of the facts "
          f"churn per quarter, it must sustain "
          f"{f['breakeven_queries_per_day']:,.0f} queries a day\nto stay ahead "
          f"of its own re-extraction.")

    print("\nThe two things this does NOT say:\n"
          "  * that extraction must be done by a model. GLEIF and SEC arrive\n"
          "    structured because a REGULATOR already paid this cost and\n"
          "    externalised it. That is a real and legitimate answer, and it is\n"
          "    why the published per-query advantage is not wrong.\n"
          "  * that the ~5e7 per-query advantage is overstated. It is not. It\n"
          "    is real and it lives entirely on the far side of this crossover.")
    print("\nWhat it does say: the advantage is an AMORTISATION argument, and\n"
          "the programme has never measured its own first arrow. For a domain\n"
          "where structure is already filed the bar is met by construction. For\n"
          "one where structure must be derived from observation — the domain\n"
          "APPROACH.md actually names as the target — it is unmeasured, and\n"
          "there is no corpus on disk on which it could be measured.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"inputs": {
        "corpus_tokens": CORPUS_TOKENS,
        "dependency_tokens": DEPENDENCY_TOKENS,
        "symbolic_usd_per_query": SYMBOLIC_USD_PER_QUERY,
        "quarterly_churn": QUARTERLY_CHURN,
        "filings_per_quarter": FILINGS_PER_QUARTER}, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
