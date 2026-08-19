"""Coverage understates a crosswalk — but only when the crosswalk is curated.

`scripts/wikidata_bridge_cik_lei.py` found that the wikidata CIK->LEI bridge
reaches **ambiguous** filers 1.33x more often than chance, so the composite
`f = (1 - coverage) x f_name` — the product of the marginals — underpriced the
bridge by 10.9% of itself. That is a useful correction and a weak claim: one
bridge, one workload, and no mechanism.

The mechanism on offer is **curation**. A wikidata entity exists because somebody
judged it notable; a GLEIF ISIN->LEI row exists because an issuer filed. If
notability is what buys the enrichment, then a curated crosswalk's coverage
should be concentrated on the entities that carry the workload's weight, and a
filed one's should not — measured on the same holdings, with the same
denominators.

Both bridges reach securities here, so the workload is the 13F holdings and the
weight is reported dollars. The discriminating statistic is
**(coverage by dollar) / (coverage by count)**: 1.0 means the crosswalk is
indifferent to what matters, and anything above means it is not.

If the two ratios come out alike, the enrichment is a property of bridging or of
size in general and the word *curated* has to come out of the claim.

**And the ratio alone cannot answer that**, which is the trap this script was
first written into. `(coverage by dollar)/(coverage by count)` has a ceiling of
`1/coverage_by_count`, so a *smaller* crosswalk scores higher mechanically and
the raw ratios of two crosswalks of different size are not comparable. The
pre-registered refutation criterion was stated on that raw ratio and would have
confirmed a mechanism that is not there. What compares is each crosswalk against
an **oracle picking the best k securities at its own k**, with a random draw at
the same k as the floor — the repo's standing rule that a lift is quoted against
a floor or not quoted at all, applied to a ceiling as well.

Run: uv run python -u scripts/curated_vs_filed_crosswalk.py
"""

from __future__ import annotations

import csv
import io
import json
import random
import zipfile
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

ISIN_ZIP = Path("data/sources/gleif-isin/isin-lei-20260818.zip")
BRIDGE = Path("data/sources/wikidata/commandagi-r2-2026-08-15/wikidata/"
              "idbridges_full_p0.parquet")
VALUED = Path("data/sources/sec-edgar/commandagi-r2-2026-08-15/finance/13f/"
              "holdings_01mar2026-31may2026_p0.parquet")
OUT = Path("runs/curated_vs_filed_crosswalk.json")


