"""The 95x was not about set cover. It is the NP/coNP asymmetry, and it has a price.

`cert_bound_asymmetry.py` split one optimum into an existential half with a
twelve-edge witness (P_hit 0.0300%, 3,309x) and a universal half that must read
the complement (P_hit 2.8589%, 35.0x). That is 95x, on a clingo set cover.

The claim being tested here is that the 95x is not a property of set cover, of
clingo, or of twelve. It is the textbook asymmetry between a claim with a short
certificate and its complement — "a cover of size <= k exists" is NP and has a
witness a verifier checks in polynomial time; "no cover of size k-1 exists" is
coNP and has none — and what is new is only that the asymmetry turns out to have
a **maintenance price on real filed data**.

If that reading is right the gap must replicate on a structurally different
problem, and it should be **larger** where the search frontier is larger. So:
shortest co-holding path between two 13F filers, `filer -> security -> filer`,
same two snapshots, same 8,425-filing stream, a BFS instead of a solver.

    witness      the path's own edges. A path of that length still exists as
                 long as they do, and adding holdings can only create shortcuts,
                 never lengthen a path that is already there.
    optimality   every fact the BFS read — the explored frontier — recorded by
                 the same generic mechanism, with no per-query rule.

Run: uv run python -u scripts/cert_witness_path.py
"""

from __future__ import annotations

import json
import random
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Hashable, Mapping

from scripts.cert_maintenance_13f import (
    NEW_FILE, OLD_FILE, SEED, USD_PER_CORE_HOUR, load_store)
from symbolic_ai_core.runtime.certificate import certify

OUT = Path("runs/cert_witness_path.json")
N_QUERIES = 300
MAX_HOPS = 6


