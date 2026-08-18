"""Where the loops live, so the outer graph never has one.

The flow graph is a DAG. Simulation steps, fixed points, search, retries, agent
turns and recurrence are all real and all need a cycle — so they get one *inside*
a container node. From outside, ``fold`` is a single node with a state in and a
state out; from inside, it runs its body subgraph until a horizon or a
convergence test says stop.

That split is what buys everything else. The outer graph stays topologically
sortable, structurally hashable and cacheable however many iterations happen
underneath, and a reader of the graph can see *that* there is a loop and where
its state enters and leaves, which is exactly what an implicit back-edge hides.

``fold`` is the only container implemented here. ``fixed_point`` and
``event_loop`` are named in the architecture note and are deliberately absent:
a container with no consumer is a speculative feature, and this one has a test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..artifact.value import Artifact
from .flow_graph import FlowGraph
from .port import Binding, Port
from .registry import OpDef, register_op

__all__ = ["FoldSpec", "FOLD_OP"]


@dataclass(frozen=True)
class FoldSpec:
    """How a ``fold`` node runs its body.

    ``state_in`` is the body input port the running state is bound to, and
    ``state_out`` is the body *output name* the next state is read from. Both are
    named rather than positional because a body with one input today has three
    tomorrow, and a positional convention is how the state silently becomes the
    first argument of something else.
    """

    body: FlowGraph
    state_in: str
    state_out: str
    steps: int = 1
    stop_when_unchanged: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"body": self.body.to_dict(), "state_in": self.state_in,
                "state_out": self.state_out, "steps": self.steps,
                "stop_when_unchanged": self.stop_when_unchanged}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "FoldSpec":
        return cls(body=FlowGraph.from_dict(d["body"]), state_in=d["state_in"],
                   state_out=d["state_out"], steps=int(d.get("steps", 1)),
                   stop_when_unchanged=bool(d.get("stop_when_unchanged", True)))


def _fold(inputs: Mapping[str, Artifact], params: Mapping[str, Any],
          ctx: Any) -> dict[str, Artifact]:
    """Run the body subgraph ``steps`` times, threading the state through.

    Convergence is decided on the **artifact id**, which is a content hash — so
    "unchanged" means the bytes are identical, not that some tolerance was met.
    A tolerance-based fixed point is a different container and should say so in
    its name.
    """
    from .evaluate import evaluate

    spec = params["spec"]
    if not isinstance(spec, FoldSpec):
        spec = FoldSpec.from_dict(spec)
    state = inputs["state"]
    steps_run = 0
    for _ in range(max(0, spec.steps)):
        body_in = _inject(spec.body, spec.state_in, state)
        outs, _ = evaluate(body_in, ctx=ctx)
        nxt = outs[spec.state_out]
        steps_run += 1
        if spec.stop_when_unchanged and nxt.id == state.id:
            state = nxt
            break
        state = nxt
    return {"state": state, "steps": Artifact(type="scalar", value=steps_run)}


def _inject(body: FlowGraph, node_id: str, state: Artifact) -> FlowGraph:
    """Replace the body's state source with a constant carrying ``state``.

    The body declares its state entry as a ``flow.const@1`` node; folding
    rewrites that node's parameter rather than the graph's shape, so every
    iteration compiles to the identical topology and the structural cache sees
    exactly one thing changing.
    """
    from dataclasses import replace as _replace

    nodes = []
    found = False
    for n in body.nodes:
        if n.id == node_id:
            found = True
            nodes.append(_replace(n, params={**n.params,
                                             "artifact": state.to_dict()}))
        else:
            nodes.append(n)
    if not found:
        raise KeyError(f"fold body has no node {node_id!r} to bind its state to")
    return body.with_nodes(nodes)


FOLD_OP = register_op(OpDef(
    id="flow.fold@1", fn=_fold, family="container",
    inputs=(Port("state", "any"),),
    outputs=(Port("state", "any"), Port("steps", "scalar")),
    doc="Run a body subgraph until a horizon or a fixed point, keeping the "
        "outer graph acyclic."))
