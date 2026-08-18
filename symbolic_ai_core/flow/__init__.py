"""The executable half: operations, typed bindings, and an acyclic outer graph.

A ``flow_graph`` is **not** a world, a term graph, a knowledge graph or an
autograd graph. It is a program: nodes are operations, edges bind one node's
output port to another node's input port, and the whole thing is acyclic so it
can be compiled, cached and reasoned about. Recurrence — loops, fixed points,
search, retries, agents, simulation steps — lives *inside* a container node, so
the outer graph stays a DAG however much iteration happens underneath.

Edges are deliberately boring. A binding says "this input is that output" and
nothing else. When a connection needs semantics — a unit conversion, a frame
transform, a resample, a coupling gain — it becomes a **node**, because hidden
logic on an edge is logic nobody can see in the trace.
"""

from __future__ import annotations

from .port import Binding, Port
from .registry import OpDef, OP_REGISTRY, op, register_op
from .flow_graph import FlowGraph, Node
from .compile import CompiledFlow, FlowError, compile_flow
from .evaluate import Context, NodeRun, Trace, evaluate
from .container import FoldSpec

__all__ = ["Binding", "Port", "OpDef", "OP_REGISTRY", "op", "register_op",
           "FlowGraph", "Node", "CompiledFlow", "FlowError", "compile_flow",
           "Context", "NodeRun", "Trace", "evaluate", "FoldSpec"]
