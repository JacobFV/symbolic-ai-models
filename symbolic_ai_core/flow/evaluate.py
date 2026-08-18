"""Run a compiled flow, memoised on structural hash, with a trace and a cost.

**The cache key is the computation, not the node.** A node's result is keyed on
``(op id, params, the ids of its input artifacts)``, and an artifact's id is its
content. So changing one input recomputes exactly the nodes downstream of it and
nothing else, two nodes that happen to compute the same thing share one entry,
and a cache hit is a fact rather than a bet on an invalidation rule someone
remembered to write.

**A cache cannot change what a graph means.** Nothing in the key is time, order,
or identity of the caller; nothing in the value is recomputed differently on a
miss. ``test_cache_is_semantically_inert`` runs a graph twice, once with the
cache emptied between, and compares the artifact ids.

**Absence propagates, and it is not failure.** A disabled node produces absent
outputs; a node whose required input is absent is skipped and produces absent
outputs of its own. That is how a router turns a branch off without the branch
having to know, and it is why an absent artifact carries a reason.

Cost is accumulated per node and is the input to
:mod:`symbolic_ai_core.cost`, which is where ``$ / solved episode above floor``
is actually computed. A node that does not report its cost reports zero, and a
zero that means "not measured" is exactly the confusion this repo spent months
in — so ``Trace.unpriced`` counts them and the report says so.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..artifact.store import ArtifactStore, MemoryStore
from ..artifact.value import Artifact, Provenance, artifact_id, to_wire
from .compile import CompiledFlow, FlowError, compile_flow
from .flow_graph import FlowGraph
from .port import ANY, Port, compatible

__all__ = ["Context", "NodeRun", "Trace", "evaluate", "cache_key"]


def cache_key(op_id: str, params: Mapping[str, Any],
              input_ids: Mapping[str, str]) -> str:
    """The structural hash a node's result is memoised under."""
    return artifact_id({"op": op_id, "params": to_wire(dict(params)),
                        "inputs": dict(sorted(input_ids.items()))})


@dataclass
class NodeRun:
    """What one node did. The unit of the execution trace."""

    node: str
    op: str
    cached: bool
    skipped: bool
    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    wall_ns: int = 0
    cost_usd: float | None = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"node": self.node, "op": self.op, "cached": self.cached,
                "skipped": self.skipped, "inputs": self.inputs,
                "outputs": self.outputs, "wall_ns": self.wall_ns,
                "cost_usd": self.cost_usd, "note": self.note}


@dataclass
class Trace:
    """Every node run, in order. A lineage_trace, in the naming law's terms."""

    runs: list[NodeRun] = field(default_factory=list)

    @property
    def unpriced(self) -> int:
        """Nodes that reported no cost. **Not the same as nodes that were free.**"""
        return sum(1 for r in self.runs if r.cost_usd is None and not r.skipped)

    @property
    def total_usd(self) -> float:
        return sum(r.cost_usd or 0.0 for r in self.runs)

    def to_dict(self) -> dict[str, Any]:
        return {"runs": [r.to_dict() for r in self.runs],
                "unpriced": self.unpriced, "total_usd": self.total_usd}


@dataclass
class Context:
    """What a node is allowed to reach. Deliberately small.

    A node gets a store, a cache, a place to record cost and whatever the caller
    put in ``env``. It does not get the graph, its siblings, or a way to write
    to another node's output — a node that could reach those would be able to
    make the trace a fiction.
    """

    store: ArtifactStore = field(default_factory=MemoryStore)
    cache: dict[str, dict[str, str]] = field(default_factory=dict)
    trace: Trace = field(default_factory=Trace)
    env: dict[str, Any] = field(default_factory=dict)
    use_cache: bool = True
    cost_usd: float | None = None      #: a node sets this to price itself


def _check_port(port: Port, art: Artifact, *, where: str) -> None:
    if not art.present:
        return
    if not compatible(port.type, art.type):
        raise FlowError(f"{where}: port declares type {port.type!r} but the "
                        f"artifact is {art.type!r}")
    if port.unit and art.unit != port.unit:
        raise FlowError(
            f"{where}: port declares unit {port.unit!r} and the artifact is in "
            f"{art.unit or 'no stated unit'!r}. Convert with an explicit node; "
            f"an implicit conversion is how a metre meets a foot.")
    if port.frame and art.frame != port.frame:
        raise FlowError(
            f"{where}: port declares frame {port.frame!r} and the artifact is in "
            f"{art.frame or 'no stated frame'!r}. Reproject with an explicit node.")
    if port.profiles:
        missing = sorted(set(port.profiles) - set(art.profiles))
        if missing:
            raise FlowError(f"{where}: port requires profile(s) {missing}; the "
                            f"artifact carries {list(art.profiles)}")


