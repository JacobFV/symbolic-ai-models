"""The bound's width is attributable, and the attribution is concentrated.

`notes/findings/2026-08-18-three-sources-two-joins-and-an-answer-that-has-to-be-an-interval.md`
left the slice usable for **25.2%** of filers: honest, and not a product. Its
successor established *why* the bound is the right output — an estimate scores
95.9% under an assumption that is demonstrably false here, and the bound's width
is the same ignorance made visible.

What neither used is that `additive_bounds` already reports **where the width
comes from**. `Bounds.width_by_subject` carries `(subject, contribution)` widest
first, and its docstring says exactly why: *"a bound with no attribution says the
answer is uncertain and nothing about which disagreement to go and settle."*

So: go and settle them, widest first. Each unbridged position resolved is one
escalation — a model call, a lookup, a human — and the question is **how few**.

This is the escalation lesson with a magnitude ordering added. The earlier
finding was *escalate where the system produces nothing, not where it is
unsure*; here every candidate produces nothing, so the ordering that remains is
**how much width each one carries**.

Run: uv run python -u scripts/bound_attribution.py
"""

from __future__ import annotations

import collections
import csv
import io
import json
import random
import statistics
import zipfile
from pathlib import Path

import pyarrow.parquet as pq

from symbolic_ai_core.runtime.ambiguity import Alternatives, additive_bounds

ISIN_ZIP = Path("data/sources/gleif-isin/isin-lei-20260818.zip")
VALUED = Path("data/sources/sec-edgar/commandagi-r2-2026-08-15/finance/13f/"
              "holdings_01mar2026-31may2026_p0.parquet")
GLEIF = Path("data/sources/gleif/commandagi-r2-2026-08-15/gleif/"
             "lei2_entities_p0.parquet")
OUT = Path("runs/bound_attribution.json")
SEED = 20260818
N = 500
COUNTRY = "US"
TARGET = 0.20
MODEL_USD = 4.535e-03
STEPS = (0, 1, 5, 10, 20, 40)


def main() -> None:
    rng = random.Random(SEED)
    cusip_lei: dict[str, str] = {}
    with zipfile.ZipFile(ISIN_ZIP) as z:
        nm = [x for x in z.namelist() if x.lower().endswith(".csv")][0]
        with z.open(nm) as fh:
            r = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
            next(r)
            for lei, isin in r:
                isin = isin.strip().upper()
                if len(isin) == 12 and isin.startswith("US"):
                    cusip_lei.setdefault(isin[2:11], lei.strip())
    g = pq.read_table(GLEIF, columns=["id", "body"])
    lei_c = {i.split(":")[-1]: (b or "")
             for i, b in zip(g.column("id").to_pylist(),
                             g.column("body").to_pylist())}
    t = pq.read_table(VALUED)
    port: dict[str, dict[str, float]] = collections.defaultdict(dict)
    for s, c, k, v in zip(t.column("source_id").to_pylist(),
                          t.column("target_id").to_pylist(),
                          t.column("kind").to_pylist(),
                          t.column("value").to_pylist()):
        if k != "holds":
            continue
        cu = c.split(":")[-1].upper()
        port[s][cu] = max(port[s].get(cu, 0.0), float(v or 0.0))

    filers = [f for f in rng.sample(sorted(port), N + 200)
              if sum(port[f].values()) > 0][:N]
    top5, needed = [], []
    curve: dict[int, list[float]] = collections.defaultdict(list)
    for f in filers:
        pos = port[f]
        total = sum(pos.values())
        known = 0.0
        unk: dict[str, float] = {}
        for c, v in pos.items():
            ctry = lei_c.get(cusip_lei.get(c, ""), "")
            if not ctry:
                unk[c] = v
            elif ctry == COUNTRY:
                known += v
        if not unk:
            continue
        alts = Alternatives({("country", c): (COUNTRY, "other") for c in unk})
        b = additive_bounds(alts,
                            lambda s, v: unk[s[1]] if v == COUNTRY else 0.0,
                            base=known)
        ws = [w for _, w in b.width_by_subject]      # widest first, from Bounds
        if not ws or sum(ws) <= 0:
            continue
        top5.append(sum(ws[:5]) / sum(ws))
        # EVERY filer contributes at EVERY k. Stopping a filer once it crosses
        # the target and omitting it from later k conditions each column on a
        # different, shrinking population -- which produced a NON-MONOTONE
        # curve (28.6% at k=1, 32.3% at k=5) and is how the bug was caught.
        for k in STEPS:
            curve[k].append(sum(ws[k:]) / total)
        needed.append(next((k for k in range(1, len(ws) + 1)
                            if sum(ws[k:]) / total <= TARGET), len(ws)))

    ns = sorted(needed)
    print(f"{len(needed)} filers with a non-degenerate band\n")
    print(f"width carried by the 5 widest unbridged positions: "
          f"p50 {statistics.median(top5):.1%}, mean {statistics.mean(top5):.1%}")
    print(f"lookups to bring the band under {TARGET:.0%}: "
          f"p50 {ns[len(ns)//2]}, p90 {ns[int(len(ns)*0.9)]}, max {ns[-1]}\n")
    hdr = f"{'lookups':>8} {'median band':>13} {'filers under target':>21} {'$/portfolio':>13}"
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    for k in STEPS:
        v = curve[k]
        under = sum(1 for x in v if x <= TARGET) / len(v)
        rows[k] = {"median_band": statistics.median(v), "under_target": under,
                   "usd": k * MODEL_USD}
        print(f"{k:>8} {statistics.median(v):>12.1%} {under:>20.1%} "
              f"{k*MODEL_USD:>12.3f}")

    print(f"\nTen lookups put {rows[10]['under_target']:.1%} of filers inside a "
          f"{TARGET:.0%} band for ${rows[10]['usd']:.3f} per portfolio.")
    print("The bound was never just honest — it came with the list of what to "
          "go and\nresolve, and that list is short because portfolio value is "
          "concentrated.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"seed": SEED, "n": len(needed), "target": TARGET,
         "top5_share_p50": statistics.median(top5),
         "lookups_p50": ns[len(ns)//2], "lookups_p90": ns[int(len(ns)*0.9)],
         "curve": {str(k): v for k, v in rows.items()}}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
