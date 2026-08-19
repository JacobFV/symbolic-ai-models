"""Does purchasable reach saturate everywhere, or only where money does?

`notes/findings/2026-08-18-purchasable-reach-saturates-...md` claims that
acquiring reach is cheap and then abruptly stops being worth anything: 2,383
curated crosswalk rows reach **68.8%** of $51.4T of 13F holdings while
2,281,221 filed rows reach 75.0%. The mechanism was measured as **value
concentration**, not better targeting — both crosswalks attain about two thirds
of what an oracle could at their own size.

That note names its own refuter in one clause:

> *"13F holdings are top-heavy by construction. A uniform workload -- every
> registered security equally -- would show saturation far later, and the shape
> of the value curve is the claim, not the constant."*

So this runs the refuter. Five unrelated workloads already on disk, each an
edge set with a natural per-entity mass, and one statistic that decides it:
**what share of the mass sits in the top 7.5% of entities** — 7.5% being the
count-coverage of the curated crosswalk, so the number is directly the
"could a small acquisition have covered this" question.

If they all cluster high, saturation is a law and the acquisition advice
generalises. If any workload is flat, the headline is a property of one asset
class and has to be restated as conditional on concentration.

Run: uv run python -u scripts/saturation_across_workloads.py
"""

from __future__ import annotations

import glob
import json
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

OUT = Path("runs/saturation_across_workloads.json")
#: the curated crosswalk's count-coverage, so "top K%" is the acquirable slice
K = 0.075
SRC = "data/sources"

#: (label, glob, the column whose repeats define an entity, what mass means)
WORKLOADS = [
    ("13F holdings, by $ held",
     f"{SRC}/sec-edgar/commandagi-r2-2026-08-15/finance/13f/holdings_*.parquet",
     "target_id", "value"),
    ("13F holdings, by position count",
     f"{SRC}/sec-edgar/commandagi-r2-2026-08-15/finance/13f/holdings_*.parquet",
     "target_id", None),
    ("patent citations, per cited patent",
     f"{SRC}/patentsview/commandagi-r2-2026-08-15/cite/patent_citations_p*.parquet",
     "target_id", None),
    ("patent assignees, per assignee",
     f"{SRC}/patentsview/commandagi-r2-2026-08-15/assignee/patent_assignee_p*.parquet",
     "target_id", None),
    ("caselaw citations, per cited case",
     f"{SRC}/courtlistener/commandagi-r2-2026-08-15/caselaw/citation_map_p*.parquet",
     "target_id", None),
    ("github events, per repo",
     f"{SRC}/gh-archive/commandagi-r2-2026-08-15/gharchive/events_*.parquet",
     "target_id", None),
]


def mass_for(pattern: str, key: str, value: str | None) -> dict[str, float]:
    w: dict[str, float] = defaultdict(float)
    cols = [key] + ([value] if value else [])
    for p in sorted(glob.glob(pattern)):
        pf = pq.ParquetFile(p)
        have = set(pf.schema_arrow.names)
        if not set(cols) <= have:
            continue
        for b in pf.iter_batches(columns=cols):
            ks = b.column(key).to_pylist()
            if value:
                for k_, v in zip(ks, b.column(value).to_pylist()):
                    w[k_] += float(v or 0.0)
            else:
                for k_ in ks:
                    w[k_] += 1.0
    return dict(w)


def main() -> None:
    hdr = (f"{'workload':<38} {'entities':>10} {'top 7.5%':>9} {'top 1%':>7} "
           f"{'top 25%':>8} {'gini':>6}")
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    for label, pattern, key, value in WORKLOADS:
        w = mass_for(pattern, key, value)
        if not w:
            print(f"{label:<38} {'(no data)':>10}")
            continue
        vals = sorted(w.values(), reverse=True)
        tot = sum(vals)
        n = len(vals)

        def top(frac: float) -> float:
            k = max(1, int(n * frac))
            return sum(vals[:k]) / tot if tot else 0.0

        # Gini over the mass distribution, ascending order.
        asc = vals[::-1]
        cum = 0.0
        for i, v in enumerate(asc, 1):
            cum += i * v
        gini = (2 * cum) / (n * tot) - (n + 1) / n if tot else 0.0
        rows[label] = {"entities": n, "top_1pct": top(0.01),
                       "top_7_5pct": top(K), "top_25pct": top(0.25),
                       "gini": gini}
        print(f"{label:<38} {n:>10,} {top(K):>8.1%} {top(0.01):>7.1%} "
              f"{top(0.25):>7.1%} {gini:>6.3f}")

    print(f"\nthe deciding statistic is the 'top 7.5%' column: that is the "
          f"count-coverage of\nthe curated crosswalk, so it answers 'could a "
          f"small acquisition have covered\nthis workload's mass?' directly.")
    tops = {k: v["top_7_5pct"] for k, v in rows.items()}
    lo, hi = min(tops.values()), max(tops.values())
    print(f"\nspread across {len(tops)} workloads: {lo:.1%} to {hi:.1%}")
    flat = [k for k, v in tops.items() if v < 0.35]
    if flat:
        print(f"\n-> SATURATION IS DOMAIN-BOUND. These workloads do not "
              f"concentrate:")
        for k in flat:
            print(f"     {k}  ({tops[k]:.1%})")
        print("   The acquisition advice must be restated as conditional on "
              "concentration,\n   and the right move is to MEASURE the value "
              "curve before buying anything.")
    else:
        print(f"\n-> SATURATION GENERALISES. Every workload puts >= 35% of its "
              f"mass in the\n   top 7.5% of entities, so a small acquisition "
              f"covers most of any of them.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"top_k": K, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