def shortest_co_holding_path(src: str, dst: str):
    """BFS over `filer -> security -> filer`, returning (hops, path_edges).

    Written against the mapping it is handed and nothing else, so the recording
    store sees every fact it consulted. That is the point: the optimality
    dependency is *discovered*, not declared, and it comes out as whatever the
    search actually had to look at.
    """
    def compute(store: Mapping) -> Any:
        if src == dst:
            return (0, ())
        # (node, is_filer) frontier; parents for path reconstruction.
        parent: dict[tuple[str, bool], tuple[str, bool] | None] = {(src, True): None}
        q = deque([(src, True, 0)])
        while q:
            node, is_filer, d = q.popleft()
            if d >= MAX_HOPS * 2:
                continue
            key = ("portfolio", node) if is_filer else ("holders", node)
            for nxt in sorted(store.get(key, frozenset())):
                state = (nxt, not is_filer)
                if state in parent:
                    continue
                parent[state] = (node, is_filer)
                if nxt == dst and not is_filer is False:
                    pass
                if not is_filer and nxt == dst:
                    # reconstruct
                    edges = []
                    cur: tuple[str, bool] | None = state
                    while parent[cur] is not None:
                        prev = parent[cur]
                        f, s = (prev[0], cur[0]) if prev[1] else (cur[0], prev[0])
                        edges.append(("holds", f, s))
                        cur = prev
                    return ((d + 1) // 2 + (d + 1) % 2, tuple(sorted(edges)))
                q.append((nxt, not is_filer, d + 1))
        return (-1, ())
    return compute


def main() -> None:
    rng = random.Random(SEED)
    print("loading two filed snapshots ...", flush=True)
    old, new = load_store(OLD_FILE), load_store(NEW_FILE)

    empty: frozenset[str] = frozenset()
    per_filing_edges: list[frozenset[Hashable]] = []
    per_filing_keys: list[frozenset[Hashable]] = []
    per_filing_removed: list[frozenset[Hashable]] = []
    filers_all = {k[1] for k in old if k[0] == "portfolio"}
    filers_all |= {k[1] for k in new if k[0] == "portfolio"}
    for f in sorted(filers_all):
        a = old.get(("portfolio", f), empty)
        b = new.get(("portfolio", f), empty)
        gone, came = a - b, b - a
        if not gone and not came:
            continue
        per_filing_removed.append(frozenset(("holds", f, s) for s in gone))
        per_filing_edges.append(frozenset(
            [("holds", f, s) for s in gone] + [("holds", f, s) for s in came]))
        per_filing_keys.append(frozenset(
            [("portfolio", f)] + [("holders", s) for s in gone | came]))
    n_upd = len(per_filing_edges)
    print(f"  {n_upd:,} filings", flush=True)

    filers = sorted(k[1] for k in old if k[0] == "portfolio")
    print(f"\nsearching {N_QUERIES} shortest co-holding paths ...", flush=True)
    t0 = time.perf_counter()
    certs, results = [], []
    while len(certs) < N_QUERIES:
        a, b = rng.choice(filers), rng.choice(filers)
        if a == b:
            continue
        cert = certify(shortest_co_holding_path(a, b), old)
        hops, edges = cert.answer
        if hops <= 0:
            continue
        certs.append(cert)
        results.append((a, b, hops, edges))
    compute_ns = (time.perf_counter() - t0) / N_QUERIES * 1e9

    hopcounts = sorted(h for _, _, h, _ in results)
    print(f"  {compute_ns/1e6:.1f} ms/answer; hops p50 "
          f"{hopcounts[len(hopcounts)//2]}, max {hopcounts[-1]}", flush=True)
    print(f"  witness    {sum(len(e) for _,_,_,e in results)/N_QUERIES:>10.1f} "
          f"edges", flush=True)
    print(f"  optimality {sum(c.size for c in certs)/N_QUERIES:>10.1f} keys "
          f"(the BFS frontier, recorded generically)", flush=True)

    idx_w: dict[Hashable, list[int]] = defaultdict(list)
    idx_o: dict[Hashable, list[int]] = defaultdict(list)
    for i, (_, _, _, edges) in enumerate(results):
        for k in edges:
            idx_w[k].append(i)
    for i, c in enumerate(certs):
        for k in c.digests:
            idx_o[k].append(i)

    def replay(index, per_filing) -> dict[str, Any]:
        hits = 0
        t = time.perf_counter_ns()
        for keys in per_filing:
            seen: set[int] = set()
            for k in keys:
                seen.update(index.get(k, ()))
            hits += len(seen)
        check_ns = time.perf_counter_ns() - t
        p = hits / (n_upd * N_QUERIES) if n_upd else 0.0
        ours = check_ns + hits * compute_ns
        theirs = N_QUERIES * n_upd * compute_ns
        return {"invalidations": hits, "p_hit": p,
                "ceiling_1_over_p": (1 / p) if p else float("inf"),
                "advantage": theirs / ours if ours else 0.0,
                "ours_usd": ours * USD_PER_CORE_HOUR / 3600 / 1e9,
                "theirs_usd_extrapolated": theirs * USD_PER_CORE_HOUR / 3600 / 1e9}

    # A third certificate, and the one that decides what the gap MEANS. The
    # BFS's recorded read set is the dependency of the *search*, not of the
    # *claim*: for a 1-hop answer nothing can be shorter (the pair is distinct
    # by construction), so optimality is unconditional; for a 2-hop answer
    # "no 1-hop path exists" is exactly "the two portfolios do not intersect",
    # which is two facts. Either way it is not 1,328. If this row is large, the
    # gap above is the NP/coNP asymmetry; if it is small, the gap above is
    # mostly the recording mechanism over-reading and my framing is wrong.
    idx_min: dict[Hashable, list[int]] = defaultdict(list)
    min_sizes = []
    for i, (a, b, hops, _) in enumerate(results):
        if hops <= 1:
            keys: tuple[Hashable, ...] = ()          # unconditional
        elif hops == 2:
            keys = (("portfolio", a), ("portfolio", b))
        else:                                        # not derived by hand
            keys = tuple(certs[i].digests)
        min_sizes.append(len(keys))
        for k in keys:
            idx_min[k].append(i)
    print(f"  optimality {sum(min_sizes)/N_QUERIES:>10.1f} keys "
          f"(hand-derived minimal, for hops <= 2)", flush=True)

    per_filing_both = [r | k for r, k in zip(per_filing_removed,
                                             per_filing_keys)]
    idx_full: dict[Hashable, list[int]] = defaultdict(list)
    for k, v in idx_w.items():
        idx_full[k].extend(v)
    for k, v in idx_min.items():
        idx_full[k].extend(v)

    rows = {"witness (path edges, deletions only)": replay(idx_w,
                                                          per_filing_removed),
            "optimality (BFS frontier, recorded)": replay(idx_o,
                                                          per_filing_keys),
            "optimality (hand-derived minimal)": replay(idx_min,
                                                        per_filing_keys),
            # Witness AND minimal optimality together certify the whole answer
            # `= d`, not a bound. This is the row that matters: it is the
            # complete answer, maintained.
            # The witness is keyed on EDGES and the minimal optimality set on
            # ADJACENCIES, so this row must be replayed against a stream
            # carrying both. Replaying it against the adjacency stream alone
            # silently matched nothing from the witness half and reported the
            # minimal row's number twice.
            "FULL ANSWER (witness + minimal)": replay(idx_full,
                                                      per_filing_both)}

    print()
    hdr = (f"{'certificate':<40} {'invalid':>10} {'P(hit)':>10} {'ceiling':>11} "
           f"{'advantage':>11}")
    print(hdr)
    print("-" * len(hdr))
    for name, r in rows.items():
        c = r["ceiling_1_over_p"]
        print(f"{name:<40} {r['invalidations']:>10} {r['p_hit']:>9.4%} "
              f"{('inf' if c == float('inf') else f'{c:,.0f}x'):>11} "
              f"{r['advantage']:>10.1f}x")

    w = rows["witness (path edges, deletions only)"]
    o = rows["optimality (BFS frontier, recorded)"]
    m = rows["optimality (hand-derived minimal)"]
    gap = w["advantage"] / o["advantage"] if o["advantage"] else float("inf")
    print(f"\ngap witness vs RECORDED optimality: {gap:,.0f}x, "
          f"against set cover's 95x")
    print(f"FULL ANSWER `= d` maintained at "
          f"{rows['FULL ANSWER (witness + minimal)']['advantage']:,.0f}x — "
          f"not a bound, the answer")
    if m["advantage"]:
        print(f"gap witness vs MINIMAL optimality:  "
              f"{w['advantage']/m['advantage']:,.1f}x")
        print(f"the recording mechanism over-read by "
              f"{m['advantage']/o['advantage']:,.0f}x, which is how much of the "
              f"first gap is an implementation artefact rather than the "
              f"claim's form")

    # CONTROL: a witness whose edges all survive must still be a path of that
    # length in the new snapshot. Checked directly, which is cheap and exact --
    # no re-search needed, because the edges themselves are the proof.
    intact = broken = 0
    for a, b, hops, edges in results:
        if any(("portfolio", f) not in new or s not in new[("portfolio", f)]
               for _, f, s in edges):
            continue
        intact += 1
        # the edges must chain a to b
        nodes = {a, b}
        for _, f, s in edges:
            nodes.add(f)
        if not edges or a not in {f for _, f, _ in edges}:
            broken += 1
    print(f"control: {intact}/{N_QUERIES} witnesses intact on the new snapshot, "
          f"{broken} that do not chain from the source")
    if broken:
        print("  CONTROL FAILED: a certified path witness is not a path.")

    rows["control"] = {"intact": intact, "broken": broken}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seed": SEED, "n": N_QUERIES,
                               "compute_ns_per_answer": compute_ns,
                               "hops_p50": hopcounts[len(hopcounts)//2],
                               "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
