"""Type-check the bindings, refuse the cycles, and put the nodes in order.

Everything here happens **before** anything runs, which is the point of having a
compile step at all: a graph that will fail on its ninth node should say so
before its first one costs anything.

Three classes of error are caught, and each is one this substrate would
otherwise discover expensively at runtime:

* a binding to a node or port that does not exist;
* a port type mismatch (``term_graph`` plugged into a ``world_snapshot``);
* a **cycle**, which is the invariant the whole flow layer rests on. Recurrence
  is legal and lives inside a container node — see :mod:`.container` — so a cycle
  in the outer graph is always a mistake and never a loop somebody meant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .flow_graph import FlowGraph, Node
from .port import compatible
from .registry import OpDef, get_op

__all__ = ["FlowError", "CompiledFlow", "compile_flow"]


class FlowError(ValueError):
    """A graph that cannot be run, with the reason stated at compile time."""


@dataclass(frozen=True)
class CompiledFlow:
    graph: FlowGraph
    order: tuple[str, ...]
    ops: Mapping[str, OpDef]

    def node(self, node_id: str) -> Node:
        return self.graph.node(node_id)

    def outputs_of(self) -> tuple[tuple[str, Any], ...]:
        """``(name, binding)`` for every terminal, in a stable order."""
        return tuple(sorted(self.graph.outputs.items()))


def compile_flow(graph: FlowGraph) -> CompiledFlow:
    ops: dict[str, OpDef] = {}
    for n in graph.nodes:
        try:
            ops[n.id] = get_op(n.op)
        except KeyError as e:
            raise FlowError(str(e)) from None

    by_id = {n.id: n for n in graph.nodes}
    for n in graph.nodes:
        defn = ops[n.id]
        for port_name, binding in n.inputs.items():
            try:
                want = defn.input(port_name)
            except KeyError as e:
                raise FlowError(f"node {n.id}: {e}") from None
            if binding.node not in by_id:
                raise FlowError(f"node {n.id}: input {port_name!r} is bound to "
                                f"node {binding.node!r}, which does not exist")
            up = ops[binding.node]
            try:
                give = up.output(binding.port)
            except KeyError as e:
                raise FlowError(f"node {n.id}: input {port_name!r} is bound to "
                                f"{binding.node}.{binding.port} -- {e}") from None
            if not compatible(want.type, give.type):
                raise FlowError(
                    f"node {n.id}: input {port_name!r} wants {want.type!r} but "
                    f"{binding.node}.{binding.port} produces {give.type!r}. Add "
                    f"an explicit conversion node -- an edge that converts is "
                    f"logic nobody can see in the trace.")
        missing = [p.name for p in defn.inputs
                   if p.required and p.name not in n.inputs]
        if missing:
            raise FlowError(f"node {n.id} ({n.op}): required input(s) {missing} "
                            f"are not bound")

    for name, b in graph.outputs.items():
        if b.node not in by_id:
            raise FlowError(f"output {name!r} names node {b.node!r}, which does "
                            f"not exist")
        ops[b.node].output(b.port)

    return CompiledFlow(graph=graph, order=_topological(graph), ops=ops)


def _topological(graph: FlowGraph) -> tuple[str, ...]:
    """Kahn's algorithm. What is left over when it stalls **is** the cycle.

    Reporting the members rather than "there is a cycle" matters: a flow graph
    is edited in a canvas, and "somewhere in these 40 nodes" is not actionable.
    """
    deps = {n.id: {b.node for b in n.inputs.values()} for n in graph.nodes}
    order: list[str] = []
    ready = sorted(nid for nid, d in deps.items() if not d)
    remaining = dict(deps)
    while ready:
        nid = ready.pop(0)
        order.append(nid)
        remaining.pop(nid, None)
        newly = sorted(k for k, d in remaining.items()
                       if nid in d and d <= set(order))
        ready.extend(n for n in newly if n not in ready)
    if remaining:
        raise FlowError(
            f"cycle in the flow graph among {sorted(remaining)}. The outer graph "
            f"is a DAG by construction; recurrence belongs inside a container "
            f"node (fold / fixed_point / event_loop), which keeps the outer "
            f"graph compilable while the iteration happens underneath.")
    return tuple(order)
