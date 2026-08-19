"""1.58% is a count. The workload does not ask questions per entity.

`notes/findings/2026-08-18-structural-federation-is-gated-by-identity-federation-and-that-saturates.md`
killed the structural-federation arm on one number: only **52,860 of 3,348,427**
GLEIF entities (**1.58%**) carry a wikidata twin, so a second source's 1.28M
ownership edges collapse to 3,996 expressible ones.

That number is an **unweighted per-entity count**, and this repo has been caught
by exactly that denominator three times — coverage of held securities is 22.3%
per distinct security, 58.8% per position held and 75.0% per dollar held, a 3.4x
span over the same join. A constraint measured per entity and a workload measured
per dollar are not the same constraint.

So this is the 2x2 nobody has run: **filers and issuers, by count and by value.**
It decides whether the residual `f` of 8.17% is a **tail** phenomenon —
economically minor, most of the value addressable — or a **broad** one, in which
case identity coverage is the binding constraint on the whole reach programme.

Nothing measured so far distinguishes those, and they imply opposite next moves.

Run: uv run python -u scripts/identity_coverage_denominators.py
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from scripts.alignment_bounds import SEC, gleif_candidates
from symbolic_ai_tasks.company_key import (fit_strip_set, load_task,
                                           predict_fitted)

WD = Path("data/sources/wikidata/commandagi-r2-2026-08-15/wikidata/"
          "idbridges_full_p0.parquet")
ISIN_ZIP = Path("data/sources/gleif-isin/isin-lei-20260818.zip")
VALUED = Path("data/sources/sec-edgar/commandagi-r2-2026-08-15/finance/13f/"
              "holdings_01mar2026-31may2026_p0.parquet")
OUT = Path("runs/identity_coverage_denominators.json")


def report(name: str, weight: dict[str, float], covered: set[str]) -> dict:
    n = len(weight)
    v = sum(weight.values())
    hit = {k for k in weight if k in covered}
    hv = sum(weight[k] for k in hit)
    row = {"n": n, "by_count": len(hit) / n if n else 0.0,
           "value": v, "by_value": hv / v if v else 0.0}
    row["ratio"] = row["by_value"] / row["by_count"] if row["by_count"] else 0.0
    print(f"{name:<34} {len(hit):>7,}/{n:<8,} = {row['by_count']:>6.1%}   "
          f"{row['by_value']:>6.1%}   {row['ratio']:>5.1f}x")
    return row


def main() -> None:
    t = pq.read_table(WD)
    lei_qid = {g.split(":")[-1] for s, g in
               zip(t.column("source_id").to_pylist(),
                   t.column("target_id").to_pylist())
               if g.startswith("kg:lei:")}
    cik_qid = {g.split(":")[-1].lstrip("0") for s, g in
               zip(t.column("source_id").to_pylist(),
                   t.column("target_id").to_pylist())
               if g.startswith("kg:sec:")}
    print(f"wikidata twins: {len(lei_qid):,} LEIs, {len(cik_qid):,} CIKs\n",
          flush=True)

    # --- the workload: 13F positions. MAX per (filer, security) because an
    # amended filing repeats the position.
    h = pq.read_table(VALUED)
    per: dict[tuple[str, str], float] = {}
    for s, c, k, v in zip(h.column("source_id").to_pylist(),
                          h.column("target_id").to_pylist(),
                          h.column("kind").to_pylist(),
                          h.column("value").to_pylist()):
        if k == "holds":
            key = (s, c.split(":")[-1].upper())
            per[key] = max(per.get(key, 0.0), float(v or 0.0))
    filer_w: dict[str, float] = defaultdict(float)
    issuer_w: dict[str, float] = defaultdict(float)
    for (f, cu), v in per.items():
        filer_w[f.split(":")[-1].lstrip("0")] += v
        issuer_w[cu] += v

    # issuers are CUSIPs; wikidata twins are keyed by LEI, so bridge through
    # GLEIF's filed ISIN->LEI mapping. isin[2:11] IS the CUSIP for US issues.
    cusip_lei: dict[str, str] = {}
    with zipfile.ZipFile(ISIN_ZIP) as z:
        nm = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(nm) as fh:
            rdr = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
            next(rdr)
            for row in rdr:
                if len(row) >= 2:
                    isin = row[1].strip().upper()
                    if len(isin) == 12 and isin.startswith("US"):
                        cusip_lei.setdefault(isin[2:11], row[0].strip())
    issuer_cov = {c for c in issuer_w if cusip_lei.get(c, "") in lei_qid}

    hdr = (f"{'population':<34} {'by COUNT':>18}   {'by VALUE':>6}   "
           f"{'ratio':>5}")
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    rows["13F filers (portfolio $)"] = report(
        "13F filers, weighted by AUM", dict(filer_w), cik_qid)
    rows["held securities ($ held)"] = report(
        "held securities, weighted by $", dict(issuer_w), issuer_cov)

    # the flat baseline the null was quoted against
    g = pq.read_table("data/sources/gleif/commandagi-r2-2026-08-15/gleif/"
                      "lei2_entities_p0.parquet", columns=["id"])
    all_leis = {i.split(":")[-1]: 1.0 for i in g.column("id").to_pylist()}
    rows["all GLEIF entities (flat)"] = report(
        "all GLEIF entities, unweighted", all_leis, lei_qid)

    print()
    flat = rows["all GLEIF entities (flat)"]["by_count"]
    for name in ("13F filers (portfolio $)", "held securities ($ held)"):
        r = rows[name]
        print(f"{name:<30} {r['by_value']/flat:>7.0f}x the flat 1.58%")

    tail = 1 - max(rows["13F filers (portfolio $)"]["by_value"],
                   rows["held securities ($ held)"]["by_value"])
    print(f"\nthe unaddressable share, by the denominator the workload uses: "
          f"{tail:.1%}")
    print("A constraint measured per entity and a workload measured per dollar "
          "are not\nthe same constraint. Which reading is right is a property "
          "of the QUESTION:\nan aggregate exposure question lives in the value "
          "column; a question about a\nnamed small entity lives in the count "
          "column, and there the 1.58% stands.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"lei_twins": len(lei_qid),
                               "cik_twins": len(cik_qid), "rows": rows},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
