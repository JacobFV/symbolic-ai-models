"""What a 55%-correct world does to an exact reasoner running over it.

`CLAUDE.md` states the rule this script exists to apply:

> Cost is charged to the **system**: if a reasoner only works because something
> upstream produced a graph, that upstream component is in the ledger whether or
> not it exists yet.

Both arrows are now measured, separately. Extraction reaches ~62% of a 0.99
ceiling (`the-first-arrow-is-cheap-and-bad`, `a-zero-shot-registry-beats-...`).
Reasoning maintains answers at 37x–13,987x
(`the-certificate-is-worth-nothing-per-quarter-...`). **Nobody has asked what the
second does when it runs on what the first produces**, and the answer is not
"62%": a query that reads many extracted facts inherits many extraction errors,
and this repo has a measured precedent for the shape — a composition amplified
its inputs' errors roughly 13x on the route network.

Two worlds over the same 5,000 OpenAlex works:

    REFERENCE   built from OpenAlex's own institution labels — the anchor.
    EXTRACTED   built by v4, the ZERO-SHOT registry extractor.

v4 is used deliberately. It needs no training split, so the extracted world has
no leakage anywhere, and it is what a deployed system would actually produce on
a corpus it has never seen. Using a rung that memorises part of the corpus would
price a system that cannot exist.

Then four query classes of increasing dependency, and the question is whether
error *amplifies*, *survives*, or *cancels*.

Run: SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \\
     uv run python -u scripts/two_arrows_end_to_end.py
"""

from __future__ import annotations

import json
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from scripts.first_arrow_gazetteer import ROR, v4
from scripts.first_arrow_geo import GeoGazetteer
from scripts.first_arrow_prose import load, norm, score

OUT = Path("runs/two_arrows_end_to_end.json")
SEED = 20260818
N_QUERIES = 2000
USD_PER_CORE_HOUR = 0.02
FRONTIER_USD_PER_MTOK = 15.0


def v4_recall(gz, raw: str) -> set[str]:
    """v4 with the abstention taken out: every candidate, never a refusal.

    The other end of the operating range. v4 emits a component's institution
    only when the registry names exactly one; this emits all of them. At the
    fact level that is strictly worse — it is guessing where the system knows
    least, which lost three times today. The question is whether a *world* built
    this way answers aggregate queries better, because a query cannot union its
    way to a collaborator that was never extracted anywhere.
    """
    out: set[str] = set()
    for cands in gz.propose(raw):
        out |= cands
    return out


def build_worlds(works, gz, extract: Callable[[Any, str], set[str]] = v4):
    """(reference, extracted): work id -> the set of institutions it involves.

    Plus both inverted indexes, because half the query classes are keyed on an
    institution rather than on a work — and a query keyed on an *extracted*
    entity is where an error at the entry point invalidates everything after it.
    """
    ref: dict[str, set[str]] = {}
    ext: dict[str, set[str]] = {}
    t0 = time.perf_counter_ns()
    for w in works:
        r: set[str] = set()
        e: set[str] = set()
        for a in w["affiliations"]:
            r |= set(a["rors"])
            e |= extract(gz, a["raw"])
        ref[w["id"]] = r
        ext[w["id"]] = e
    extract_ns = time.perf_counter_ns() - t0

    def invert(world):
        out: dict[str, set[str]] = defaultdict(set)
        for wid, insts in world.items():
            for i in insts:
                out[i].add(wid)
        return out

    return ref, ext, invert(ref), invert(ext), extract_ns


def collaborators(world, inv, inst: str) -> set[str]:
    """Every institution appearing on a work this one appears on."""
    out: set[str] = set()
    for wid in inv.get(inst, ()):
        out |= world[wid]
    out.discard(inst)
    return out


