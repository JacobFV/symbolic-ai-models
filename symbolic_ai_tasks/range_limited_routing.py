"""Minimum-hop routing when every leg must be short enough to fly.

The first **powered** composition on real data. The SEC-to-GLEIF attempt failed
not on architecture but on density — 3.7% of GLEIF carries ownership edges, so
the join left n=3. Openflights has two dense halves of the same source: 6,072
airports with coordinates and 37,042 scheduled routes, and a question that
needs both.

Given an aircraft range limit, the reachable network is not the route network:
a leg longer than the limit cannot be flown, so ``geo`` decides which edges
exist and the graph search runs on what survives. Either kernel alone answers a
different question.

Two things this measures that a single-kernel task cannot:

* **Whether composition is load-bearing.** The graph-only answer — plain
  breadth-first search ignoring distance — agrees with the constrained answer
  on **13.8%** of pairs at a 2,000 km limit. It is not a near-miss heuristic.
* **How error crosses the boundary.** Substituting the spherical
  approximation for the geodesic reclassifies **0.051%** of legs and changes
  **0.650%** of answers. A composition amplifies its inputs' errors, and here
  by roughly 13x, because a misclassified hub edge lies on many shortest paths.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from symbolic_ai_kernels.geo import distance_km, haversine_km

__all__ = ["RangeNetwork", "build_network", "min_hops", "agreement",
           "answer_sensitivity", "hop_table", "compare_from_sources"]


@dataclass(frozen=True)
class RangeNetwork:
    """The route graph, plus the leg lengths that decide which edges are real."""

    adjacency: Mapping[str, frozenset[str]]
    length_km: Mapping[tuple[str, str], float]

    @property
    def nodes(self) -> tuple[str, ...]:
        return tuple(sorted(self.adjacency))

    def within(self, limit_km: float) -> dict[str, frozenset[str]]:
        """The subgraph an aircraft of this range can actually fly."""
        out: dict[str, set[str]] = collections.defaultdict(set)
        for (s, t), d in self.length_km.items():
            if d <= limit_km:
                out[s].add(t)
        return {k: frozenset(v) for k, v in out.items()}


def build_network(pos: Mapping[str, tuple[float, float]],
                  edges: Sequence[tuple[str, str]],
                  *, metric: Callable[..., float] = distance_km
                  ) -> RangeNetwork:
    """Measure every leg once.

    ``metric`` is a parameter so the sensitivity of the *answer* to the choice
    of geodesy can be measured rather than argued about. It defaults to the
    geo kernel's Vincenty-on-WGS84; passing :func:`haversine_km` is what
    produces the amplification number in the module docstring.
    """
    adj: dict[str, set[str]] = collections.defaultdict(set)
    length: dict[tuple[str, str], float] = {}
    for s, t in edges:
        if s not in pos or t not in pos:
            continue
        adj[s].add(t)
        length[(s, t)] = metric(*pos[s], *pos[t])
    return RangeNetwork(adjacency={k: frozenset(v) for k, v in adj.items()},
                        length_km=length)


def min_hops(adjacency: Mapping[str, frozenset[str] | set[str]],
             source: str, target: str, *, cap: int = 8) -> int | None:
    """Fewest legs from source to target, or ``None`` within ``cap`` hops.

    ``None`` means "not found within the cap", which is not the same as
    "unreachable", and the caller is told which cap produced it rather than
    being handed a bare failure.
    """
    if source == target:
        return 0
    seen = {source}
    frontier = {source}
    for hop in range(1, cap + 1):
        nxt: set[str] = set()
        for u in frontier:
            nxt |= set(adjacency.get(u, ()))
        nxt -= seen
        if target in nxt:
            return hop
        seen |= nxt
        frontier = nxt
        if not frontier:
            return None
    return None


def agreement(net: RangeNetwork, limit_km: float,
              pairs: Sequence[tuple[str, str]]) -> dict[str, float]:
    """How often the graph-only answer matches the composed one.

    The floor here is not a weak baseline, it is **the other kernel used
    alone** — which is the only floor that answers "was the composition worth
    building".
    """
    limited = net.within(limit_km)
    agree = longer = unreachable = 0
    for s, t in pairs:
        whole = min_hops(net.adjacency, s, t)
        cut = min_hops(limited, s, t)
        if whole == cut:
            agree += 1
        elif cut is None:
            unreachable += 1
        else:
            longer += 1
    n = len(pairs) or 1
    return {"agree": agree / n, "more_hops": longer / n,
            "unreachable": unreachable / n, "n": len(pairs)}


def answer_sensitivity(exact: RangeNetwork, approx: RangeNetwork,
                       limit_km: float, pairs: Sequence[tuple[str, str]]
                       ) -> dict[str, float]:
    """What a small metric error does to the answer once a graph amplifies it."""
    flipped = sum(1 for e, d in exact.length_km.items()
                  if (d <= limit_km) != (approx.length_km[e] <= limit_km))
    a, b = exact.within(limit_km), approx.within(limit_km)
    changed = sum(1 for s, t in pairs
                  if min_hops(a, s, t) != min_hops(b, s, t))
    n_edges = len(exact.length_km) or 1
    n = len(pairs) or 1
    return {"legs_flipped": flipped, "leg_flip_rate": flipped / n_edges,
            "answers_changed": changed, "answer_change_rate": changed / n,
            "amplification": (changed / n) / (flipped / n_edges)
            if flipped else 0.0}


def hop_table(adjacency: Mapping[str, frozenset[str] | set[str]],
              source: str, *, cap: int = 8) -> dict[str, int]:
    """Hop distance from one source to every node it reaches within ``cap``.

    One traversal answers as many pairs as there are nodes, which is what makes
    a statistically honest sample affordable: sampling *pairs* costs a search
    each and left the earlier estimates resting on 7 to 32 events, and small
    counts are this repo's oldest way of being confidently wrong.
    """
    dist = {source: 0}
    frontier = {source}
    for hop in range(1, cap + 1):
        nxt: set[str] = set()
        for u in frontier:
            nxt |= set(adjacency.get(u, ()))
        nxt -= dist.keys()
        if not nxt:
            break
        for v in nxt:
            dist[v] = hop
        frontier = nxt
    return dist


def compare_from_sources(a: Mapping[str, frozenset[str] | set[str]],
                         b: Mapping[str, frozenset[str] | set[str]],
                         sources: Sequence[str], targets: Sequence[str],
                         *, cap: int = 8) -> dict[str, float]:
    """Compare two adjacency structures over every (source, target) pair."""
    same = diff = total = 0
    for s in sources:
        da, db = hop_table(a, s, cap=cap), hop_table(b, s, cap=cap)
        for t in targets:
            if t == s:
                continue
            total += 1
            if da.get(t) == db.get(t):
                same += 1
            else:
                diff += 1
    return {"pairs": total, "same": same, "differ": diff,
            "differ_rate": diff / total if total else 0.0}
