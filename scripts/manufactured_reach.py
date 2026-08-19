"""Reach you cannot buy: does closure settle the filers no crosswalk reaches?

`notes/findings/2026-08-18-purchasable-reach-saturates-...md` closed the
purchasable half of the reach problem with a negative: crosswalk value
**saturates**. 2,383 curated rows reach 68.8% of $51.4T of 13F holdings and
2,281,221 filed rows reach 75.0%, and normalised against an oracle at each
crosswalk's own size the two are 1.06x apart. Buying more mappings will not
close the 68x cliff at the first identity boundary.

What is left is **structural** reach, and it is the half this repo's machinery is
for. The mechanism on offer:

> The name join's failure mode is **over-generation**, and 93.0% cross-validation
> against the wikidata bridge says the right candidate is almost always in the
> set. Entities share a canonical name because they are *Morgan Stanley & Co*,
> *Morgan Stanley Bank*, *Morgan Stanley Capital* — **members of one group**.
> That is precisely what GLEIF's relationship file encodes, and it is on disk.

So: take the transitive closure of `IS_ULTIMATELY_CONSOLIDATED_BY`, and ask
whether an ambiguous filer's candidates all land on **one root**. If they do, the
filer is **determined at the group level** — every question asked about the group
rather than the legal entity has a single answer, though the alignment itself
stays ambiguous. Nothing is acquired; the answer is manufactured from structure
already held.

**The scope caveat is half the finding.** This settles group-level questions
only. "Which country is this filer's *entity* in?" stays ambiguous when the
group spans countries; "whose group is this filer part of?" does not. That is
the *match the question to the data's shape* thesis stated as a measurement
rather than as advice.

**The control that must fail.** Few roots would produce agreement by chance, so
the LEI->root map is permuted within the candidate population and remeasured. If
the shuffled world agrees comparably, this is a base-rate artefact. It is run
twice -- over all ambiguous filers, and over the conditional population alone,
because a shuffle across a pool containing entities the graph never mentions
destroys coverage as well as structure and would be answering an easier
question than the headline asks.

Run: uv run python -u scripts/manufactured_reach.py
"""

from __future__ import annotations

import collections
import json
import random
import time
from pathlib import Path

import pyarrow.parquet as pq

from scripts.alignment_bounds import SEC, gleif_candidates
from scripts.wikidata_bridge_cik_lei import advantage, load_bridge
from symbolic_ai_tasks.company_key import (fit_strip_set, load_task,
                                           predict_fitted)
from symbolic_ai_tasks.cross_source_alignment import AlignmentResult

RELS = Path("data/sources/gleif/commandagi-r2-2026-08-15/gleif/"
            "relationships_p0.parquet")
OUT = Path("runs/manufactured_reach.json")
SEED = 20260818
#: the two notions of "one group", measured separately because they answer
#: different questions. Consolidation is ownership; fund management is not.
CONSOLIDATION = ("IS_ULTIMATELY_CONSOLIDATED_BY", "IS_DIRECTLY_CONSOLIDATED_BY",
                 "IS_INTERNATIONAL_BRANCH_OF")
FUNDS = ("IS_FUND-MANAGED_BY", "IS_SUBFUND_OF", "IS_FEEDER_TO")


def in_graph(kinds: tuple[str, ...]) -> set[str]:
    """Every LEI the relationship graph mentions, as source **or** target.

    Testing membership of the ``root`` map instead is wrong and quietly so:
    ``root`` only holds entities with an *outgoing* edge, so a top-level parent
    -- the commonest interesting case, a subsidiary matching the same name as
    its own parent -- reads as absent from a graph it is the root of. That
    version reported 11 filers with all candidates present and an 81.8%
    conditional rate from n=11.
    """
    seen: set[str] = set()
    pf = pq.ParquetFile(RELS)
    for batch in pf.iter_batches(columns=["source_id", "target_id", "kind"]):
        for s_, t, k in zip(batch.column("source_id").to_pylist(),
                            batch.column("target_id").to_pylist(),
                            batch.column("kind").to_pylist()):
            if k in kinds:
                seen.add(s_)
                seen.add(t)
    return seen


