"""The graph as **data**. No subclassing, no domain imports, no hidden state.

A ``FlowGraph`` is a list of nodes and a map of named outputs, and it serialises
to plain JSON. Every editor — including a canvas in another language — is a
projection of this, never a second source of truth.

The module is called ``flow_graph`` and not ``graph`` on purpose; see
``notes/decisions/2026-08-18-flow-is-a-dag-the-world-is-not.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping

from ..artifact.value import to_wire
from .port import Binding

__all__ = ["Node", "FlowGraph"]


@dataclass(frozen=True)
class Node:
    """One operation instance: which op, with what parameters, fed from where.

    ``disabled`` is not a comment. A disabled node still exists, still has its
    bindings, and still occupies its place in the topology — its outputs simply
    become *absent* artifacts, and absence propagates to whoever required them.
    That is what makes toggling one node a reversible experiment rather than an
    edit to the graph.
    """

    id: str
    op: str
    params: Mapping[str, Any] = field(default_factory=dict)
    inputs: Mapping[str, Binding] = field(default_factory=dict)
    disabled: bool = False
    meta: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "op": self.op, "params": to_wire(dict(self.params)),
                "inputs": {k: v.to_dict() for k, v in sorted(self.inputs.items())},
                "disabled": self.disabled, "meta": dict(self.meta)}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Node":
        return cls(id=d["id"], op=d["op"], params=dict(d.get("params") or {}),
                   inputs={k: Binding(**v)
                           for k, v in (d.get("inputs") or {}).items()},
                   disabled=bool(d.get("disabled", False)),
                   meta=dict(d.get("meta") or {}))


@dataclass(frozen=True)
class FlowGraph:
    """Nodes plus the terminals a caller actually wants back."""

    nodes: tuple[Node, ...] = ()
    outputs: Mapping[str, Binding] = field(default_factory=dict)
    meta: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for n in self.nodes:
            if n.id in seen:
                raise ValueError(f"duplicate node id {n.id!r}: a binding names a "
                                 f"node, so two nodes with one name is an "
                                 f"ambiguous edge, not a redefinition")
            seen.add(n.id)

    def node(self, node_id: str) -> Node:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(f"no node {node_id!r}; have {[n.id for n in self.nodes]}")

    def with_nodes(self, nodes: Iterable[Node]) -> "FlowGraph":
        return replace(self, nodes=tuple(nodes))

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": [n.to_dict() for n in self.nodes],
                "outputs": {k: v.to_dict() for k, v in sorted(self.outputs.items())},
                "meta": dict(self.meta)}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "FlowGraph":
        return cls(nodes=tuple(Node.from_dict(n) for n in d.get("nodes") or []),
                   outputs={k: Binding(**v)
                            for k, v in (d.get("outputs") or {}).items()},
                   meta=dict(d.get("meta") or {}))
