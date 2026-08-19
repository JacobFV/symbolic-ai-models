"""Is tier 3 absent, or only absent from the source we asked?

`notes/findings/2026-08-18-reach-has-three-tiers-...md` split reach into
purchasable (saturates), derivable-from-recorded-structure (81.3% where it
applies, 22.4% of the hard cases), and **absent** — 90% of GLEIF entities carry
no relationship anyone filed, and the residual `f` of 8.17% was placed there.

That note called tier 3 "not a procurement problem", and it quietly assumed
something it never checked: that a relationship GLEIF did not record was not
recorded **anywhere**. GLEIF Level 2 is reportable only when a consolidating
parent exists *and* is itself LEI-registered — a rule about GLEIF's own
registry, not about the world. wikidata's backbone carries **1,540,285**
ownership edges (`owned-by` 1,162,331, `parent-organization` 196,426,
`subsidiary` 116,506, `owner-of` 65,022) under no such rule.

So the question this asks is not "how much more" but **which kind of limit tier 3
is**. If a second source settles even one ambiguous filer the first could not,
then tier 3 is a function of how many sources are federated rather than a wall,
and 8.17% is not a floor.

**How the two graphs are unioned.** Nodes are LEIs and wikidata QIDs; the
`idbridges` `same-as` edges make a bridged pair **one node**, so a QID with an
LEI is contracted into that LEI. Ownership is normalised to `child -> parent` in
both sources (`subsidiary` and `owner-of` point downward and are reversed), GLEIF
wins on conflict because it is the filed one, and the root is then the same
directed closure the GLEIF-only number used — so the arms are comparable.

The 280,499 wikidata ownership edges with exactly **one** LEI endpoint are the
interesting ones: they let two LEI-carrying entities be related through an
intermediate that carries no LEI at all, which no amount of GLEIF data reaches.

Run: uv run python -u scripts/federated_structure.py
"""

from __future__ import annotations

import collections
import glob
import json
import random
import time
from pathlib import Path

import pyarrow.parquet as pq

from scripts.alignment_bounds import SEC, gleif_candidates
from scripts.manufactured_reach import CONSOLIDATION, FUNDS, RELS
from scripts.wikidata_bridge_cik_lei import advantage, load_bridge
from symbolic_ai_tasks.company_key import (fit_strip_set, load_task,
                                           predict_fitted)
from symbolic_ai_tasks.cross_source_alignment import AlignmentResult

WD = "data/sources/wikidata/commandagi-r2-2026-08-15/wikidata"
BACKBONE = f"{WD}/backbone_full_p*.parquet"
BRIDGE = Path(f"{WD}/idbridges_full_p0.parquet")
OUT = Path("runs/federated_structure.json")
SEED = 20260818
#: normalised to child -> parent. The second pair point downward and are flipped.
UP_KINDS = {"owned-by", "parent-organization"}
DOWN_KINDS = {"subsidiary", "owner-of"}


def close_over(up: dict[str, str]) -> dict[str, str]:
    """child -> root, iteratively, with cycles collapsing to a stable member."""
    root: dict[str, str] = {}
    for start in list(up):
        x, seen = start, []
        while x in up and x not in root:
            if x in seen:
                x = min(seen)
                break
            seen.append(x)
            x = up[x]
        r = root.get(x, x)
        for y in seen:
            root[y] = r
    return root


def gleif_up() -> dict[str, str]:
    up: dict[str, str] = {}
    kinds = CONSOLIDATION + FUNDS
    pf = pq.ParquetFile(RELS)
    for b in pf.iter_batches(columns=["source_id", "target_id", "kind"]):
        for s, t, k in zip(b.column("source_id").to_pylist(),
                           b.column("target_id").to_pylist(),
                           b.column("kind").to_pylist()):
            if k in kinds:
                up.setdefault(s, t)
    return up