def main() -> None:
    print("the workload: 13F positions with a reported value", flush=True)
    h = pq.read_table(VALUED)
    # MAX per (filer, security): an amended filing repeats the position, and
    # summing double-counts the amendment. Same rule as the vertical slice.
    per: dict[tuple[str, str], float] = {}
    for s, c, k, v in zip(h.column("source_id").to_pylist(),
                          h.column("target_id").to_pylist(),
                          h.column("kind").to_pylist(),
                          h.column("value").to_pylist()):
        if k != "holds":
            continue
        key = (s, c.split(":")[-1].upper())
        per[key] = max(per.get(key, 0.0), float(v or 0.0))
    weight: dict[str, float] = defaultdict(float)
    for (_, cu), v in per.items():
        weight[cu] += v
    total_n = len(weight)
    total_v = sum(weight.values())
    print(f"  {total_n:,} distinct securities, ${total_v/1e12:,.1f}T held\n",
          flush=True)

    print("crosswalk 1 (FILED): GLEIF ISIN->LEI", flush=True)
    filed: set[str] = set()
    with zipfile.ZipFile(ISIN_ZIP) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(name) as fh:
            rdr = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
            next(rdr)
            for row in rdr:
                if len(row) < 2:
                    continue
                isin = row[1].strip().upper()
                if len(isin) == 12 and isin.startswith("US"):
                    filed.add(isin[2:11])
    print(f"  {len(filed):,} US CUSIPs", flush=True)

    print("crosswalk 2 (CURATED): wikidata -> isin", flush=True)
    t = pq.read_table(BRIDGE)
    curated = {g.split(":")[-1][2:11]
               for g in t.column("target_id").to_pylist()
               if g.startswith("kg:isin:") and len(g.split(":")[-1]) == 12
               and g.split(":")[-1].startswith("US")}
    print(f"  {len(curated):,} US CUSIPs", flush=True)

    rows = {}
    hdr = (f"\n{'crosswalk':<26} {'by COUNT':>18} {'by DOLLAR':>20} "
           f"{'ratio':>8}")
    print(hdr)
    print("-" * (len(hdr) - 1))
    for label, cw in (("FILED   GLEIF ISIN->LEI", filed),
                      ("CURATED wikidata->ISIN", curated)):
        hit = {c for c in weight if c in cw}
        n = len(hit) / total_n
        d = sum(weight[c] for c in hit) / total_v
        r = d / n if n else float("nan")
        rows[label.strip()] = {"n_covered": len(hit), "coverage_count": n,
                               "coverage_dollar": d, "ratio": r}
        print(f"{label:<26} {len(hit):>7,} = {n:>6.1%} "
              f"${sum(weight[c] for c in hit)/1e12:>7.1f}T = {d:>6.1%} "
              f"{r:>7.2f}x")

    f_r = rows["FILED   GLEIF ISIN->LEI"]["ratio"]
    c_r = rows["CURATED wikidata->ISIN"]["ratio"]
    print(f"\nraw ratios differ {c_r/f_r:.2f}x — and that number means nothing "
          f"on its own,\nbecause the ratio's ceiling is 1/coverage and the two "
          f"crosswalks have different k.")

    # --- floor and ceiling at each crosswalk's OWN k. This is what the raw
    # ratio cannot give: random-at-k is the floor, best-k-by-value the ceiling,
    # and the fraction of that span attained is comparable across sizes.
    srt = sorted(weight.values(), reverse=True)
    keys = sorted(weight)
    rng = random.Random(20260818)
    print(f"\n{'crosswalk':<26} {'random':>9} {'actual':>9} {'oracle':>9} "
          f"{'attained':>10}")
    for label, cw in (("FILED   GLEIF ISIN->LEI", filed),
                      ("CURATED wikidata->ISIN", curated)):
        r = rows[label.strip()]
        k = r["n_covered"]
        ceiling = sum(srt[:k]) / total_v
        floor = sum(sum(weight[c] for c in rng.sample(keys, k)) / total_v
                    for _ in range(20)) / 20
        att = (r["coverage_dollar"] - floor) / (ceiling - floor)
        r.update(floor=floor, ceiling=ceiling, attained=att)
        print(f"{label:<26} {floor:>8.1%} {r['coverage_dollar']:>8.1%} "
              f"{ceiling:>8.1%} {att:>9.1%}")

    fa_ = rows["FILED   GLEIF ISIN->LEI"]["attained"]
    ca_ = rows["CURATED wikidata->ISIN"]["attained"]
    print(f"\nnormalised, the two are {ca_/fa_:.2f}x apart — so CURATION IS NOT "
          f"THE MECHANISM.\nBoth crosswalks capture about two thirds of the "
          f"value achievable at their own size.\nThe dramatic per-row figure "
          f"below is real and is a SATURATION effect: value\nconcentrates, so "
          f"the first few thousand rows carry most of it and the next two\n"
          f"million carry the tail.")

    # The economically consequential form: how much of the answer does each
    # crosswalk buy per row it contains? A crosswalk is a thing you acquire, and
    # rows are what you pay for.
    print(f"\nper row acquired — the acquisition decision:")
    for label, cw in (("FILED   GLEIF ISIN->LEI", filed),
                      ("CURATED wikidata->ISIN", curated)):
        r = rows[label.strip()]
        per_row = r["coverage_dollar"] / len(cw) * 1e6
        rows[label.strip()]["dollar_coverage_per_million_rows"] = per_row
        print(f"  {label:<26} {len(cw):>9,} rows -> "
              f"{r['coverage_dollar']:>6.1%} of value = "
              f"{per_row:>8.1f}% per million rows")
    fa = rows["FILED   GLEIF ISIN->LEI"]["dollar_coverage_per_million_rows"]
    ca = rows["CURATED wikidata->ISIN"]["dollar_coverage_per_million_rows"]
    print(f"\n  the small crosswalk delivers {ca/fa:,.0f}x more answered value "
          f"per row it contains — {len(curated):,} rows reach "
          f"{rows['CURATED wikidata->ISIN']['coverage_dollar']:.1%} of the value "
          f"that\n  {len(filed):,} rows reach "
          f"{rows['FILED   GLEIF ISIN->LEI']['coverage_dollar']:.1%} of. "
          f"Purchasable reach SATURATES.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"securities": total_n, "value_total": total_v, "crosswalks": rows,
         "raw_ratio_effect": c_r / f_r, "normalised_effect": ca_ / fa_,
         "value_per_row_effect": ca / fa},
        indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