def main() -> None:
    rng = random.Random(SEED)
    print(f"loading {ROR} ...", flush=True)
    gz = GeoGazetteer(ROR)
    works = load()
    print(f"  {len(works):,} works, {gz.n_orgs:,} organizations", flush=True)

    ref, ext, inv_ref, inv_ext, extract_ns = build_worlds(works, gz)
    print(f"\nbuilt both worlds in {extract_ns/1e9:.1f}s "
          f"({extract_ns/len(works):,.0f} ns/work)", flush=True)

    # --- fact level, for the amplification denominator
    fact = score([(ext[w["id"]], ref[w["id"]]) for w in works])
    print(f"\nfact level (institutions_of a WORK, depth 1): "
          f"F1 {fact['f1']:.3f}, Jaccard {fact['jaccard']:.3f}, "
          f"exact {fact['exact_set_match']:.1%}")

    rows: dict[str, Any] = {"institutions_of(work)": fact}

    # --- queries keyed on a work, but reading more than one
    all_ids = [w["id"] for w in works]
    real_insts = sorted({i for v in ref.values() for i in v})
    print(f"  reference world: {len(real_insts):,} distinct institutions, "
          f"{sum(len(v) for v in ref.values()):,} facts; "
          f"extracted: {len({i for v in ext.values() for i in v}):,} "
          f"institutions, {sum(len(v) for v in ext.values()):,} facts")

    # --- collaborators: keyed on an institution, unions many works
    sample = rng.sample(real_insts, min(N_QUERIES, len(real_insts)))
    pairs = [(collaborators(ext, inv_ext, i), collaborators(ref, inv_ref, i))
             for i in sample]
    pairs = [(p, t) for p, t in pairs if t]
    rows["collaborators(institution)"] = score(pairs)

    # --- works_at: keyed on an institution, depends on every extraction
    pairs = [(inv_ext.get(i, set()), inv_ref.get(i, set())) for i in sample]
    pairs = [(p, t) for p, t in pairs if t]
    rows["works_at(institution)"] = score(pairs)

    print()
    hdr = (f"{'query class':<30} {'n':>6} {'F1':>7} {'Jaccard':>9} "
           f"{'exact':>8} {'prec':>7} {'rec':>7} {'amplif':>8}")
    print(hdr)
    print("-" * len(hdr))
    for name, r in rows.items():
        amp = ((1 - r["jaccard"]) / (1 - fact["jaccard"])
               if fact["jaccard"] < 1 else 0.0)
        r["amplification"] = amp
        print(f"{name:<30} {r['n']:>6,} {r['f1']:>7.3f} {r['jaccard']:>9.3f} "
              f"{r['exact_set_match']:>7.1%} {r['precision']:>6.1%} "
              f"{r['recall']:>6.1%} {amp:>7.2f}x")

    # --- a COUNT, where errors cannot cancel into a set
    counts = []
    for i in sample:
        t = len(inv_ref.get(i, set()))
        if not t:
            continue
        counts.append(abs(len(inv_ext.get(i, set())) - t) / t)
    rel = statistics.median(counts)
    mean_rel = statistics.mean(counts)
    print(f"\ncount query — works_at_count(institution): median relative error "
          f"{rel:.1%}, mean {mean_rel:.1%} over {len(counts):,} institutions")
    rows["works_at_count(institution)"] = {"median_rel_error": rel,
                                           "mean_rel_error": mean_rel,
                                           "n": len(counts)}

    # --- the ledger
    n_facts = sum(len(v) for v in ref.values())
    sym_usd = extract_ns * USD_PER_CORE_HOUR / 3600 / 1e9
    corpus_tok = sum(len(a["raw"]) for w in works
                     for a in w["affiliations"]) / 4.0
    llm_usd = corpus_tok / 1e6 * FRONTIER_USD_PER_MTOK
    print(f"\nthe ledger for building this world once")
    print(f"  symbolic  {extract_ns/1e9:>8.1f}s  ${sym_usd:.3e}   "
          f"quality {fact['f1']:.3f} F1")
    print(f"  model     {corpus_tok:>8,.0f} tok ${llm_usd:.3e}   "
          f"(input only, perfect extraction assumed — a lower bound)")
    print(f"  ratio     {llm_usd/max(1e-30, sym_usd):>8,.0f}x on price, and the "
          f"symbolic world is {fact['f1']:.0%} right")

    print(f"\nwhat this says about every advantage in HANDOVER 3, 3b and 3c: "
          f"they are\nquoted over a world someone else built. Built by us at "
          f"{llm_usd/max(1e-30,sym_usd):,.0f}x less, the world is "
          f"{fact['f1']:.1%} F1 at the fact level and\nthe queries over it land "
          f"where the table above says.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "seed": SEED, "works": len(works), "rows": rows,
        "extract_ns": extract_ns, "symbolic_usd": sym_usd,
        "llm_usd_lower_bound": llm_usd,
        "anchor": "agreement with the world built from OpenAlex's own labels",
    }, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
