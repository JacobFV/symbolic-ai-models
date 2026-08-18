"""Does the minimal certificate survive a graph that has a diameter?

`cert_witness_path.py` maintained a **complete** shortest-path answer at
13,987x, by noticing that the BFS's 1,328-key read set over-approximated the
claim's dependency by 6,591x — for a 1-hop answer nothing can be shorter, and
for a 2-hop answer "no 1-hop path" is exactly "the two portfolios do not
intersect", two facts.

Both of those derivations are about `d <= 2`, and the co-holding graph has no
diameter to speak of: any two 13F filers holding one common large-cap are one
hop apart. The finding's own note names this as the thing that would break it.

So: the openflights route network under a 2,000 km range limit. 6,072 airports,
37,042 routes, a graph this repo has already measured as dense and nearly
connected (amplification 8.3x–44x), and one where a shortest path is actually
long.

The quantity is the **minimal optimality dependency**: to certify "no path
shorter than `d`", you must know that the destination lies outside the ball of
radius `d-1` around the source, so the dependency is that ball's edges.
Meet-in-the-middle halves the radius — search `ceil((d-1)/2)` from one end and
`floor((d-1)/2)` from the other — and does not change the growth rate. Against
that, the witness is `d` edges and grows linearly.

**No update stream is needed and none is invented.** The question is whether the
minimal dependency stays small, which is a property of the graph. Pricing it
against an injected delta would only multiply this number by a rate somebody
chose.

Run: uv run python -u scripts/cert_diameter.py
"""

from __future__ import annotations

import json
import random
import statistics
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Mapping

from symbolic_ai_adapters import load_airports, load_routes
from symbolic_ai_core.source import SourceRegistry, data_root
from symbolic_ai_tasks.range_limited_routing import build_network

OUT = Path("runs/cert_diameter.json")
SEED = 20260818
LIMIT_KM = 2000.0
N_PAIRS = 400


def bfs_path(adj: Mapping[str, frozenset[str]], src: str, dst: str,
             cap: int = 12) -> tuple[int, tuple[tuple[str, str], ...]]:
    """Shortest hop path, and its edges. -1 if unreachable within `cap`."""
    if src == dst:
        return 0, ()
    parent: dict[str, str | None] = {src: None}
    q = deque([(src, 0)])
    while q:
        node, d = q.popleft()
        if d >= cap:
            continue
        for nxt in adj.get(node, ()):
            if nxt in parent:
                continue
            parent[nxt] = node
            if nxt == dst:
                edges, cur = [], nxt
                while parent[cur] is not None:
                    edges.append((parent[cur], cur))
                    cur = parent[cur]
                return d + 1, tuple(reversed(edges))
            q.append((nxt, d + 1))
    return -1, ()


def ball_edges(adj: Mapping[str, frozenset[str]], root: str, radius: int
               ) -> tuple[set[tuple[str, str]], set[str]]:
    """Every edge inside the ball of the given radius, and the nodes in it.

    These are the facts a proof of "the destination is not within `radius`
    hops of here" must consult: you cannot know the ball's contents without
    reading the edges that define it.
    """
    edges: set[tuple[str, str]] = set()
    seen = {root}
    frontier = [root]
    for _ in range(radius):
        nxt_frontier = []
        for node in frontier:
            for nxt in adj.get(node, ()):
                edges.add((node, nxt))
                if nxt not in seen:
                    seen.add(nxt)
                    nxt_frontier.append(nxt)
        frontier = nxt_frontier
    return edges, seen


