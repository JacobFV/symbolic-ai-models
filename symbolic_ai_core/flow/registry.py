"""What operations exist. A domain registers definitions; the graph stays data.

The flow graph never subclasses anything and never imports a domain. A node
names an op by id, and this registry is the one place that turns an id into
something callable. That is the property that lets the same serialised graph be
executed here and edited in a TypeScript canvas that has never heard of Python.

Ids are versioned — ``language.semantic_parse@1`` — because a graph on disk
outlives the op that ran it, and a silently changed operation is a published
number that quietly means something else. Registering an existing id raises.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from ..artifact.value import Artifact
from .port import Port

__all__ = ["OpDef", "OP_REGISTRY", "register_op", "op", "get_op"]

#: ``(inputs, params, ctx) -> {port name: Artifact}``
OpFn = Callable[[Mapping[str, Artifact], Mapping[str, Any], Any],
                Mapping[str, Artifact]]


@dataclass(frozen=True)
class OpDef:
    """One operation's contract, independent of who calls it."""

    id: str
    fn: OpFn
    inputs: tuple[Port, ...] = ()
    outputs: tuple[Port, ...] = ()
    requires: tuple[str, ...] = ()      #: world profiles it needs
    provides: tuple[str, ...] = ()      #: world profiles it produces
    pure: bool = True
    deterministic: bool = True
    family: str = "transform"           #: source/parse/kernel/router/container/...
    doc: str = ""

    def input(self, name: str) -> Port:
        for p in self.inputs:
            if p.name == name:
                return p
        raise KeyError(f"op {self.id} has no input port {name!r}; "
                       f"has {[p.name for p in self.inputs]}")

    def output(self, name: str) -> Port:
        for p in self.outputs:
            if p.name == name:
                return p
        raise KeyError(f"op {self.id} has no output port {name!r}; "
                       f"has {[p.name for p in self.outputs]}")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "inputs": [p.to_dict() for p in self.inputs],
                "outputs": [p.to_dict() for p in self.outputs],
                "requires": list(self.requires), "provides": list(self.provides),
                "pure": self.pure, "deterministic": self.deterministic,
                "family": self.family, "doc": self.doc}


OP_REGISTRY: dict[str, OpDef] = {}


def register_op(defn: OpDef) -> OpDef:
    if defn.id in OP_REGISTRY:
        raise ValueError(
            f"op {defn.id} is already registered. Operations are versioned "
            f"(`name@2`) rather than redefined: a graph on disk outlives the op "
            f"that ran it, and redefining one silently changes what every "
            f"recorded run meant.")
    if "@" not in defn.id:
        raise ValueError(f"op id {defn.id!r} carries no version; use `{defn.id}@1`")
    OP_REGISTRY[defn.id] = defn
    return defn


def get_op(op_id: str) -> OpDef:
    try:
        return OP_REGISTRY[op_id]
    except KeyError:
        raise KeyError(f"unknown op {op_id!r}; registered: "
                       f"{sorted(OP_REGISTRY)}") from None


def op(op_id: str, *, inputs: tuple[Port, ...] = (),
       outputs: tuple[Port, ...] = (), **kw: Any) -> Callable[[OpFn], OpFn]:
    """Decorator form. The function keeps its identity so it stays testable."""

    def wrap(fn: OpFn) -> OpFn:
        register_op(OpDef(id=op_id, fn=fn, inputs=inputs, outputs=outputs,
                          doc=(fn.__doc__ or "").strip().split("\n")[0], **kw))
        return fn

    return wrap
