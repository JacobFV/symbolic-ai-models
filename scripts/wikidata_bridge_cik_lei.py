"""A file on disk *does* link a CIK to an LEI, and I published that none did.

`notes/findings/2026-08-18-the-advantage-is-a-property-of-provenance-463x-filed-against-18x-derived.md`
states that SEC and GLEIF share no identifier, that the only attribute both hold
is the name, and therefore that the 68x cliff at the first identity boundary is a
**data acquisition** problem. The first clause is false.

`data/sources/wikidata/.../idbridges_full_p0.parquet` is 69,679 `same-as` edges
out of the wikidata namespace, and its target namespaces are **lei 53,198**,
isin 9,936, **sec 3,660**, asx 2,846, ticker 39. Any wikidata entity carrying
both a `sec` and a `lei` edge *is* a CIK->LEI bridge, joined on identifiers at
both ends. I never looked, because I searched for the mechanism (a `same_as`
column) instead of for the name, and a file called `idbridges` was invisible to
that search.

**What this measures, and why it is not just a coverage number.** The obvious
composite — bridge where it reaches, names elsewhere — was priced in
`scripts/bridged_join.py` as `f = (1 - coverage) x f_name`, which assumes
coverage is **independent of ambiguity**. It is not obviously independent in
either direction: wikidata notability tracks corporate size, and large
corporations are exactly the ones with many GLEIF entities sharing a canonical
name. If the bridge preferentially reaches the ambiguous filers it removes more
than its share of `f`; if it reaches the easy ones it removes less. So this
measures the joint distribution rather than the product of the marginals.

And because the bridge and the name join answer the same question by different
routes, they can be checked against each other — the first cross-validation of
either in this repo.

Run: uv run python -u scripts/wikidata_bridge_cik_lei.py
"""

from __future__ import annotations

import collections
import json
import time
from pathlib import Path

import pyarrow.parquet as pq

from scripts.alignment_bounds import SEC, gleif_candidates
from symbolic_ai_tasks.company_key import (fit_strip_set, load_task,
                                           predict_fitted)
from symbolic_ai_tasks.cross_source_alignment import AlignmentResult

BRIDGE = Path("data/sources/wikidata/commandagi-r2-2026-08-15/wikidata/"
              "idbridges_full_p0.parquet")
OUT = Path("runs/wikidata_bridge_cik_lei.json")
#: the escalation price sheet, HANDOVER §3
MODEL_USD = 41.0 / 1e6 * 15.0
OURS_USD = 1.56e-11


def advantage(f: float) -> float:
    return MODEL_USD / (f * MODEL_USD + (1 - f) * OURS_USD)


def load_bridge() -> dict[str, str]:
    """CIK -> LEI, through any wikidata entity carrying both.

    Leading zeros are stripped at both ends: SEC writes `cik:0000796343` in one
    file and `cik:796343` in another, and a join on the padded form silently
    misses everything.
    """
    t = pq.read_table(BRIDGE)
    by_entity: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for s, g in zip(t.column("source_id").to_pylist(),
                    t.column("target_id").to_pylist()):
        parts = g.split(":")
        by_entity[s][parts[1]] = parts[-1]
    out: dict[str, str] = {}
    for v in by_entity.values():
        if "sec" in v and "lei" in v:
            out[v["sec"].lstrip("0")] = v["lei"]
    return out