def minimal_optimality(adj, radj, src: str, dst: str, d: int
                       ) -> tuple[int, str]:
    """|dependency| for "no path shorter than d", by meet-in-the-middle.

    Searching `ceil((d-1)/2)` forward from the source and `floor((d-1)/2)`
    backward from the destination certifies the same thing as one ball of
    radius `d-1` and reads far fewer edges, so this is the *strongest* honest
    version of the certificate — reporting the naive one-sided ball would
    inflate the result in the direction of the hypothesis.
    """
    if d <= 1:
        return 0, "unconditional: nothing is shorter than one hop"
    r = d - 1
    fwd, _ = ball_edges(adj, src, (r + 1) // 2)
    bwd, _ = ball_edges(radj, dst, r // 2)
    return len(fwd) + len(bwd), f"meet-in-the-middle at radii {(r+1)//2}/{r//2}"


def main() -> None:
    rng = random.Random(SEED)
    print("loading the route network ...", flush=True)
    t0 = time.perf_counter()
    base = next(s for s in SourceRegistry().snapshots().values()
                if s.source == "openflights").resolve(data_root())
    air = load_airports(base)
    edges, _ = load_routes(base, known=air.world.entities)
    pos = {i: (e.facets["geo.place"].values["lat"],
               e.facets["geo.place"].values["lon"])
           for i, e in air.world.entities.items()}
    net = build_network(pos, edges)
    adj = net.within(LIMIT_KM)
    radj: dict[str, set[str]] = defaultdict(set)
    for s, ts in adj.items():
        for t in ts:
            radj[t].add(s)
    radj_f = {k: frozenset(v) for k, v in radj.items()}
    n_edges = sum(len(v) for v in adj.values())
    print(f"  {len(adj):,} airports with outbound legs, {n_edges:,} flyable "
          f"legs at {LIMIT_KM:.0f} km ({time.perf_counter()-t0:.1f}s)",
          flush=True)

    nodes = sorted(adj)
    print(f"\n{N_PAIRS} random pairs ...", flush=True)
    rows: list[dict[str, Any]] = []
    while len(rows) < N_PAIRS:
        a, b = rng.choice(nodes), rng.choice(nodes)
        if a == b:
            continue
        d, path = bfs_path(adj, a, b)
        if d <= 0:
            continue
        opt, how = minimal_optimality(adj, radj_f, a, b, d)
        rows.append({"src": a, "dst": b, "d": d, "witness": len(path),
                     "optimality": opt, "how": how})

    by_d: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by_d[r["d"]].append(r)

    print()
    hdr = (f"{'d (hops)':>9} {'n':>5} {'witness':>9} {'minimal optimality':>20} "
           f"{'ratio':>10} {'% of graph':>11}")
    print(hdr)
    print("-" * len(hdr))
    summary = []
    for d in sorted(by_d):
        rs = by_d[d]
        w = statistics.mean(r["witness"] for r in rs)
        o = statistics.median(r["optimality"] for r in rs)
        omax = max(r["optimality"] for r in rs)
        summary.append({"d": d, "n": len(rs), "witness_mean": w,
                        "optimality_median": o, "optimality_max": omax,
                        "ratio": o / w if w else 0.0,
                        "frac_of_graph": o / n_edges})
        print(f"{d:>9} {len(rs):>5} {w:>9.1f} {o:>14,.0f} (max {omax:>6,}) "
              f"{(o/w if w else 0):>9.1f}x {o/n_edges:>10.2%}")

    ds = sorted(r["d"] for r in rows)
    print(f"\nhops p50 {ds[len(ds)//2]}, p90 {ds[int(len(ds)*0.9)]}, "
          f"max {ds[-1]}")

    # The comparison that decides it. 13F: witness 2.5 edges, minimal
    # optimality 0.5 keys, ratio 0.2x, and the full answer maintained at
    # 13,987x. If the ratio here is orders of magnitude larger, the full-answer
    # result was a property of a graph with no diameter.
    overall_w = statistics.mean(r["witness"] for r in rows)
    overall_o = statistics.median(r["optimality"] for r in rows)
    print(f"\nthis graph:  witness {overall_w:.1f} edges, minimal optimality "
          f"{overall_o:,.0f} edges, ratio {overall_o/overall_w:,.0f}x")
    print(f"13F co-holding: witness 2.5 edges, minimal optimality 0.5 keys, "
          f"ratio 0.2x")

    # Control: the d<=2 cases must look like 13F's -- small -- or the two
    # measurements are not comparable and neither number means anything.
    shallow = [r for r in rows if r["d"] <= 2]
    if shallow:
        so = statistics.median(r["optimality"] for r in shallow)
        print(f"\ncontrol: {len(shallow)} pairs at d<=2 have median minimal "
              f"optimality {so:,.0f} edges "
              f"({'small, comparable to 13F' if so < 100 else 'NOT small — the two graphs differ at d<=2 too, so the comparison across d is confounded'})")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seed": SEED, "limit_km": LIMIT_KM,
                               "flyable_legs": n_edges, "by_d": summary,
                               "pairs": rows[:50]}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