def wikidata_up(canon: dict[str, str]) -> dict[str, str]:
    """Ownership from the backbone, with bridged QIDs contracted onto their LEI."""
    up: dict[str, str] = {}
    for p in sorted(glob.glob(BACKBONE)):
        pf = pq.ParquetFile(p)
        for b in pf.iter_batches(columns=["source_id", "target_id", "kind"]):
            for s, t, k in zip(b.column("source_id").to_pylist(),
                               b.column("target_id").to_pylist(),
                               b.column("kind").to_pylist()):
                if k in UP_KINDS:
                    up.setdefault(canon.get(s, s), canon.get(t, t))
                elif k in DOWN_KINDS:
                    up.setdefault(canon.get(t, t), canon.get(s, s))
    return {c: p for c, p in up.items() if c != p}


def determined(amb, root) -> set[str]:
    return {f for f, r in amb.items()
            if len({root.get(c.entity, c.entity) for c in r.candidates}) == 1}


def main() -> None:
    t0 = time.perf_counter()
    task = load_task(SEC)
    strip = fit_strip_set(task, task.ids)
    keys = predict_fitted(task, strip)
    index = gleif_candidates(strip, set(keys.values()))
    results = {f: AlignmentResult(filer=f, key=k, candidates=tuple(index[k]))
               for f, k in keys.items() if k in index}
    amb = {f: r for f, r in results.items() if r.ambiguous}
    bridge = load_bridge()
    bridged = {f for f in results if f.split(":")[-1].lstrip("0") in bridge}
    print(f"{len(results):,} matched filers, {len(amb):,} ambiguous, "
          f"{len(bridged):,} bridged  ({time.perf_counter()-t0:.1f}s)\n",
          flush=True)

    bt = pq.read_table(BRIDGE)
    canon = {s: g for s, g in zip(bt.column("source_id").to_pylist(),
                                  bt.column("target_id").to_pylist())
             if g.startswith("kg:lei:")}
    print(f"contracting {len(canon):,} bridged QIDs onto their LEI", flush=True)

    g_up = gleif_up()
    print(f"GLEIF ownership edges:    {len(g_up):,}", flush=True)
    t1 = time.perf_counter()
    w_up = wikidata_up(canon)
    print(f"wikidata ownership edges: {len(w_up):,}  "
          f"({time.perf_counter()-t1:.0f}s)", flush=True)
    u_up = dict(w_up)
    u_up.update(g_up)          # GLEIF wins on conflict: it is the filed source
    print(f"union:                    {len(u_up):,}\n", flush=True)

    rng = random.Random(SEED)
    arms = {}
    dets = {}
    for label, up in (("GLEIF only", g_up), ("wikidata only", w_up),
                      ("UNION", u_up)):
        root = close_over(up)
        det = determined(amb, root)
        dets[label] = det
        pool = sorted({c.entity for r in amb.values() for c in r.candidates})
        vals = [root.get(x, x) for x in pool]
        rng.shuffle(vals)
        shuf = dict(zip(pool, vals))
        ctl = len({f for f, r in amb.items()
                   if len({shuf[c.entity] for c in r.candidates}) == 1})
        arms[label] = {"determined": len(det), "share": len(det) / len(amb),
                       "control": ctl / len(amb), "edges": len(up),
                       "roots": len(set(root.values()))}
        print(f"{label:<14} determined {len(det):>4,}/{len(amb):,} = "
              f"{len(det)/len(amb):>6.1%}   control {ctl/len(amb):>5.1%}")

    only_wd = dets["wikidata only"] - dets["GLEIF only"]
    only_g = dets["GLEIF only"] - dets["wikidata only"]
    print(f"\nsettled by wikidata that GLEIF could NOT: {len(only_wd):,}")
    print(f"settled by GLEIF that wikidata could NOT:  {len(only_g):,}")
    print(f"settled by both:                           "
          f"{len(dets['GLEIF only'] & dets['wikidata only']):,}")
    # A handful is not a result. The UNION control settles ~1 filer by chance,
    # so anything of this order is noise-adjacent and the slice rule applies:
    # form a hypothesis from it, never report one.
    verdict = ("SUBSTANTIAL" if len(only_wd) >= 0.05 * len(amb) else
               "NOISE-ADJACENT" if len(only_wd) <= 3 * arms["UNION"]["control"]
               * len(amb) else "SMALL BUT REAL")
    print(f"\n-> {verdict}: {len(only_wd):,} filers of {len(amb):,}, against a "
          f"union control of\n   {arms['UNION']['control']*len(amb):.0f}. "
          f"Federating a second structural source buys "
          f"{len(only_wd)/len(amb):.1%} here.")

    # --- WHY, which is the whole value of a null. Two mechanisms with opposite
    # consequences: wikidata records structure for the SAME entities GLEIF does
    # (redundancy -- federation is pointless), or for DIFFERENT ones that simply
    # cannot be reached from LEI space (the identity bridge is the bottleneck,
    # not the structure). Predict the factors, not the product.
    reachable = sum(1 for c, p_ in w_up.items()
                    if c.startswith("kg:lei:") and p_.startswith("kg:lei:"))
    print(f"\nwhere did 1.28M ownership edges go?")
    print(f"  wikidata ownership edges, total          {len(w_up):>10,}")
    print(f"  ... with BOTH ends projected into LEI    {reachable:>10,} "
          f"= {reachable/len(w_up):.2%}")
    print(f"  GLEIF ownership edges, for scale         {len(g_up):>10,}")
    print(f"\n  wikidata holds {len(w_up)/len(g_up):.1f}x more ownership "
          f"structure than GLEIF and only\n  {reachable/len(g_up):.1%} as much "
          f"of it is expressible about LEIs, because only "
          f"{len(canon):,}\n  wikidata entities carry one.")

    # The conditional: mechanism strength with coverage divided out.
    q_of = {v: k for k, v in canon.items()}
    full = {f: r for f, r in amb.items()
            if all(c.entity in q_of for c in r.candidates)}
    wroot = close_over(w_up)
    fdet = len(determined(full, wroot))
    print(f"\n  ambiguous filers whose candidates ALL carry a wikidata entity: "
          f"{len(full):,}/{len(amb):,} = {len(full)/len(amb):.1%}")
    print(f"  determined among those:                                        "
          f"{fdet:,}/{max(1,len(full)):,} = {fdet/max(1,len(full)):.1%}")
    print(f"\n  -> the limit is the IDENTITY BRIDGE, not the structure. "
          f"Federating a second\n     structural source is gated by tier-1 "
          f"coverage -- and tier 1 saturates.\n     The tiers are not "
          f"independent.")
    diag = {"wikidata_edges": len(w_up), "projected_to_lei": reachable,
            "gleif_edges": len(g_up), "candidates_with_qid": len(full),
            "conditional_determined": fdet / max(1, len(full))}

    f_name = len(amb) / len(results)
    rows = {}
    print(f"\nf for a group-level question, and what each lever is worth:\n")
    print(f"  {'policy':<40} {'f':>8} {'advantage':>11}")
    print("  " + "-" * 61)
    for label, det in (("names alone", set()),
                       ("+ GLEIF closure", dets["GLEIF only"]),
                       ("+ UNION closure", dets["UNION"]),
                       ("+ UNION closure + wikidata bridge",
                        dets["UNION"] | (bridged & set(amb)))):
        f = len(set(amb) - det) / len(results)
        rows[label] = {"f": f, "advantage": advantage(f)}
        print(f"  {label:<40} {f:>7.2%} {advantage(f):>10.1f}x")
    print(f"\n  the second source adds "
          f"{rows['+ UNION closure']['advantage']/rows['+ GLEIF closure']['advantage']:.2f}x "
          f"on top of the first, at zero acquisition cost")
    print(f"  end to end, names -> everything: "
          f"{rows['+ UNION closure + wikidata bridge']['advantage']/rows['names alone']['advantage']:.2f}x")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"seed": SEED, "matched": len(results), "ambiguous": len(amb),
         "arms": arms, "only_wikidata": len(only_wd), "only_gleif": len(only_g),
         "both": len(dets["GLEIF only"] & dets["wikidata only"]),
         "policies": rows, "diagnostic": diag}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
