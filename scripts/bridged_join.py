"""A cross-source join on an IDENTIFIER, not on names — and what it costs.

`notes/findings/2026-08-18-the-advantage-is-a-property-of-provenance-463x-filed-against-18x-derived.md`
found the 68× cliff at the first identity boundary and then found it
**irreducible by modelling**: SEC and GLEIF each carry a rich identifier
(CIK; LEI plus a *state* company-register number — NVIDIA is Delaware 2862596),
neither carries the other's. (The "only attribute both hold is the name"
clause is now RETRACTED — wikidata bridges both namespaces; see
`scripts/wikidata_bridge_cik_lei.py`. It does not change this script.) Its
closing sentence was that fixing this is a **data acquisition** problem.

So this acquires the data. GLEIF publishes a free daily **ISIN → LEI** mapping,
and for US securities an ISIN is literally `US` + the 9-character CUSIP + a check
digit — so `isin[2:11]` *is* the CUSIP, with no arithmetic. The 13F holdings on
disk are CUSIP-keyed. That is an exact-identifier bridge from one filed source to
another, and it is the first join in this repo that does not go through names.

**What the bridge changes, and what it does not.** An identifier join is
unambiguous by construction: it hits or it misses, and `f` from *ambiguity* goes
to zero. What replaces it is **coverage** — and that is a different failure mode,
not obviously a better one. A name join answers every question ambiguously; an
identifier join answers some questions perfectly and the rest not at all. This
measures both so the trade is visible rather than assumed.

Run: uv run python -u scripts/bridged_join.py
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ISIN_ZIP = Path("data/sources/gleif-isin/isin-lei-20260818.zip")
HOLDINGS = Path("data/sources/sec-edgar/commandagi-r2-2026-08-15/sec13f/"
                "holdings_p0.parquet")
OUT = Path("runs/bridged_join.json")
#: from the alignment finding: the name join's ambiguity rate
NAME_JOIN_F = 0.147


def load_isin_lei(path: Path) -> dict[str, str]:
    """CUSIP -> LEI, for US securities only.

    `isin[2:11]` is the CUSIP verbatim. Taking the substring rather than
    recomputing a check digit removes a whole class of arithmetic bug, and the
    check digit carries no information the mapping needs.
    """
    out: dict[str, str] = {}
    with zipfile.ZipFile(path) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(name) as fh:
            rdr = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
            header = next(rdr)
            li = header.index("LEI") if "LEI" in header else 0
            ii = header.index("ISIN") if "ISIN" in header else 1
            for row in rdr:
                if len(row) <= max(li, ii):
                    continue
                isin = row[ii].strip().upper()
                if len(isin) == 12 and isin.startswith("US"):
                    out.setdefault(isin[2:11], row[li].strip())
    return out


def main() -> None:
    print(f"loading {ISIN_ZIP} ...", flush=True)
    cusip_lei = load_isin_lei(ISIN_ZIP)
    print(f"  {len(cusip_lei):,} distinct US CUSIPs carry an LEI", flush=True)

    t = pq.read_table(HOLDINGS)
    cusips = {c.split(":")[-1].upper()
              for c in t.column("target_id").to_pylist()}
    print(f"  {len(cusips):,} distinct CUSIPs held across 13F", flush=True)

    hit = {c for c in cusips if c in cusip_lei}
    leis = {cusip_lei[c] for c in hit}
    print(f"\ncoverage: {len(hit):,}/{len(cusips):,} = "
          f"{len(hit)/len(cusips):.1%} of held securities bridge to an LEI")
    print(f"          {len(leis):,} distinct legal entities reached")

    # Ambiguity: does any CUSIP map to more than one LEI? An identifier join
    # should not, and checking rather than assuming is the point.
    multi = Counter()
    with zipfile.ZipFile(ISIN_ZIP) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(name) as fh:
            rdr = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
            header = next(rdr)
            li = header.index("LEI") if "LEI" in header else 0
            ii = header.index("ISIN") if "ISIN" in header else 1
            seen: dict[str, set[str]] = {}
            for row in rdr:
                if len(row) <= max(li, ii):
                    continue
                isin = row[ii].strip().upper()
                if len(isin) == 12 and isin.startswith("US"):
                    c = isin[2:11]
                    if c in cusips:
                        seen.setdefault(c, set()).add(row[li].strip())
    ambiguous = {c: v for c, v in seen.items() if len(v) > 1}
    f_bridge = len(ambiguous) / max(1, len(hit))
    print(f"\nambiguous bridged CUSIPs: {len(ambiguous):,}/{len(hit):,} = "
          f"{f_bridge:.4%}")
    print(f"the name join's ambiguity, for comparison:      {NAME_JOIN_F:.1%}")

    covered = len(hit) / len(cusips)
    print(f"\nSo the trade is explicit:")
    print(f"  NAME join       answers 100% of questions, {NAME_JOIN_F:.1%} of "
          f"them ambiguously")
    print(f"  IDENTIFIER join answers {covered:.1%} of questions, "
          f"{f_bridge:.2%} of them ambiguously,")
    print(f"                  and {1-covered:.1%} not at all")
    print("\nAmbiguity and coverage are different failure modes. An ambiguous "
          "answer\ncarries its alternatives and a caller can act on the "
          "mixture; a missing one\ncarries nothing. Which is better is a "
          "property of the caller, not of the join.")

    # --- the arithmetic that decides whether acquiring the bridge was worth it.
    #
    # A coverage gap escalates just as surely as an ambiguity does: a query the
    # bridge cannot answer has to go somewhere. So the identifier join alone has
    # f = 1 - coverage, which is far WORSE than the name join it was meant to
    # improve on. The policy that actually helps is bridge-then-name.
    M = 6.15e-04          # a model answer over the 41-token dependency
    O = 1.56e-11          # ours, from HANDOVER §3
    def adv(f):
        return M / (f * M + (1 - f) * O)

    f_name = NAME_JOIN_F
    f_bridge_only = 1 - covered
    f_combined = (1 - covered) * NAME_JOIN_F
    print("\nand the advantage each policy actually buys:")
    print(f"  {'name join alone':<34} f {f_name:>7.2%}  {adv(f_name):>7.1f}x")
    print(f"  {'identifier join alone':<34} f {f_bridge_only:>7.2%}  "
          f"{adv(f_bridge_only):>7.1f}x   <- WORSE: a coverage gap escalates too")
    print(f"  {'bridge, then names where it misses':<34} f {f_combined:>7.2%}  "
          f"{adv(f_combined):>7.1f}x")
    print(f"\nSo acquiring the identifier buys "
          f"{adv(f_combined)/adv(f_name):.2f}x, not the collapse to the "
          f"single-source 463x.\nThe cliff is not closed by the bridge — it is "
          f"CONVERTED from an ambiguity\nproblem into a coverage problem, and "
          f"coverage is the larger of the two.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"us_cusips_with_lei": len(cusip_lei), "cusips_held": len(cusips),
         "bridged": len(hit), "coverage": covered,
         "distinct_leis_reached": len(leis),
         "ambiguous_bridged": len(ambiguous), "f_bridge": f_bridge,
         "name_join_f": NAME_JOIN_F,
         "policies": {"name_only": {"f": f_name, "advantage": adv(f_name)},
                      "bridge_only": {"f": f_bridge_only,
                                      "advantage": adv(f_bridge_only)},
                      "bridge_then_name": {"f": f_combined,
                                           "advantage": adv(f_combined)}}},
        indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
