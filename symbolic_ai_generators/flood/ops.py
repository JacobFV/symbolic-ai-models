"""The flow operations that turn a flood world into an answer.

One flow DAG, three kernels, two explicit couplings:

```
world  --datalog--> open/reach            (relational closure, cyclic network)
       --apply---->  world'
       --asp------> candidate routes      <- COUPLING 1: the completion space
                                             is built from datalog's DERIVED
                                             `open` facts, which ASP cannot
                                             compute itself
       --smt------> laden-mass feasibility <- COUPLING 2: the constraints are
                                             built from ASP's chosen routes,
                                             and read the load limits ASP
                                             cannot see because they are
                                             Quantities with units
       --fuse-----> can_serve
```

The division of labour is not decorative. Each kernel is doing the thing the
other two cannot:

* the road network is **cyclic**, so reachability is a recursive relational
  closure and neither ASP's choice rules nor SMT's arithmetic is the right tool;
* choosing a simple path is a **combinatorial completion** with degree and
  connectivity constraints, which datalog cannot express and SMT would encode
  badly;
* the bridge limits are **Quantities with units**, which the relational
  projection discards by construction — ASP literally cannot see them.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from symbolic_ai_core.artifact.value import Artifact, Provenance
from symbolic_ai_core.flow.port import Port
from symbolic_ai_core.flow.registry import OpDef, register_op
from symbolic_ai_core.world import Claim, EntityRef, Quantity, WorldSnapshot
from symbolic_ai_kernels import KernelRequest, get_kernel
from symbolic_ai_kernels.flow_ops import claims_artifact, read_world

__all__ = ["ROUTE_PROGRAM", "CHECK_LOADS", "route_edges"]

#: A simple path from the depot to the demand site, chosen over the links
#: datalog derived as open. Standard edge-selection encoding: pick undirected
#: edges, constrain degrees (1 at each endpoint, 0 or 2 elsewhere), and require
#: every chosen edge to be connected to the depot -- without that last
#: constraint the answer sets include a path plus arbitrary disjoint cycles.
ROUTE_PROGRAM = """
region(V) :- type(V, "region").
edge(A, B) :- open(A, B), A < B.

{ use(A, B) } :- edge(A, B).

inc(V, A, B) :- use(A, B), V = A.
inc(V, A, B) :- use(A, B), V = B.
deg(V, N) :- region(V), N = #count { A, B : inc(V, A, B) }.

:- depot(V), deg(V, N), N != 1.
:- needs(V), deg(V, N), N != 1.
:- region(V), not depot(V), not needs(V), deg(V, N), N != 0, N != 2.

conn(V) :- depot(V).
conn(B) :- conn(A), use(A, B).
conn(A) :- conn(B), use(A, B).
:- use(A, B), not conn(A).