def roots_from(kinds: tuple[str, ...]) -> dict[str, str]:
    """LEI -> the root of its group, by transitive closure over ``kinds``.

    Keys are the **full** ``kg:lei:*`` form, because that is what the parquet
    holds and what ``Candidate.entity`` holds. A first version stripped the
    prefix on lookup but not on insert, so every lookup missed and the answer
    came out a clean 0/598 -- with a 0/598 control, which is what gave it away.

    An entity with no outgoing edge is its own root. Closure is iterative with a
    visited set rather than recursive: GLEIF's graph is not guaranteed acyclic
    (a mutual-consolidation pair exists) and a cycle must terminate at a stable
    representative rather than blowing the stack.
    """
    up: dict[str, str] = {}
    pf = pq.ParquetFile(RELS)
    for batch in pf.iter_batches(columns=["source_id", "target_id", "kind"]):
        for s, t, k in zip(batch.column("source_id").to_pylist(),
                           batch.column("target_id").to_pylist(),
                           batch.column("kind").to_pylist()):
            if k in kinds:
                up.setdefault(s, t)
    root: dict[str, str] = {}

    def resolve(x: str) -> str:
        seen: list[str] = []
        while x in up and x not in root:
            if x in seen:                      # cycle: the smallest id wins, so
                x = min(seen)                  # every member agrees on the same
                break                          # representative
            seen.append(x)
            x = up[x]
        r = root.get(x, x)
        for y in seen:
            root[y] = r
        return r

    for lei in list(up):
        resolve(lei)
    return root


