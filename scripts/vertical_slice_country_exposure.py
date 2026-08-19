"""Three filed sources, two joins, one answer that has to be an interval.

Fifteen cycles of this session measured costs and never demonstrated a working
capability end to end. The mandate asks for a vertical slice — input, a shared
world, sources that compose, a certificate, a price — and the bridge acquired
last cycle makes one possible for the first time:

    13F holdings          filer (CIK) -> security (CUSIP)      2.36M edges
    GLEIF ISIN->LEI       CUSIP -> LEI                         2.28M US CUSIPs
    GLEIF entities        LEI -> country                       3.35M entities

**The question:** what is the country exposure of a 13F filer's portfolio? Real,
valuable, and unanswerable without federation.

**Why it cannot be a point estimate, and why that is the interesting part.** The
bridge covers 22.3% of held securities
(`notes/findings/2026-08-18-the-advantage-is-a-property-of-provenance-...`), so
for a typical portfolio most positions have unknown domicile. Collapsing that to
"of the ones we know, X% are US" would be a silent lie — it reports a conditional
as a share. The honest answer is an **interval**, and this repo already has exact
attained bounds built for precisely that shape: `additive_bounds` returns the
true extremes with the assignment that realises each, in linear time.

So the slice is also the first test of whether the ambiguity machinery composes
with a real federated query rather than with a constructed one.

Run: uv run python -u scripts/vertical_slice_country_exposure.py
"""

from __future__ import annotations

import csv
import io
import json
import random
import statistics
import time
import zipfile
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from symbolic_ai_core.runtime.ambiguity import Alternatives, additive_bounds

ISIN_ZIP = Path("data/sources/gleif-isin/isin-lei-20260818.zip")
VALUED = Path("data/sources/sec-edgar/commandagi-r2-2026-08-15/finance/13f/"
              "holdings_01mar2026-31may2026_p0.parquet")
GLEIF = Path("data/sources/gleif/commandagi-r2-2026-08-15/gleif/"
             "lei2_entities_p0.parquet")
OUT = Path("runs/vertical_slice_country_exposure.json")
SEED = 20260818
N_FILERS = 500
COUNTRY = "US"
#: an actionable interval, chosen before the run: a 20-point band on a share
ACTIONABLE_WIDTH = 0.20


