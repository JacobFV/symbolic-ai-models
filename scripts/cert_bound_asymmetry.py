"""An optimum is two claims, and only one of them is cheap to keep.

`cert_dependency_size.py` measured the ceiling on a maintenance certificate:

    advantage <= 1 / P_hit,   P_hit ~ r x keys_per_update / total_keys

so the whole mechanism is governed by ``r``, the size of the dependency. The
clingo cover answer sits at r=12 and P_hit 2.71%, a ceiling of 37x — the worst
of the four query classes, purely because it reads the most.

But the recorded read set is not the dependency of the *answer*; it is the
dependency of the *computation*, and for an optimisation those differ by the
structure of the problem. "The optimal cover has size k" is two claims:

    k is achievable    — a WITNESS of k edges. Monotone: more holdings can only
                         make covering easier, so this survives every addition
                         to the corpus and dies only if a witness edge is
                         deleted.
    k is optimal       — no cover of size k-1 exists. A NEGATIVE claim resting
                         on the absence of a better option, which is why the
                         recording mechanism correctly read every item's whole
                         holder set. A single new edge anywhere in them can
                         destroy it.

That asymmetry is the reason a solver's unsat core is **not** a sound stability
certificate for the lower half: the core proves infeasibility under the facts
present, and infeasibility is not preserved when facts are added.

13F grows: 411,122 positions opened against 333,014 closed. So the prediction is
that the two halves of one answer differ by two orders of magnitude in what they
cost to maintain, and that the cheap half is the one nobody would have separated
out.

CONTROL: the optimality certificate must reproduce the 2.71% / 37.3x already on
disk, or this is not measuring the same thing as the experiment it extends.

Run: uv run python -u scripts/cert_bound_asymmetry.py
"""

from __future__ import annotations

import json
import os
import random
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Hashable, Mapping

from scripts.cert_freshness_13f import filing_updates
from scripts.cert_maintenance_13f import (
    NEW_FILE, OLD_FILE, SEED, USD_PER_CORE_HOUR, load_store)

#: Swap the two snapshots, so the same filed bytes read as a SHRINKING corpus
#: instead of a growing one. 13F opened 411,122 edges against 333,014 closed, so
#: the witness -- which is monotone under additions and dies only on deletion --
#: had the easier direction. Reversing is the falsifier for that, and it needs
#: no new data and nothing injected.
REVERSE = bool(os.environ.get("SYMBOLIC_AI_REVERSE_SNAPSHOTS"))
OUT = Path("runs/cert_bound_asymmetry_reversed.json" if REVERSE
           else "runs/cert_bound_asymmetry.json")
N_QUERIES = 300
COVER_SIZE = 12


def optimal_cover(store: Mapping, secs: tuple[str, ...]
                  ) -> tuple[int, frozenset[Hashable], frozenset[Hashable]]:
    """Optimal cover size, its witness edges, and the facts optimality rests on.

    Returns ``(k, witness, optimality_read)``:

    * ``witness`` — one ``("holds", filer, sec)`` edge per item, from the chosen
      filers. These are the facts that make ``<= k`` true.
    * ``optimality_read`` — the holder-set key of every item. These are the facts
      that make ``>= k`` true, and there is no smaller sound set: any filer
      anywhere in them could have been the one that made ``k-1`` reachable.
    """
    import clingo
    lines, universe = [], []
    holders: dict[int, frozenset[str]] = {}
    for i, s in enumerate(secs):
        hs = store.get(("holders", s), frozenset())
        if not hs:
            continue
        holders[i] = hs
        universe.append(i)
        for f in hs:
            lines.append(f'covers("{f}",{i}).')
    optimality = frozenset(("holders", s) for s in secs)
    if not universe:
        return 0, frozenset(), optimality
    lines.append("filer(F) :- covers(F,_).")
    lines.append("{ pick(F) } :- filer(F).")
    lines.append("covered(I) :- pick(F), covers(F,I).")
    lines.append(":- item(I), not covered(I).")
    lines += [f"item({i})." for i in universe]
    lines.append("#minimize { 1,F : pick(F) }.")
    ctl = clingo.Control()
    ctl.add("base", [], "\n".join(lines))
    ctl.ground([("base", [])])
    picked: list[str] = []
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            picked = [a.arguments[0].string for a in model.symbols(shown=True)
                      if a.name == "pick"]
    # The witness: for each item, one chosen filer that covers it. Greedy pick
    # of the first is fine -- any one of them is a proof that the item is
    # covered, and a smaller witness is a stronger certificate.
    witness = set()
    for i in universe:
        for f in picked:
            if f in holders[i]:
                witness.add(("holds", f, secs[i]))
                break
    return len(picked), frozenset(witness), optimality