#show use/2.
"""


def route_edges(model: Iterable[str]) -> list[tuple[str, str]]:
    """``['use(region_0, region_3)', ...]`` -> the edge list of one route."""
    out = []
    for atom in model:
        if not atom.startswith("use("):
            continue
        a, _, b = atom[4:-1].partition(", ")
        out.append((a.strip(), b.strip()))
    return sorted(out)


def _limits(world: WorldSnapshot) -> dict[tuple[str, str], float]:
    """``(a, b) -> posted limit in kg``, read from the world's Quantity claims.

    These are exactly the claims the relational projection discards, which is
    why this reads the world directly rather than asking datalog or ASP.
    """
    span: dict[str, tuple[str, str]] = {}
    for c in world.claims:
        if c.predicate == "bridge_on":
            a, b, via = (c.roles["a"].id, c.roles["b"].id, c.roles["via"].id)
            span[via] = tuple(sorted((a, b)))
    out: dict[tuple[str, str], float] = {}
    for c in world.claims:
        if c.predicate == "load_limit" and isinstance(c.roles.get("value"),
                                                      Quantity):
            bid = c.roles["of"].id
            if bid in span:
                out[span[bid]] = c.roles["value"].value
    return out


def _fleet(world: WorldSnapshot) -> dict[str, dict[str, Quantity]]:
    out: dict[str, dict[str, Quantity]] = {}
    for c in world.claims:
        if c.predicate in ("mass", "capacity") and isinstance(
                c.roles.get("value"), Quantity):
            out.setdefault(c.roles["of"].id, {})[c.predicate] = c.roles["value"]
    return {k: v for k, v in out.items() if {"mass", "capacity"} <= set(v)}


def _demand(world: WorldSnapshot) -> Quantity | None:
    for c in world.claims:
        if c.predicate == "demand" and isinstance(c.roles.get("value"), Quantity):
            return c.roles["value"]
    return None


def _check_loads(inputs: Mapping[str, Artifact], params: Mapping[str, Any],
                 ctx) -> dict[str, Artifact]:
    """For each candidate route and vehicle, ask SMT whether the load clears.

    A composite node: it calls one kernel many times rather than being one
    kernel. That is legal and is the honest shape here — the alternative is a
    fold whose state is a cross product, which would be the same loop wearing a
    container's clothes.

    The quantifier matters and is the thing a single-kernel answer gets wrong:
    a vehicle qualifies if **some** route admits it, not if the shortest one
    does. The shortest route is frequently the one with the weak bridge.
    """
    world = read_world(inputs["world"])
    routes = [route_edges(m) for m in (inputs["routes"].value or {}).get(
        "artifacts", {}).get("models", [])]
    # Ablations. Each removes one kernel's contribution while leaving the graph
    # otherwise identical, so a drop in agreement is attributable to that
    # kernel and not to a different pipeline.
    if params.get("ignore_bridge_limits"):
        limits_off = True
    else:
        limits_off = False
    if params.get("first_route_only"):
        routes = routes[:1]
    limits, fleet, demand = _limits(world), _fleet(world), _demand(world)
    smt = get_kernel("smt@1")

    if demand is None or not fleet:
        return {"claims": claims_artifact((), "flood.check_loads@1"),
                "report": Artifact(type="json", value={
                    "refused": "the world states no demand or no fleet"})}

    per_vehicle: dict[str, list[dict[str, Any]]] = {}
    usd = 0.0
    for vid, q in sorted(fleet.items()):
        per_vehicle[vid] = []
        for i, route in enumerate(routes):
            on_route = ([] if limits_off
                        else [limits[e] for e in route if e in limits])
            constraints = [
                {"op": ">=", "args": [{"var": f"payload@{vid}"},
                                      {"q": {"value": demand.value,
                                             "unit": demand.unit}}]},
                {"op": "<=", "args": [{"var": f"payload@{vid}"},
                                      {"q": {"value": q["capacity"].value,
                                             "unit": q["capacity"].unit}}]},
            ]
            for limit in on_route:
                constraints.append({"op": "<=", "args": [
                    {"op": "+", "args": [{"var": f"mass@{vid}"},
                                         {"var": f"payload@{vid}"}]},
                    {"q": {"value": limit, "unit": "kg"}}]})
            request = KernelRequest(params={"constraints": constraints})
            projection = smt.project(world, request)
            result = smt.run(projection, request)
            usd += result.cost.usd or 0.0
            per_vehicle[vid].append({
                "route": i, "edges": route, "limits": on_route,
                "feasible": result.ok, "why": result.refused})
            if result.ok:
                break

    claims = []
    for vid, tries in sorted(per_vehicle.items()):
        feasible = any(t["feasible"] for t in tries)
        claims.append(Claim(
            "can_serve", {"vehicle": EntityRef(vid)},
            polarity="positive" if feasible else "negative",
            modality="asserted",
            provenance=Provenance(
                producer="flood.check_loads@1", inputs=("smt@1",),
                method="SMT over the laden mass on each candidate route; a "
                       "vehicle qualifies if SOME route admits it")))
    # A composite node prices itself from the kernels it called, not from its
    # own wall clock: the loop around them is free and the solver calls are not.
    ctx.cost_usd = usd
    return {
        "claims": claims_artifact(claims, "flood.check_loads@1"),
        "report": Artifact(type="json", value={
            "n_routes": len(routes), "per_vehicle": per_vehicle,
            "n_smt_calls": sum(len(v) for v in per_vehicle.values()),
            "usd": usd}),
    }


CHECK_LOADS = register_op(OpDef(
    id="flood.check_loads@1", fn=_check_loads, family="kernel",
    inputs=(Port("world", "world_snapshot"), Port("routes", "json")),
    outputs=(Port("claims", "claim_set"), Port("report", "json")),
    requires=("core.quantity",), provides=("logic.constraint",),
    # `ignore_bridge_limits` and `first_route_only` are ABLATION parameters and
    # exist so a control can remove one kernel's contribution while leaving the
    # graph otherwise identical -- a drop measured against a different pipeline
    # is attributable to nothing.
    doc="Ask SMT whether each vehicle's laden mass clears every bridge on some "
        "candidate route."))


# ---------------------------------------------------------------------------
# routing: skip what cannot change the answer
# ---------------------------------------------------------------------------
def _qualifying_laden(world: WorldSnapshot) -> list[float]:
    """Laden mass of every vehicle whose capacity clears the demand."""
    fleet, demand = _fleet(world), _demand(world)
    if demand is None:
        return []
    return [q["mass"].value + demand.value for q in fleet.values()
            if q["capacity"].value >= demand.value]


def needs_the_solvers(world: WorldSnapshot, reach: Iterable[Any]) -> tuple[bool, str]:
    """Whether the expensive path can still change the answer.

    Two gates, and both are **provably lossless** rather than heuristic — which
    is the only kind of routing worth doing before there is a utility model to
    trade against:

    * the demand site is not reachable from the depot, so no vehicle can serve
      it whatever the loads are;
    * every capacity-qualifying vehicle's laden mass clears the *lightest*
      posted limit, so no bridge can bind and the answer is capacity alone.

    Both are arithmetic over facts already on the table. Neither needs a solver,
    and that is the point: the cheap check has to be cheaper than the thing it
    is deciding whether to run, or routing costs more than it saves.
    """
    depot = next((c.roles["where"].id for c in world.claims
                  if c.predicate == "depot"), None)
    site = next((c.roles["where"].id for c in world.claims
                 if c.predicate == "needs"), None)
    reachable = {(c.roles.get("a"), c.roles.get("b")) for c in reach
                 if getattr(c, "predicate", "") == "reach"}
    pairs = {(getattr(a, "id", a), getattr(b, "id", b)) for a, b in reachable}
    if depot is not None and site is not None and (depot, site) not in pairs:
        return False, ("the demand site is not reachable from the depot, so no "
                       "vehicle can serve it whatever the loads are")

    limits = _limits(world)
    laden = _qualifying_laden(world)
    if limits and laden and max(laden) <= min(limits.values()):
        return False, (f"every qualifying vehicle's laden mass "
                       f"({max(laden):g} kg) clears the lightest posted limit "
                       f"({min(limits.values()):g} kg), so no bridge can bind")
    return True, ""


def _demand_is_reachable(world: WorldSnapshot) -> bool:
    """Whether datalog's derived closure connects the depot to the demand site.

    Reads the `reach` claims already applied to this world rather than
    recomputing them: a cheap arm that redid the closure would not be cheap.
    """
    depot = next((c.roles["where"].id for c in world.claims
                  if c.predicate == "depot"), None)
    site = next((c.roles["where"].id for c in world.claims
                 if c.predicate == "needs"), None)
    if depot is None or site is None:
        return False
    for c in world.claims:
        if c.predicate != "reach":
            continue
        a, b = c.roles.get("a"), c.roles.get("b")
        if getattr(a, "id", a) == depot and getattr(b, "id", b) == site:
            return True
    return False


def _capacity_only(inputs: Mapping[str, Artifact], params: Mapping[str, Any],
                   ctx) -> dict[str, Artifact]:
    """The cheap answer: capacity against demand, no routing and no loads.

    Correct **only** where :func:`needs_the_solvers` said the expensive path
    could not change it. Used unconditionally it scores 0.410 against a 0.440
    floor -- below it, which is the whole content of "cheap-and-incapable is not
    a point on the cost curve".
    """
    world = read_world(inputs["world"])
    fleet, demand = _fleet(world), _demand(world)
    # Reachability is read from the world this node was handed, NOT from a
    # parameter. The first version took `params.get("reachable", True)`, the
    # node carried no params, and so the cheap arm answered "capacity clears it"
    # on every unreachable world -- 39 wrong answers in 300, on a path whose
    # docstring called itself provably lossless. The gate binds this input to
    # the post-datalog world, so the `reach` claims are already here; asking for
    # them is both correct and free.
    reachable = _demand_is_reachable(world)
    claims = []
    for vid, q in sorted(fleet.items()):
        ok = reachable and demand is not None and \
            q["capacity"].value >= demand.value
        claims.append(Claim(
            "can_serve", {"vehicle": EntityRef(vid)},
            polarity="positive" if ok else "negative", modality="asserted",
            provenance=Provenance(
                producer="flood.capacity_only@1",
                method="capacity against demand; no routing, no load check")))
    return {"claims": claims_artifact(claims, "flood.capacity_only@1"),
            "report": Artifact(type="json", value={"cheap": True,
                                                   "reachable": reachable})}


CAPACITY_ONLY = register_op(OpDef(
    id="flood.capacity_only@1", fn=_capacity_only, family="kernel",
    inputs=(Port("world", "world_snapshot"),),
    outputs=(Port("claims", "claim_set"), Port("report", "json")),
    doc="Capacity against demand alone. The cheap arm of the escalation."))
