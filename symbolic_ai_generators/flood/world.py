"""Generating the world, rendering the report, and the brute-force oracle.

Everything is a pure function of the seed, like every other generator here, so a
case is addressable and a cache is optional.

The **oracle is computed by exhaustive search** rather than by the kernels it is
meant to check. That is the whole reason it exists: an oracle that shared the
kernels' code would agree with them by construction, which is the same defect as
a floor fitted with the model's own features. It is exponential and only usable
at this size, which is fine — its job is to be independent, not fast.
"""

from __future__ import annotations

import hashlib
import itertools
import random
from dataclasses import dataclass, field
from typing import Any, Iterator, Sequence

from symbolic_ai_core.world import (Claim, Entity, EntityRef, Facet, Quantity,
                                    WorldSnapshot)

__all__ = ["FloodCase", "generate", "render_report", "solution_by_search",
           "REACH_RULES"]

#: Reachability over an **undirected, cyclic** road network, avoiding flooded
#: regions. Written as ASP text because both the ASP kernel and the datalog
#: kernel need the same relation, and the datalog form is built from these by
#: :func:`reach_rules` so the two cannot drift.
REACH_RULES_TEXT = """
open(A, B) :- link(A, B), not flooded(A), not flooded(B).
open(B, A) :- link(A, B), not flooded(A), not flooded(B).
reach(A, B) :- open(A, B).
reach(A, C) :- open(A, B), reach(B, C).
"""


def reach_rules():
    """The same relation as :data:`REACH_RULES_TEXT`, as datalog ``Rule``s."""
    from symbolic_ai_kernels.datalog import Atom, Literal, Rule, Var
    A, B, C = Var("A"), Var("B"), Var("C")
    link, flooded = Atom("link", (A, B)), Atom("flooded", (A,))
    return [
        Rule(Atom("open", (A, B)), (Literal(link),
                                    Literal(Atom("flooded", (A,)), True),
                                    Literal(Atom("flooded", (B,)), True))),
        Rule(Atom("open", (B, A)), (Literal(link),
                                    Literal(Atom("flooded", (A,)), True),
                                    Literal(Atom("flooded", (B,)), True))),
        Rule(Atom("reach", (A, B)), (Literal(Atom("open", (A, B))),)),
        Rule(Atom("reach", (A, C)), (Literal(Atom("open", (A, B))),
                                     Literal(Atom("reach", (B, C))))),
    ]


REACH_RULES = reach_rules


@dataclass(frozen=True)
class FloodCase:
    """One generated world, with its text surface and its independent answer."""

    seed: int
    world: WorldSnapshot
    report: str
    regions: tuple[str, ...]
    links: tuple[tuple[str, str], ...]
    flooded: tuple[str, ...]
    bridges: dict[tuple[str, str], float]
    vehicles: dict[str, tuple[float, float]]     #: id -> (mass kg, capacity kg)
    depot: str
    demand_site: str
    demand_kg: float
    answer: tuple[str, ...]                      #: vehicles that can do the job
    meta: dict[str, Any] = field(default_factory=dict)


def _rng(seed: int) -> random.Random:
    h = hashlib.blake2b(f"flood|{seed}".encode(), digest_size=8)
    return random.Random(int.from_bytes(h.digest(), "big"))