def main() -> None:
    rng = random.Random(SEED)
    t0 = time.perf_counter()

    print("join 1: CUSIP -> LEI", flush=True)
    cusip_lei: dict[str, str] = {}
    with zipfile.ZipFile(ISIN_ZIP) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(name) as fh:
            rdr = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
            next(rdr)
            for lei, isin in rdr:
                isin = isin.strip().upper()
                if len(isin) == 12 and isin.startswith("US"):
                    cusip_lei.setdefault(isin[2:11], lei.strip())
    print(f"  {len(cusip_lei):,} US CUSIPs", flush=True)

    print("join 2: LEI -> country", flush=True)
    g = pq.read_table(GLEIF, columns=["id", "body"])
    lei_country = {i.split(":")[-1]: (b or "")
                   for i, b in zip(g.column("id").to_pylist(),
                                   g.column("body").to_pylist())}
    print(f"  {len(lei_country):,} entities", flush=True)

    print("the world: filer -> positions, with reported value", flush=True)
    h = pq.read_table(VALUED)
    portfolios: dict[str, dict[str, float]] = defaultdict(dict)
    for s, c, k, v in zip(h.column("source_id").to_pylist(),
                          h.column("target_id").to_pylist(),
                          h.column("kind").to_pylist(),
                          h.column("value").to_pylist()):
        if k != "holds":          # calls and puts are a different question
            continue
        cu = c.split(":")[-1].upper()
        # MAX, not sum: the same filer appears twice for the same security when
        # a filing is amended (cik 2100119 holds AAPL at both 242.077e9 and
        # 241.721e9), and summing would double-count the amendment.
        prev = portfolios[s].get(cu, 0.0)
        portfolios[s][cu] = max(prev, float(v or 0.0))
    build_s = time.perf_counter() - t0
    print(f"  {len(portfolios):,} filers, built in {build_s:.1f}s", flush=True)

    filers = rng.sample(sorted(portfolios), min(N_FILERS, len(portfolios)))
    rows = []
    skipped_zero_value: list[str] = []
    t1 = time.perf_counter_ns()
    for f in filers:
        pos = portfolios[f]
        if not pos:
            continue
        known_c = 0.0
        unknown_w: dict[str, float] = {}
        n_bridged = 0
        witness: list[str] = []
        for c, val in pos.items():
            lei = cusip_lei.get(c)
            country = lei_country.get(lei or "", "")
            if not country:
                unknown_w[c] = val
            else:
                n_bridged += 1
                if country == COUNTRY:
                    known_c += val
                    witness.append(c)
        # Each unresolved position is a subject whose country is one of
        # {COUNTRY, other}, and its CONTRIBUTION is its reported value rather
        # than 1. `additive_bounds` returns the attained extremes and the
        # assignment realising each -- not an interval relaxation.
        alts = Alternatives({("country", c): (COUNTRY, "other")
                             for c in unknown_w})
        b = additive_bounds(
            alts, lambda s, v: unknown_w[s[1]] if v == COUNTRY else 0.0,
            base=known_c)
        total = sum(pos.values())
        if total <= 0:
            # A filer whose every reported value is missing or zero yields
            # base 0 and contributions 0, i.e. a spurious ZERO-WIDTH band that
            # counts as perfectly determined. The degenerate row printed as
            # "tightest" is how this was caught; dropping it rather than
            # dividing by a placeholder 1.0 is the fix.
            skipped_zero_value.append(f)
            continue
        rows.append({"filer": f, "positions": len(pos), "bridged": n_bridged,
                     "value_total": total,
                     "value_bridged": total - sum(unknown_w.values()),
                     "known_in_country": known_c,
                     "low": b.low / total, "high": b.high / total,
                     "width": (b.high - b.low) / total,
                     "witness_size": len(witness)})
    query_ns = (time.perf_counter_ns() - t1) / max(1, len(rows))
    if skipped_zero_value:
        print(f"\ndropped {len(skipped_zero_value)} of {len(filers)} filers "
              f"whose every reported value is zero or missing; they would have "
              f"scored as perfectly determined")

    widths = sorted(r["width"] for r in rows)
    # Coverage has two denominators and they differ by 2.7x. Per DISTINCT
    # SECURITY it is 22.3% (the last finding's number); per POSITION HELD it is
    # far higher, because portfolios concentrate on widely-held large caps and
    # those are exactly the issuers that carry an LEI. Which one is right
    # depends on whether the workload asks about securities or about portfolios.
    total_pos = sum(r["positions"] for r in rows)
    total_bridged = sum(r["bridged"] for r in rows)
    val_total = sum(r["value_total"] for r in rows)
    val_bridged = sum(r["value_bridged"] for r in rows)
    print(f"\ncoverage has THREE denominators, and they span 4x:")
    print(f"  per DISTINCT SECURITY  22.3%")
    print(f"  per POSITION HELD      {total_bridged/total_pos:.1%}   "
          f"({total_bridged:,}/{total_pos:,})")
    print(f"  per DOLLAR HELD        {val_bridged/val_total:.1%}   "
          f"(${val_bridged/1e12:.2f}T of ${val_total/1e12:.2f}T)")
    bridged = [r["value_bridged"] / max(1e-9, r["value_total"]) for r in rows]
    actionable = [r for r in rows if r["width"] <= ACTIONABLE_WIDTH]
    print(f"\n{len(rows)} filers answered, {query_ns:,.0f} ns each")
    print(f"  positions per filer: p50 "
          f"{sorted(r['positions'] for r in rows)[len(rows)//2]:,}")
    print(f"  bridged share of a portfolio BY VALUE: p50 {statistics.median(bridged):.1%}, "
          f"mean {statistics.mean(bridged):.1%}")
    print(f"\n{COUNTRY} exposure, as exact attained bounds:")
    print(f"  interval width: p10 {widths[len(widths)//10]:.1%}, "
          f"p50 {widths[len(widths)//2]:.1%}, "
          f"p90 {widths[int(len(widths)*0.9)]:.1%}")
    print(f"  filers with a band <= {ACTIONABLE_WIDTH:.0%}: "
          f"{len(actionable)}/{len(rows)} = {len(actionable)/len(rows):.1%}")

    ex = min(rows, key=lambda r: r["width"])
    print(f"\ntightest: {ex['filer'].split(':')[-1]} — "
          f"{ex['positions']:,} positions, {ex['bridged']:,} bridged, "
          f"{COUNTRY} share by value in [{ex['low']:.1%}, {ex['high']:.1%}]")
    med = sorted(rows, key=lambda r: r["width"])[len(rows)//2]
    print(f"median-width: {med['filer'].split(':')[-1]} — "
          f"{med['positions']:,} positions, {med['bridged']:,} bridged, "
          f"{COUNTRY} share by value in [{med['low']:.1%}, {med['high']:.1%}]")

    print(f"\nThe lower bound carries a WITNESS — the bridged positions whose "
          f"issuer\nis domiciled in {COUNTRY} — and a reader checks it by "
          f"following two\nidentifier joins per position, with no search and no "
          f"trust in this script.")
    print(f"\nCost: {build_s:.1f}s to build the world once, "
          f"{query_ns/1e3:,.1f} µs per portfolio answered.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"seed": SEED, "country": COUNTRY, "n_filers": len(filers),
         "build_seconds": build_s, "query_ns": query_ns,
         "bridged_share_median": statistics.median(bridged),
         "width_p10": widths[len(widths)//10],
         "width_p50": widths[len(widths)//2],
         "width_p90": widths[int(len(widths)*0.9)],
         "actionable_fraction": len(actionable)/len(rows),
         "actionable_width_threshold": ACTIONABLE_WIDTH,
         "rows": rows[:50]}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
