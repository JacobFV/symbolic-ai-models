"""The flow graph itself: one DAG, three kernels, two couplings, one answer.

This is the shape the whole substrate was built for, and it is deliberately
assembled from parts that know nothing about flood logistics: ``kernel.run@1``
names a kernel by id, ``world.apply_delta@1`` reconciles, ``world.fuse@1``
combines. Only :mod:`symbolic_ai_generators.flood.ops` knows what a bridge is.
"""

from __future__ import annotations

from typing import Any

from symbolic_ai_core.artifact.value import Artifact
from symbolic_ai_core.flow import Binding, Context, FlowGraph, Node, evaluate
from symbolic_ai_core.flow import ops as _flow_ops           # flow.const@1
from symbolic_ai_core.world import WorldSnapshot
from symbolic_ai_kernels import flow_ops as _kernel_ops      # kernel.run@1
from symbolic_ai_kernels.flow_ops import world_artifact

from . import ops as _flood_ops                              # flood.check_loads@1
from . import routing as _flood_routing                      # the gate policy
from .world import reach_rules

assert _flood_routing

assert _flow_ops and _kernel_ops and _flood_ops

__all__ = ["build_flow", "build_routed_flow", "solve"]


def build_routed_flow(world: WorldSnapshot, *, max_routes: int = 32
                      ) -> FlowGraph:
    """The same task, with the expensive path gated by two lossless checks.

    Escalation, in the architecture note's sense: the cheap arm answers when it
    is *provably* sufficient, and the solvers run otherwise. The gate itself is
    arithmetic over facts already on the table -- it has to be cheaper than the
    thing it is deciding whether to run, or routing costs more than it saves.

    Both branches produce a `claim_set`, and `flow.choose@1` takes the first
    present one in a named order. The unselected branch's nodes are skipped with
    the gate's reason in the trace, which is what makes the saving auditable
    rather than asserted.
    """
    from .ops import ROUTE_PROGRAM

    return FlowGraph(nodes=(
        Node(id="world", op="flow.const@1",
             params={"artifact": world_artifact(world)}),
        Node(id="reach", op="kernel.run@1",
             params={"kernel": "datalog@1",
                     "request": {"rules": reach_rules(),
                                 "role_names": {"open": ["a", "b"],
                                                "reach": ["a", "b"]}}},
             inputs={"world": Binding("world", "out")}),
        Node(id="world2", op="world.apply_delta@1",
             inputs={"world": Binding("world", "out"),
                     "delta": Binding("reach", "delta")}),

        Node(id="gate", op="flow.route@1",
             params={"branches": ["full", "cheap"], "policy": "flood_escalate"},
             inputs={"in": Binding("world2", "world"),
                     "aux": Binding("reach", "claims")}),

        # the expensive arm
        Node(id="routes", op="kernel.run@1",
             params={"kernel": "asp@1",
                     "request": {"program": ROUTE_PROGRAM,
                                 "max_models": max_routes}},
             inputs={"world": Binding("gate", "a")}),
        Node(id="loads", op="flood.check_loads@1",
             inputs={"world": Binding("gate", "a"),
                     "routes": Binding("routes", "report")}),

        # the cheap arm
        Node(id="cheap", op="flood.capacity_only@1",
             inputs={"world": Binding("gate", "b")}),

        Node(id="answer", op="flow.choose@1",
             params={"order": ["a", "b"]},
             inputs={"a": Binding("loads", "claims"),
                     "b": Binding("cheap", "claims")}),
    ), outputs={
        "loads": Binding("answer", "out"),
        "picked": Binding("answer", "picked"),
        "decision": Binding("gate", "decision"),
        "reach": Binding("reach", "claims"),
    })


def build_flow(world: WorldSnapshot, *, max_routes: int = 32,
               ignore_flooding: bool = False,
               ignore_bridge_limits: bool = False,
               first_route_only: bool = False) -> FlowGraph:
    """The graph. Acyclic, even though the world it reasons about is not.

    The three keyword flags are **ablations**, not options. Each removes one
    kernel's contribution while leaving every other node identical, so the drop
    in agreement with the brute-force oracle is attributable to that kernel.
    ``ignore_flooding`` routes over raw ``link`` facts instead of the ``open``
    relation datalog derived; ``ignore_bridge_limits`` drops the SMT load
    constraints; ``first_route_only`` keeps just the first candidate route,
    which is the mistake a single-shot planner makes.
    """
    from .ops import ROUTE_PROGRAM

    program = (ROUTE_PROGRAM.replace("edge(A, B) :- open(A, B), A < B.",
                                     "edge(A, B) :- link(A, B), A < B.")
               if ignore_flooding else ROUTE_PROGRAM)

    return FlowGraph(nodes=(
        Node(id="world", op="flow.const@1",
             params={"artifact": world_artifact(world)}),

        # 1. relational closure over a cyclic network. Datalog's job.
        Node(id="reach", op="kernel.run@1",
             params={"kernel": "datalog@1",
                     "request": {"rules": reach_rules(),
                                 "role_names": {"open": ["a", "b"],
                                                "reach": ["a", "b"]}}},
             inputs={"world": Binding("world", "out")}),

        # 2. the derived facts become part of the world the next kernel sees.
        Node(id="world2", op="world.apply_delta@1",
             inputs={"world": Binding("world", "out"),
                     "delta": Binding("reach", "delta")}),

        # 3. COUPLING 1: the completion space is built from `open`, which only
        #    step 1 could compute.
        Node(id="routes", op="kernel.run@1",
             params={"kernel": "asp@1",
                     "request": {"program": program,
                                 "max_models": max_routes}},
             inputs={"world": Binding("world2", "world")}),

        # 4. COUPLING 2: the constraints are built from those routes, over the
        #    Quantity claims the relational projection discarded.
        Node(id="loads", op="flood.check_loads@1",
             params={"ignore_bridge_limits": ignore_bridge_limits,
                     "first_route_only": first_route_only},
             inputs={"world": Binding("world", "out"),
                     "routes": Binding("routes", "report")}),

        # 5. one world out of three kernels' claims.
        Node(id="fused", op="world.fuse@1",
             params={"authority_from_kernels": ["smt@1"]},
             inputs={"a": Binding("reach", "claims"),
                     "b": Binding("routes", "claims"),
                     "c": Binding("loads", "claims")}),
    ), outputs={
        "reach": Binding("reach", "claims"),
        "routes": Binding("routes", "report"),
        "loads": Binding("loads", "claims"),
        "load_report": Binding("loads", "report"),
        "fused": Binding("fused", "claims"),
        "unresolved": Binding("fused", "unresolved"),
        "projection_datalog": Binding("reach", "projection"),
        "projection_asp": Binding("routes", "projection"),
    })


def solve(world: WorldSnapshot, *, max_routes: int = 32,
          ctx: Context | None = None, routed: bool = False,
          **ablations: bool) -> tuple[tuple[str, ...], dict[str, Any], Context]:
    """Run the graph and read the answer out. ``(vehicles, outputs, context)``."""
    graph = (build_routed_flow(world, max_routes=max_routes) if routed
             else build_flow(world, max_routes=max_routes, **ablations))
    outs, ctx = evaluate(graph, ctx=ctx or Context())
    can = tuple(sorted(
        c["roles"]["vehicle"]["entity"]
        for c in outs["loads"].value["claims"]
        if c["polarity"] == "positive"))
    return can, outs, ctx