def evaluate(graph: FlowGraph | CompiledFlow, *, ctx: Context | None = None,
             ) -> tuple[dict[str, Artifact], Context]:
    """Run to the named outputs. Returns ``(outputs, context)``.

    The context is returned rather than only the outputs because the trace and
    the cost ledger are the *other* half of a result here — a number without the
    record of what it cost to produce is the shape of claim this repo has
    already had to retract.
    """
    flow = graph if isinstance(graph, CompiledFlow) else compile_flow(graph)
    ctx = ctx or Context()
    produced: dict[str, dict[str, Artifact]] = {}

    for node_id in flow.order:
        node = flow.node(node_id)
        defn = flow.ops[node_id]
        inputs: dict[str, Artifact] = {}
        absent_because = ""
        for port_name, b in node.inputs.items():
            art = produced[b.node][b.port]
            _check_port(defn.input(port_name), art,
                        where=f"node {node_id} input {port_name!r}")
            if not art.present and defn.input(port_name).required:
                absent_because = (f"required input {port_name!r} is absent "
                                  f"({art.meta.get('absent_because', 'no reason given')})")
            inputs[port_name] = art

        if node.disabled or absent_because:
            why = "node disabled" if node.disabled else absent_because
            produced[node_id] = {p.name: Artifact.absent(p.type, why=why)
                                 for p in defn.outputs}
            ctx.trace.runs.append(NodeRun(node=node_id, op=node.op, cached=False,
                                          skipped=True, note=why))
            continue

        input_ids = {k: v.id for k, v in inputs.items()}
        key = cache_key(node.op, node.params, input_ids)
        hit = ctx.cache.get(key) if (ctx.use_cache and defn.pure) else None
        if hit is not None:
            outs = {k: ctx.store.get(v) for k, v in hit.items()}
            produced[node_id] = outs
            ctx.trace.runs.append(NodeRun(node=node_id, op=node.op, cached=True,
                                          skipped=False, inputs=input_ids,
                                          outputs=dict(hit)))
            continue

        ctx.cost_usd = None
        t0 = time.perf_counter_ns()
        raw = defn.fn(inputs, node.params, ctx)
        wall = time.perf_counter_ns() - t0
        outs = _finish(defn, node_id, raw, input_ids, ctx)
        produced[node_id] = outs
        out_ids = {k: ctx.store.put(v) for k, v in outs.items()}
        if ctx.use_cache and defn.pure:
            ctx.cache[key] = out_ids
        ctx.trace.runs.append(NodeRun(node=node_id, op=node.op, cached=False,
                                      skipped=False, inputs=input_ids,
                                      outputs=out_ids, wall_ns=wall,
                                      cost_usd=ctx.cost_usd))

    return ({name: produced[b.node][b.port]
             for name, b in flow.outputs_of()}, ctx)


def _finish(defn, node_id: str, raw: Mapping[str, Artifact],
            input_ids: Mapping[str, str], ctx: Context) -> dict[str, Artifact]:
    """Type-check what a node returned and stamp its provenance."""
    declared = {p.name for p in defn.outputs}
    extra = sorted(set(raw) - declared)
    if extra:
        raise FlowError(f"node {node_id} ({defn.id}) returned undeclared output "
                        f"port(s) {extra}; declared {sorted(declared)}")
    out: dict[str, Artifact] = {}
    for p in defn.outputs:
        art = raw.get(p.name)
        if art is None:
            if p.required:
                raise FlowError(f"node {node_id} ({defn.id}) declared required "
                                f"output {p.name!r} and returned nothing")
            art = Artifact.absent(p.type, why="op returned no value")
        _check_port(p, art, where=f"node {node_id} output {p.name!r}")
        out[p.name] = art.with_provenance(Provenance(
            producer=f"{node_id}:{defn.id}",
            inputs=tuple(sorted(input_ids.values())),
            method=art.provenance.method))
    return out