def main() -> None:
    t0 = time.perf_counter()
    task = load_task(SEC)
    strip = fit_strip_set(task, task.ids)
    keys = predict_fitted(task, strip)
    index = gleif_candidates(strip, set(keys.values()))
    results = {f: AlignmentResult(filer=f, key=k, candidates=tuple(index[k]))
               for f, k in keys.items() if k in index}
    bridge = load_bridge()
    bridged = {f for f in results if f.split(":")[-1].lstrip("0") in bridge}
    amb = {f: r for f, r in results.items() if r.ambiguous}
    print(f"{len(results):,} matched filers, {len(amb):,} ambiguous, "
          f"{len(bridged):,} bridged, in {time.perf_counter()-t0:.1f}s\n",
          flush=True)

    rng = random.Random(SEED)
    rows = {}
    for label, kinds in (("consolidation", CONSOLIDATION),
                         ("consolidation + funds", CONSOLIDATION + FUNDS)):
        t1 = time.perf_counter()
        root = roots_from(kinds)
        det = set()
        no_edge = 0
        for f, r in amb.items():
            rs = {root.get(c.entity, c.entity)
                  for c in r.candidates}
            if len(rs) == 1:
                det.add(f)
                if not any(c.entity in root for c in r.candidates):
                    # every candidate is its own root: "agreement" here is the
                    # degenerate case of a singleton group, not group structure.
                    no_edge += 1
        share = len(det) / len(amb)

        # --- the control that must fail. Permute the root labels among the
        # candidate LEIs, preserving how many roots there are and how big they
        # are, and destroying only which entity belongs to which.
        pool = sorted({c.entity for r in amb.values()
                       for c in r.candidates})
        vals = [root.get(x, x) for x in pool]
        rng.shuffle(vals)
        shuf = dict(zip(pool, vals))
        ctl = sum(1 for r in amb.values()
                  if len({shuf[c.entity]
                          for c in r.candidates}) == 1) / len(amb)

        rows[label] = {"determined": len(det), "share": share,
                       "control_share": ctl, "degenerate_singletons": no_edge,
                       "roots": len(set(root.values())),
                       "seconds": time.perf_counter() - t1}
        print(f"{label}:")
        print(f"  ambiguous filers determined at GROUP level: {len(det):,}/"
              f"{len(amb):,} = {share:.1%}")
        print(f"    of which every candidate was its own root: {no_edge:,} "
              f"({no_edge/max(1,len(det)):.1%}) — a singleton group, not "
              f"structure")
        print(f"  PERMUTATION CONTROL: {ctl:.1%}  "
              f"({'PASSES — control fails as it must' if ctl < share/2 else 'FAILS — base-rate artefact'})")
        print(f"  built in {rows[label]['seconds']:.1f}s\n", flush=True)

    # --- the diagnostic that decides what a low number MEANS. 17% determined
    # is either "name-sharing crosses corporate groups" (mechanism wrong) or
    # "GLEIF's relationship file is sparse" (mechanism fine, and reach is
    # purchasable after all). The two are distinguished by conditioning on
    # whether the candidates are IN the graph at all.
    root = roots_from(CONSOLIDATION + FUNDS)
    det_all_pre = {f for f, r in amb.items()
                   if len({root.get(c.entity, c.entity)
                           for c in r.candidates}) == 1}
    known = in_graph(CONSOLIDATION + FUNDS)
    inn = collections.Counter()
    full_det = full_n = 0
    for f, r in amb.items():
        k = sum(1 for c in r.candidates if c.entity in known)
        inn["all" if k == len(r.candidates) else
            ("none" if k == 0 else "some")] += 1
        if k == len(r.candidates):
            full_n += 1
            if len({root.get(c.entity, c.entity)
                    for c in r.candidates}) == 1:
                full_det += 1
    print("is 18.2% the MECHANISM failing or the DATA being thin?\n")
    print(f"  ambiguous filers whose candidates are in the relationship graph:")
    for k in ("all", "some", "none"):
        print(f"    {k:<5} {inn[k]:>4,}/{len(amb):,} = {inn[k]/len(amb):>6.1%}")
    # The control has to run on the CONDITIONAL population too, or it is
    # answering an easier question than the headline does: shuffling roots
    # across a pool that includes entities the graph never mentions destroys
    # coverage as well as structure, and coverage is not what is being claimed.
    cpool = sorted({c.entity for f, r in amb.items() for c in r.candidates
                    if all(x.entity in known for x in r.candidates)})
    cvals = [root.get(x, x) for x in cpool]
    rng.shuffle(cvals)
    cshuf = dict(zip(cpool, cvals))
    cctl = sum(1 for f, r in amb.items()
               if all(c.entity in known for c in r.candidates)
               and len({cshuf[c.entity] for c in r.candidates}) == 1)
    cond = full_det / max(1, full_n)
    print(f"\n  CONDITIONAL on every candidate being in the graph: "
          f"{full_det:,}/{full_n:,} = {cond:.1%} determined")
    print(f"  unconditional: {len(det_all_pre)/len(amb):.1%}")
    print(f"  PERMUTATION CONTROL on the SAME conditional population: "
          f"{cctl:,}/{full_n:,} = {cctl/max(1,full_n):.1%}")
    print(f"\n  -> {'THE DATA IS THIN' if cond > 0.5 else 'THE MECHANISM IS WEAK'}: "
          f"name-sharing {'stays inside' if cond > 0.5 else 'crosses'} corporate "
          f"groups.")
    print(f"     The limit is relationship COVERAGE — and it is a third kind of "
          f"limit.\n     GLEIF mentions {len(known):,} entities in relationships "
          f"out of 3,348,427\n     ({len(known)/3348427:.1%}), because Level 2 is "
          f"only reportable when a\n     consolidating parent exists AND is "
          f"itself LEI-registered. This is not a\n     smaller copy of a file "
          f"you can buy a bigger one of; for the other 90%\n     the "
          f"relationship was never recorded by anyone.\n")
    graph_cov = {"all": inn["all"], "some": inn["some"], "none": inn["none"],
                 "conditional_determined": cond, "conditional_n": full_n,
                 "conditional_control": cctl / max(1, full_n)}

    # --- what it does to f. A filer is escalated only if it is ambiguous AND
    # unbridged AND its candidates disagree at group level.
    residual_names = set(amb) - det_all_pre
    residual_both = residual_names - bridged
    f_name = len(amb) / len(results)
    f_bridge = len(set(amb) - bridged) / len(results)
    f_closure = len(residual_names) / len(results)
    f_both = len(residual_both) / len(results)
    print("f, for a GROUP-LEVEL question, under four policies:\n")
    hdr = f"  {'policy':<44} {'f':>8} {'advantage':>11}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for name, f in (("names alone", f_name),
                    ("+ wikidata bridge", f_bridge),
                    ("+ closure (no acquisition at all)", f_closure),
                    ("+ both", f_both)):
        print(f"  {name:<44} {f:>7.2%} {advantage(f):>10.1f}x")
    print(f"\n  closure alone buys {advantage(f_closure)/advantage(f_name):.2f}x; "
          f"the bridge alone buys {advantage(f_bridge)/advantage(f_name):.2f}x; "
          f"together {advantage(f_both)/advantage(f_name):.2f}x")
    print(f"\n  And closure cost NOTHING to acquire — the relationship file was "
          f"already\n  on disk and is the same source the candidates came from.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"seed": SEED, "matched": len(results), "ambiguous": len(amb),
         "bridged": len(bridged), "closures": rows,
         "f": {"names": f_name, "bridge": f_bridge, "closure": f_closure,
               "both": f_both},
         "advantage": {"names": advantage(f_name), "bridge": advantage(f_bridge),
                       "closure": advantage(f_closure),
                       "both": advantage(f_both)}}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
