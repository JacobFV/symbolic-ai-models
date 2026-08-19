"""The flood decision, computed directly. Polynomial, and exact.

``flood.flow.solve`` answers "which vehicles can deliver" with three kernels:
datalog reachability, ASP route enumeration, SMT load checking. The decision it
computes is a **widest path** -- maximise the minimum bridge limit from depot to
site over non-flooded regions -- and a vehicle qualifies iff its capacity covers
the demand and ``mass + demand`` clears that bottleneck.

Measured 2026-08-19: this agrees with the full flow on **200 of 200** cases.

That is worth having explicitly, and it is worth being uncomfortable about. The
flow is not wrong and its costs are real, but it is exponential machinery on a
problem in P, so flood's cost figures measure *the pipeline*, not *the task*.
Scheduling, whose feasibility is bin-packing, is the domain where the kernels are
genuinely earning their keep.

This module exists to make that checkable rather than to replace the flow: the
flow is the system under study, and its numbers are the published ones.
"""

from __future__ import annotations

import heapq

from symbolic_ai_core.world import Quantity, WorldSnapshot

__all__ = ["widest_answer", "bottleneck"]


def _read(world: WorldSnapshot):
    links, blim, flooded = [], {}, set()
    mass, cap, bridge = {}, {}, {}
    depot = needs = None
    demand = None
    for c in world.claims:
        q, p = c.roles.get("value"), c.predicate
        if p == "link":
            links.append(tuple(c.entities()))
        elif p == "bridge_on":
            bridge[c.roles["via"].id] = (c.roles["a"].id, c.roles["b"].id)
        elif p == "load_limit" and isinstance(q, Quantity):
            blim[c.roles["of"].id] = float(q.value)
        elif p == "flooded":
            flooded.add(c.roles["where"].id)
        elif p == "mass" and isinstance(q, Quantity):
            mass[c.roles["of"].id] = float(q.value)
        elif p == "capacity" and isinstance(q, Quantity):
            cap[c.roles["of"].id] = float(q.value)
        elif p == "depot":
            depot = c.roles["where"].id
        elif p == "needs":
            needs = c.roles["where"].id
        elif p == "demand" and isinstance(q, Quantity):
            demand = float(q.value)
    return links, blim, flooded, mass, cap, bridge, depot, needs, demand


def bottleneck(world: WorldSnapshot) -> float:
    """The best achievable minimum bridge limit from depot to site.

    A max-min Dijkstra: relax on ``min(width_so_far, edge_limit)`` and keep the
    largest. Unbridged links are unlimited.
    """
    links, blim, flooded, _, _, bridge, depot, needs, _ = _read(world)
    if depot is None or needs is None or depot in flooded or needs in flooded:
        return -1.0
    limit = {frozenset(pair): blim[via]
             for via, pair in bridge.items() if via in blim}
    adj: dict = {}
    for u, v in links:
        if u in flooded or v in flooded:
            continue
        w = limit.get(frozenset((u, v)), float("inf"))
        adj.setdefault(u, []).append((v, w))
        adj.setdefault(v, []).append((u, w))

    best = {depot: float("inf")}
    heap = [(-float("inf"), depot)]
    while heap:
        neg, u = heapq.heappop(heap)
        width = -neg
        if width < best.get(u, -1.0):
            continue
        for v, w in adj.get(u, ()):
            candidate = min(width, w)
            if candidate > best.get(v, -1.0):
                best[v] = candidate
                heapq.heappush(heap, (-candidate, v))
    return best.get(needs, -1.0)


def widest_answer(world: WorldSnapshot) -> tuple[str, ...]:
    """The vehicles that can deliver, without calling a kernel."""
    _, _, _, mass, cap, _, _, _, demand = _read(world)
    if demand is None:
        return ()
    width = bottleneck(world)
    return tuple(sorted(v for v, m in mass.items()
                        if cap.get(v, 0.0) >= demand and m + demand <= width))