def generate(seed: int, *, n_regions: int = 6, n_vehicles: int = 3,
             n_chords: int = 2) -> FloodCase:
    """One case. Pure in ``seed``.

    The road network is a **ring plus chords**, so it is genuinely cyclic — the
    topology the flow DAG refuses and the world IR exists to hold — and the
    reachability question is not answerable by a tree walk.
    """
    r = _rng(seed)
    regions = tuple(f"region_{i}" for i in range(n_regions))

    links: list[tuple[str, str]] = [
        (regions[i], regions[(i + 1) % n_regions]) for i in range(n_regions)]
    candidates = [(a, b) for i, a in enumerate(regions)
                  for b in regions[i + 2:]
                  if (a, b) not in links and (b, a) not in links]
    r.shuffle(candidates)
    links.extend(candidates[:n_chords])
    links = [tuple(sorted(l)) for l in links]

    depot = regions[0]
    demand_site = regions[n_regions // 2]

    # Flooding never closes the depot or the demand site: a case with no route
    # at all is a different (and much easier) question.
    floodable = [x for x in regions if x not in (depot, demand_site)]
    flooded = tuple(sorted(r.sample(floodable, r.randint(1, 2))))

    # Bridges cover most links, and the limits straddle the laden masses. Both
    # are tuned so the answer PARTITIONS the fleet rather than taking all of it
    # or none: at the first parameters tried, 10 of 12 seeds answered "every
    # truck" or "no truck", which is a task with almost no signal in it.
    bridges: dict[tuple[str, str], float] = {}
    for link in r.sample(links, max(3, (2 * len(links)) // 3)):
        bridges[link] = float(r.choice([2500, 3000, 3500, 4500, 6000]))

    vehicles = {f"truck_{i}": (float(r.choice([1200, 1800, 2600, 3200])),
                               float(r.choice([1500, 2500, 4000])))
                for i in range(n_vehicles)}
    demand_kg = float(r.choice([900, 1400, 2100]))

    answer = solution_by_search(regions, links, flooded, bridges, vehicles,
                                depot, demand_site, demand_kg)
    world = _build_world(regions, links, flooded, bridges, vehicles, depot,
                         demand_site, demand_kg)
    return FloodCase(
        seed=seed, world=world,
        report=render_report(regions, links, flooded, bridges, vehicles, depot,
                             demand_site, demand_kg),
        regions=regions, links=tuple(links), flooded=flooded, bridges=bridges,
        vehicles=vehicles, depot=depot, demand_site=demand_site,
        demand_kg=demand_kg, answer=answer,
        meta={"n_links": len(links), "n_bridges": len(bridges)})


def _build_world(regions, links, flooded, bridges, vehicles, depot,
                 demand_site, demand_kg) -> WorldSnapshot:
    entities: dict[str, Entity] = {
        rid: Entity(rid, types=("region",),
                    facets={"geo.place": Facet("geo.place", {"name": rid})})
        for rid in regions}
    claims: list[Claim] = []

    for a, b in links:
        claims.append(Claim("link", {"a": EntityRef(a), "b": EntityRef(b)}))
    for f in flooded:
        claims.append(Claim("flooded", {"where": EntityRef(f)}))

    for i, ((a, b), limit) in enumerate(sorted(bridges.items())):
        bid = f"bridge_{i}"
        entities[bid] = Entity(bid, types=("bridge",), facets={
            "geo.network": Facet("geo.network", {"span": f"{a}-{b}"})})
        claims.append(Claim("bridge_on", {"a": EntityRef(a), "b": EntityRef(b),
                                          "via": EntityRef(bid)}))
        # A Quantity role: datalog discards this, SMT is built for it.
        claims.append(Claim("load_limit", {"of": EntityRef(bid),
                                           "value": Quantity(limit, "kg")}))

    for vid, (mass, cap) in sorted(vehicles.items()):
        entities[vid] = Entity(vid, types=("vehicle",), facets={
            "scene.body": Facet("scene.body", {"kind": "truck"}),
            "logic.constraint": Facet("logic.constraint", {
                "variables": {"payload": {"unit": "kg"}}})})
        claims.append(Claim("mass", {"of": EntityRef(vid),
                                     "value": Quantity(mass, "kg")}))
        claims.append(Claim("capacity", {"of": EntityRef(vid),
                                         "value": Quantity(cap, "kg")}))

    claims.append(Claim("depot", {"where": EntityRef(depot)}))
    claims.append(Claim("needs", {"where": EntityRef(demand_site)}))
    claims.append(Claim("demand", {"of": EntityRef(demand_site),
                                   "value": Quantity(demand_kg, "kg")}))
    return WorldSnapshot(entities=entities, claims=tuple(claims))


# ---------------------------------------------------------------------------
# the independent oracle
# ---------------------------------------------------------------------------
def _routes(regions, links, flooded, depot, demand_site
            ) -> Iterator[tuple[str, ...]]:
    """Every simple path from depot to demand site avoiding flooded regions.

    Exhaustive and exponential. It is not the kernels' algorithm and shares no
    code with them, which is the only way its agreement means anything.
    """
    adj: dict[str, set[str]] = {r: set() for r in regions}
    for a, b in links:
        if a in flooded or b in flooded:
            continue
        adj[a].add(b)
        adj[b].add(a)
    stack: list[tuple[str, tuple[str, ...]]] = [(depot, (depot,))]
    while stack:
        node, path = stack.pop()
        if node == demand_site and len(path) > 1:
            yield path
            continue
        for nxt in sorted(adj[node]):
            if nxt not in path and nxt not in flooded:
                stack.append((nxt, path + (nxt,)))


def solution_by_search(regions, links, flooded, bridges, vehicles, depot,
                       demand_site, demand_kg) -> tuple[str, ...]:
    """Which vehicles can deliver the demand. Brute force, no kernels.

    A vehicle qualifies when it has the capacity **and** some route exists whose
    every bridge admits its laden mass. Note the quantifier: *some* route, not
    the shortest one — the shortest route may be the one with the weak bridge,
    which is exactly the case a single-kernel answer gets wrong.
    """
    routes = list(_routes(regions, links, flooded, depot, demand_site))
    out = []
    for vid, (mass, cap) in sorted(vehicles.items()):
        if cap < demand_kg:
            continue
        laden = mass + demand_kg
        for path in routes:
            limits = [bridges[tuple(sorted((a, b)))]
                      for a, b in zip(path, path[1:])
                      if tuple(sorted((a, b))) in bridges]
            if all(laden <= lim for lim in limits):
                out.append(vid)
                break
    return tuple(out)


# ---------------------------------------------------------------------------
# the text surface
# ---------------------------------------------------------------------------
def render_report(regions, links, flooded, bridges, vehicles, depot,
                  demand_site, demand_kg) -> str:
    """A multi-paragraph incident report. **It never states the answer.**

    Each fact appears in exactly one paragraph, and the three that determine the
    answer — which regions are cut off, which bridges are weak, which vehicle is
    heavy — are in three different ones. No sentence is close to "truck_1 can go";
    that sentence is a function of facts nobody put together.
    """
    paras = []
    road_lines = ", ".join(f"{a} to {b}" for a, b in sorted(links))
    paras.append(
        f"INCIDENT REPORT. The road network in the affected area connects "
        f"{len(regions)} regions. Open carriageways on the last survey were: "
        f"{road_lines}. The network is a ring with additional cross-links, so "
        f"most regions have more than one approach.")
    paras.append(
        f"Flooding. Standing water has closed {', '.join(flooded)} to all "
        f"traffic. Regions are impassable rather than slow; no route may pass "
        f"through them.")
    if bridges:
        limits = "; ".join(
            f"the {a}-{b} crossing is posted at {int(limit)} kg"
            for (a, b), limit in sorted(bridges.items()))
        paras.append(f"Structures. Several crossings carry posted load limits: "
                     f"{limits}. Limits apply to laden gross mass.")
    fleet = "; ".join(
        f"{vid} has an unladen mass of {int(mass)} kg and a capacity of "
        f"{int(cap)} kg" for vid, (mass, cap) in sorted(vehicles.items()))
    paras.append(f"Fleet. The depot at {depot} holds: {fleet}.")
    paras.append(
        f"Requirement. {demand_site} requires a delivery of {int(demand_kg)} kg "
        f"of supplies. Dispatch has not yet been assigned.")
    return "\n\n".join(paras)