def main() -> None:
    rng = random.Random(SEED)
    print("loading two filed snapshots ...", flush=True)
    old, new = load_store(OLD_FILE), load_store(NEW_FILE)
    if REVERSE:
        old, new = new, old
        print("  REVERSED: the later snapshot is 'old', so the corpus shrinks",
              flush=True)
    updates = filing_updates(old, new)
    total_keys = len(set(old) | set(new))

    # The edge-level view of the same delta, split by direction. This is what
    # the witness certificate is checked against and it is the only place the
    # asymmetry can show up.
    empty: frozenset[str] = frozenset()
    added: set[Hashable] = set()
    removed: set[Hashable] = set()
    per_filing_removed: list[frozenset[Hashable]] = []
    per_filing_added: list[frozenset[Hashable]] = []
    filers = {k[1] for k in old if k[0] == "portfolio"}
    filers |= {k[1] for k in new if k[0] == "portfolio"}
    for f in sorted(filers):
        a = old.get(("portfolio", f), empty)
        b = new.get(("portfolio", f), empty)
        gone = frozenset(("holds", f, s) for s in a - b)
        came = frozenset(("holds", f, s) for s in b - a)
        if not gone and not came:
            continue
        removed |= gone
        added |= came
        per_filing_removed.append(gone)
        per_filing_added.append(came)
    total_edges = sum(len(v) for k, v in old.items() if k[0] == "portfolio")
    print(f"  {len(updates):,} filings; {len(added):,} edges opened, "
          f"{len(removed):,} closed, of {total_edges:,}", flush=True)
    print(f"  per filing: {len(added)/len(updates):.1f} opened, "
          f"{len(removed)/len(updates):.1f} closed", flush=True)

    secs = sorted(k[1] for k in old if k[0] == "holders")
    print(f"\nsolving {N_QUERIES} covers of {COVER_SIZE} securities ...",
          flush=True)
    t0 = time.perf_counter()
    answers, queries = [], []
    for _ in range(N_QUERIES):
        q = tuple(rng.sample(secs, COVER_SIZE))
        queries.append(q)
        answers.append(optimal_cover(old, q))
    compute_s = time.perf_counter() - t0
    compute_ns = compute_s / N_QUERIES * 1e9
    print(f"  {compute_s:.1f}s, {compute_ns/1e6:.2f} ms/answer; "
          f"witness {sum(len(w) for _, w, _ in answers)/N_QUERIES:.1f} edges, "
          f"optimality read {sum(len(o) for _, _, o in answers)/N_QUERIES:.1f} "
          f"keys", flush=True)

    # Inverted indexes: fact key -> the answers whose certificate reads it.
    idx_witness: dict[Hashable, list[int]] = defaultdict(list)
    idx_opt: dict[Hashable, list[int]] = defaultdict(list)
    for i, (_, w, o) in enumerate(answers):
        for k in w:
            idx_witness[k].append(i)
        for k in o:
            idx_opt[k].append(i)

    def replay(index, per_filing) -> dict[str, Any]:
        hits = 0
        t = time.perf_counter_ns()
        for keys in per_filing:
            seen: set[int] = set()
            for k in keys:
                seen.update(index.get(k, ()))
            hits += len(seen)
        check_ns = time.perf_counter_ns() - t
        n_upd = len(per_filing)
        p_hit = hits / (n_upd * N_QUERIES) if n_upd else 0.0
        ours = check_ns + hits * compute_ns
        theirs = N_QUERIES * n_upd * compute_ns
        return {"updates": n_upd, "invalidations": hits, "p_hit": p_hit,
                "advantage": theirs / ours if ours else 0.0,
                "ceiling_1_over_p": 1 / p_hit if p_hit else float("inf"),
                "ours_usd": ours * USD_PER_CORE_HOUR / 3600 / 1e9,
                "theirs_usd_extrapolated": (theirs * USD_PER_CORE_HOUR
                                            / 3600 / 1e9)}

    per_filing_all = [a | b for a, b in zip(per_filing_added,
                                            per_filing_removed)]
    rows = {
        # The control: adjacency keys, both directions. Must reproduce 2.71%.
        "optimality (adjacency, all changes)": replay(idx_opt, updates),
        # The witness, which is what the upper bound actually rests on.
        "witness (edges, deletions only)": replay(idx_witness,
                                                 per_filing_removed),
        # DEGENERATE, and kept in order to say so. This row was written to
        # decompose the saving into "monotonicity" and "smaller dependency",
        # and that decomposition is ill-posed: a witness edge exists in the old
        # snapshot, so it can only ever be deleted and no addition can touch
        # it, which makes this row identical to the one above by construction.
        # The small dependency is *licensed by* the monotonicity — the witness
        # is only a sound certificate because additions cannot break it — so
        # the two are one effect and no measurement here separates them.
        "witness (edges, all changes) [degenerate]": replay(idx_witness,
                                                            per_filing_all),
    }

    print()
    hdr = (f"{'certificate':<38} {'updates':>8} {'invalid':>9} {'P(hit)':>9} "
           f"{'ceiling':>10} {'advantage':>11} {'ours $':>11} {'theirs $':>11}")
    print(hdr)
    print("-" * len(hdr))
    for name, r in rows.items():
        ceil = r["ceiling_1_over_p"]
        print(f"{name:<38} {r['updates']:>8} {r['invalidations']:>9} "
              f"{r['p_hit']:>8.4%} "
              f"{('inf' if ceil == float('inf') else f'{ceil:,.0f}x'):>10} "
              f"{r['advantage']:>10.1f}x {r['ours_usd']:>11.2e} "
              f"{r['theirs_usd_extrapolated']:>11.2e}")

    opt = rows["optimality (adjacency, all changes)"]
    wit = rows["witness (edges, deletions only)"]
    print()
    print(f"control: optimality P(hit) {opt['p_hit']:.4%} against the 2.71% "
          f"already on disk, advantage {opt['advantage']:.1f}x against 37.3x")
    print(f"the split is worth {wit['advantage']/opt['advantage']:.0f}x "
          f"on the upper bound — and it buys HALF an answer, a maintained "
          f"`<= k`, not a maintained `= k`")

    # --- ANCHOR. The witness certificate claims soundness: if none of its
    # edges was deleted, a cover of that size still exists. That is an argument,
    # and this repo does not publish arguments. Every surviving witness is
    # checked against the new snapshot by re-solving.
    #
    # Two anchors, because they catch different things. The witness's soundness
    # is *structural* — the k edges ARE a cover, so if they all still exist a
    # cover of size k still exists, and no measurement can make that more true.
    # What can be wrong is the implementation: the wrong edges recorded, or an
    # index that misses a deletion. So the first anchor checks every witness
    # against the snapshot it was built on (n=300, not sample-limited), and the
    # second re-solves the survivors on the new one (n small, because most
    # witnesses do not survive a whole quarter — which is itself the point).
    malformed = 0
    for q, (k, w, _) in zip(queries, answers):
        if not w:
            continue
        exists = all(("portfolio", f) in old and s in old[("portfolio", f)]
                     for _, f, s in w)
        # One edge per ITEM, drawn from at most k distinct FILERS. Comparing
        # |w| to k is the wrong comparison and it failed 300/300 on the first
        # run: |w| is 12 and k is 4 to 9. What has to hold is that the witness
        # covers every item and names no more filers than the optimum claims.
        covers_all = {s for _, _, s in w} == {x for x in q
                                             if old.get(("holders", x))}
        if not exists or not covers_all or len({f for _, f, _ in w}) > k:
            malformed += 1
    print(f"\nanchor A: {len(answers) - malformed}/{len(answers)} witnesses are "
          f"real edges in the old snapshot, cover every item, and name no more "
          f"filers than the optimum ({malformed} malformed)")

    print("anchor B: re-solving every surviving witness on the new snapshot ...",
          flush=True)
    survived = broken = rechecked = 0
    for k, w, _ in answers:
        if any(("portfolio", f) not in new or s not in new[("portfolio", f)]
               for _, f, s in w):
            continue                       # witness edge gone; not certified
        survived += 1
        q = tuple(sorted({s for _, _, s in w}))
        if len(q) < COVER_SIZE:            # an item with no holders at all
            continue
        rechecked += 1
        if optimal_cover(new, q)[0] > k:
            broken += 1
    print(f"  {survived}/{len(answers)} witnesses intact, {rechecked} "
          f"re-solved, {broken} where the maintained bound was WRONG")
    if broken:
        print("  ANCHOR FAILED: a certified `<= k` did not hold on the new "
              "snapshot. The witness certificate is unsound as implemented.")
    else:
        print("  anchor holds: every certified bound survives re-solution")
    rows["anchor"] = {"witnesses_intact": survived, "rechecked": rechecked,
                      "broken": broken}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"seed": SEED, "n_queries": N_QUERIES, "cover_size": COVER_SIZE,
         "compute_ns_per_answer": compute_ns, "edges_opened": len(added),
         "edges_closed": len(removed), "total_edges": total_edges,
         "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