def main() -> None:
    t0 = time.perf_counter()
    bridge = load_bridge()
    print(f"{len(bridge):,} CIK->LEI pairs through wikidata\n", flush=True)

    task = load_task(SEC)
    strip = fit_strip_set(task, task.ids)
    keys = predict_fitted(task, strip)
    index = gleif_candidates(strip, set(keys.values()))
    results = {f: AlignmentResult(filer=f, key=k, candidates=tuple(index[k]))
               for f, k in keys.items() if k in index}
    print(f"{len(task.ids):,} SEC filers, {len(results):,} matched to GLEIF by "
          f"name, in {time.perf_counter()-t0:.1f}s", flush=True)

    def cik_of(filer: str) -> str:
        return filer.split(":")[-1].lstrip("0")

    # --- the denominator that keeps this comparable to the 14.7% already
    # published. That number is 598/4,068 MATCHED filers, so coverage has to be
    # measured over matched filers too; the 15.3% over all 8,021 is a different
    # denominator and mixing them is this repo's oldest arithmetic trap.
    matched_bridged = {f for f in results if cik_of(f) in bridge}
    all_bridged = {f for f in task.ids if cik_of(f) in bridge}
    amb = {f for f, r in results.items() if r.ambiguous}
    print(f"\ncoverage has two denominators here, and the composite needs the "
          f"second:")
    print(f"  all SEC filers      {len(all_bridged):,}/{len(task.ids):,} = "
          f"{len(all_bridged)/len(task.ids):.1%}")
    print(f"  MATCHED filers      {len(matched_bridged):,}/{len(results):,} = "
          f"{len(matched_bridged)/len(results):.1%}   <- the one that composes")

    base_amb = len(amb) / len(results)
    amb_bridged = len(amb & matched_bridged) / max(1, len(matched_bridged))
    amb_unbridged = (len(amb - matched_bridged)
                     / max(1, len(results) - len(matched_bridged)))
    print(f"\nis coverage independent of ambiguity? (the composite assumed yes)")
    print(f"  ambiguity, all matched filers   {base_amb:>7.1%}  "
          f"({len(amb):,}/{len(results):,})")
    print(f"  ambiguity among BRIDGED         {amb_bridged:>7.1%}  "
          f"({len(amb & matched_bridged):,}/{len(matched_bridged):,})")
    print(f"  ambiguity among UNBRIDGED       {amb_unbridged:>7.1%}")
    enrich = amb_bridged / base_amb if base_amb else float("nan")
    print(f"  enrichment {enrich:.2f}x — the bridge reaches "
          f"{'AMBIGUOUS' if enrich > 1 else 'EASY'} filers "
          f"{'more' if enrich > 1 else 'less'} often than chance")

    # --- the honest composite: bridge first, names only where it misses.
    # Not (1-coverage) x f_name, which is the product of the marginals; the
    # numerator is the filers that are BOTH unbridged AND ambiguous.
    residual = amb - matched_bridged
    f_honest = len(residual) / len(results)
    f_indep = (1 - len(matched_bridged) / len(results)) * base_amb
    print(f"\nthe composite, two ways:")
    print(f"  {'name join alone':<38} f {base_amb:>7.2%}  "
          f"{advantage(base_amb):>7.1f}x")
    print(f"  {'independence estimate (what I priced)':<38} f {f_indep:>7.2%}  "
          f"{advantage(f_indep):>7.1f}x")
    print(f"  {'MEASURED joint':<38} f {f_honest:>7.2%}  "
          f"{advantage(f_honest):>7.1f}x   "
          f"({advantage(f_honest)/advantage(base_amb):.2f}x over names alone)")
    print(f"  the independence estimate is off by "
          f"{abs(f_honest-f_indep)/f_indep:.1%} of itself")

    # --- cross-validation. Two joins, same question, different routes.
    agree = disagree = 0
    agree_amb = disagree_amb = 0
    for f in sorted(matched_bridged):
        want = "kg:lei:" + bridge[cik_of(f)]
        got = {c.entity for c in results[f].candidates}
        hit = want in got
        agree += hit
        disagree += not hit
        if f in amb:
            agree_amb += hit
            disagree_amb += not hit
    tot = max(1, agree + disagree)
    tot_a = max(1, agree_amb + disagree_amb)
    print(f"\ncross-validation — is the bridge's LEI among the name join's "
          f"candidates?")
    print(f"  all bridged+matched   {agree:,}/{tot:,} = {agree/tot:.1%} agree")
    print(f"  the AMBIGUOUS subset  {agree_amb:,}/{tot_a:,} = "
          f"{agree_amb/tot_a:.1%} agree   <- where the bridge PICKS a candidate")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"bridge_pairs": len(bridge), "filers": len(task.ids),
         "matched": len(results), "bridged_all": len(all_bridged),
         "bridged_matched": len(matched_bridged),
         "coverage_all": len(all_bridged) / len(task.ids),
         "coverage_matched": len(matched_bridged) / len(results),
         "ambiguity_base": base_amb, "ambiguity_bridged": amb_bridged,
         "ambiguity_unbridged": amb_unbridged, "enrichment": enrich,
         "f_name": base_amb, "f_independence": f_indep, "f_joint": f_honest,
         "advantage_name": advantage(base_amb),
         "advantage_independence": advantage(f_indep),
         "advantage_joint": advantage(f_honest),
         "agreement": agree / tot, "agreement_ambiguous": agree_amb / tot_a,
         "n_agreement": tot, "n_agreement_ambiguous": tot_a}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
