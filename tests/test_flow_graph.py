"""The executable half: acyclic, typed, cached, and unable to lie in its trace.

Every test here corresponds to an invariant in
``notes/decisions/2026-08-18-flow-is-a-dag-the-world-is-not.md``. They are
structural rather than numerical on purpose — these are the properties that make
a *number* produced by a flow graph mean anything, and they are cheap enough to
run on every commit that touches the runtime.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from symbolic_ai_core.artifact import Artifact
from symbolic_ai_core.flow import (Binding, Context, FlowError, FlowGraph, Node,
                                   OpDef, Port, compile_flow, evaluate,
                                   register_op)
from symbolic_ai_core.flow import ops as _ops   # registers flow.const@1 etc.
from symbolic_ai_core.flow import container as _container   # flow.fold@1

assert _ops and _container


# --- test ops, registered once at import ----------------------------------
def _double(inputs, params, ctx):
    a = inputs["in"]
    return {"out": replace(a, value=a.value * 2)}


def _add_one(inputs, params, ctx):
    a = inputs["in"]
    ctx.cost_usd = 0.5                      # a node prices itself
    return {"out": replace(a, value=a.value + 1)}


def _mutate(inputs, params, ctx):
    """Tries to mutate its input. Must be unable to."""
    a = inputs["in"]
    with pytest.raises(Exception):
        a.value = 99                        # frozen dataclass
    return {"out": a}


def _wrong_type(inputs, params, ctx):
    return {"out": Artifact(type="text", value="nope")}


register_op(OpDef(id="test.double@1", fn=_double, inputs=(Port("in", "scalar"),),
                  outputs=(Port("out", "scalar"),)))
register_op(OpDef(id="test.add_one@1", fn=_add_one,
                  inputs=(Port("in", "scalar"),), outputs=(Port("out", "scalar"),)))
register_op(OpDef(id="test.mutate@1", fn=_mutate, inputs=(Port("in", "scalar"),),
                  outputs=(Port("out", "scalar"),)))
register_op(OpDef(id="test.wrong_type@1", fn=_wrong_type,
                  inputs=(Port("in", "scalar"),),
                  outputs=(Port("out", "scalar"),)))
register_op(OpDef(id="test.metres@1", fn=_double,
                  inputs=(Port("in", "scalar", unit="m"),),
                  outputs=(Port("out", "scalar", unit="m"),)))
register_op(OpDef(id="test.ecef@1", fn=_double,
                  inputs=(Port("in", "scalar", frame="epsg:4978"),),
                  outputs=(Port("out", "scalar", frame="epsg:4978"),)))
register_op(OpDef(id="test.needs_geo@1", fn=_double,
                  inputs=(Port("in", "scalar", profiles=("geo.place",)),),
                  outputs=(Port("out", "scalar"),)))


def const_node(nid: str, value, **kw) -> Node:
    return Node(id=nid, op="flow.const@1",
                params={"artifact": Artifact(type="scalar", value=value, **kw)})


def chain(*, n_doubles: int = 1, start: int = 3) -> FlowGraph:
    nodes = [const_node("src", start)]
    prev = "src"
    for i in range(n_doubles):
        nodes.append(Node(id=f"d{i}", op="test.double@1",
                          inputs={"in": Binding(prev, "out")}))
        prev = f"d{i}"
    return FlowGraph(nodes=tuple(nodes), outputs={"out": Binding(prev, "out")})


# --- the invariants -------------------------------------------------------
def test_a_flow_graph_runs():
    outs, ctx = evaluate(chain(n_doubles=2, start=3))
    assert outs["out"].value == 12
    assert [r.node for r in ctx.trace.runs] == ["src", "d0", "d1"]


def test_flow_graph_rejects_cycles():
    """The outer graph is a DAG. Recurrence belongs in a container."""
    g = FlowGraph(nodes=(
        Node(id="a", op="test.double@1", inputs={"in": Binding("b", "out")}),
        Node(id="b", op="test.double@1", inputs={"in": Binding("a", "out")}),
    ))
    with pytest.raises(FlowError, match="cycle"):
        compile_flow(g)


def test_the_cycle_error_names_its_members():
    g = FlowGraph(nodes=(
        Node(id="a", op="test.double@1", inputs={"in": Binding("b", "out")}),
        Node(id="b", op="test.double@1", inputs={"in": Binding("a", "out")}),
        const_node("unrelated", 1),
    ))
    with pytest.raises(FlowError) as e:
        compile_flow(g)
    assert "'a'" in str(e.value) and "'b'" in str(e.value)
    assert "unrelated" not in str(e.value)


def test_port_types_are_checked_at_compile_time():
    """Before anything runs, and therefore before anything costs."""
    register_op(OpDef(id="test.text_source@1",
                      fn=lambda i, p, c: {"out": Artifact(type="text", value="x")},
                      outputs=(Port("out", "text"),)))
    g = FlowGraph(nodes=(
        Node(id="s", op="test.text_source@1"),
        Node(id="d", op="test.double@1", inputs={"in": Binding("s", "out")}),
    ))
    with pytest.raises(FlowError, match="wants 'scalar'"):
        compile_flow(g)


def test_an_op_cannot_return_a_type_it_did_not_declare():
    g = FlowGraph(nodes=(const_node("src", 1),
                         Node(id="w", op="test.wrong_type@1",
                              inputs={"in": Binding("src", "out")})),
                  outputs={"out": Binding("w", "out")})
    with pytest.raises(FlowError, match="port declares type"):
        evaluate(g)


def test_units_are_checked():
    g = FlowGraph(nodes=(const_node("src", 1.0, unit="ft"),
                         Node(id="m", op="test.metres@1",
                              inputs={"in": Binding("src", "out")})),
                  outputs={"out": Binding("m", "out")})
    with pytest.raises(FlowError, match="unit 'm'"):
        evaluate(g)


def test_frames_are_checked():
    g = FlowGraph(nodes=(const_node("src", 1.0, frame="epsg:4326"),
                         Node(id="f", op="test.ecef@1",
                              inputs={"in": Binding("src", "out")})),
                  outputs={"out": Binding("f", "out")})
    with pytest.raises(FlowError, match="frame 'epsg:4978'"):
        evaluate(g)


def test_required_profiles_are_checked():
    g = FlowGraph(nodes=(const_node("src", 1.0, profiles=("logic.term",)),
                         Node(id="g", op="test.needs_geo@1",
                              inputs={"in": Binding("src", "out")})),
                  outputs={"out": Binding("g", "out")})
    with pytest.raises(FlowError, match="geo.place"):
        evaluate(g)


def test_an_explicit_conversion_node_is_the_legal_way_through():
    """The type checker refuses an implicit conversion and leaves this open."""
    g = FlowGraph(nodes=(
        const_node("src", 3.0, unit="ft"),
        Node(id="cv", op="flow.convert_unit@1",
             params={"factor": 0.3048, "to": "m"},
             inputs={"in": Binding("src", "out")}),
        Node(id="m", op="test.metres@1", inputs={"in": Binding("cv", "out")}),
    ), outputs={"out": Binding("m", "out")})
    outs, _ = evaluate(g)
    assert outs["out"].unit == "m"
    assert outs["out"].value == pytest.approx(3.0 * 0.3048 * 2)


def test_kernel_cannot_mutate_input():
    g = FlowGraph(nodes=(const_node("src", 1),
                         Node(id="m", op="test.mutate@1",
                              inputs={"in": Binding("src", "out")})),
                  outputs={"out": Binding("m", "out")})
    outs, _ = evaluate(g)
    assert outs["out"].value == 1


def test_cache_is_semantically_inert():
    """Same graph, cache emptied between runs, identical artifact ids."""
    g = chain(n_doubles=3, start=5)
    warm, ctx1 = evaluate(g, ctx=Context())
    cold, ctx2 = evaluate(g, ctx=Context(use_cache=False))
    assert warm["out"].id == cold["out"].id
    assert warm["out"].value == cold["out"].value


def test_only_downstream_of_a_change_recomputes():
    ctx = Context()
    evaluate(chain(n_doubles=3, start=5), ctx=ctx)
    ctx.trace.runs.clear()
    evaluate(chain(n_doubles=3, start=5), ctx=ctx)
    assert all(r.cached for r in ctx.trace.runs), "an unchanged graph re-ran"

    ctx.trace.runs.clear()
    evaluate(chain(n_doubles=3, start=6), ctx=ctx)   # only the source changed
    assert not any(r.cached for r in ctx.trace.runs), (
        "a changed source did not invalidate its downstream")


def test_two_nodes_computing_the_same_thing_share_one_cache_entry():
    """The key is the computation, not the node. Content addressing earns this."""
    ctx = Context()
    g = FlowGraph(nodes=(const_node("src", 4),
                         Node(id="a", op="test.double@1",
                              inputs={"in": Binding("src", "out")}),
                         Node(id="b", op="test.double@1",
                              inputs={"in": Binding("src", "out")})),
                  outputs={"a": Binding("a", "out"), "b": Binding("b", "out")})
    outs, ctx = evaluate(g, ctx=ctx)
    assert outs["a"].id == outs["b"].id
    cached = [r.node for r in ctx.trace.runs if r.cached]
    assert cached == ["b"]


def test_a_disabled_node_makes_its_downstream_absent_rather_than_failing():
    g = FlowGraph(nodes=(
        const_node("src", 1),
        Node(id="d", op="test.double@1", inputs={"in": Binding("src", "out")},
             disabled=True),
        Node(id="e", op="test.double@1", inputs={"in": Binding("d", "out")}),
    ), outputs={"out": Binding("e", "out")})
    outs, ctx = evaluate(g)
    assert outs["out"].present is False
    assert "disabled" in outs["out"].meta["absent_because"]
    assert all(r.skipped for r in ctx.trace.runs if r.node in ("d", "e"))


def test_the_trace_counts_unpriced_nodes_rather_than_calling_them_free():
    g = FlowGraph(nodes=(const_node("src", 1),
                         Node(id="p", op="test.add_one@1",
                              inputs={"in": Binding("src", "out")}),
                         Node(id="u", op="test.double@1",
                              inputs={"in": Binding("p", "out")})),
                  outputs={"out": Binding("u", "out")})
    _, ctx = evaluate(g)
    assert ctx.trace.total_usd == 0.5
    assert ctx.trace.unpriced == 2, "a node that reported nothing read as free"


def test_the_graph_round_trips_through_json():
    g = chain(n_doubles=2)
    # The const node's params carry an Artifact object; the wire form is a dict.
    wire = FlowGraph(nodes=tuple(
        replace(n, params={"artifact": n.params["artifact"].to_dict()})
        if n.op == "flow.const@1" else n for n in g.nodes), outputs=g.outputs)
    back = FlowGraph.from_dict(wire.to_dict())
    outs, _ = evaluate(back)
    assert outs["out"].value == 12


def test_duplicate_node_ids_are_refused():
    with pytest.raises(ValueError, match="duplicate node id"):
        FlowGraph(nodes=(const_node("a", 1), const_node("a", 2)))


def test_registering_an_op_twice_is_refused():
    with pytest.raises(ValueError, match="already registered"):
        register_op(OpDef(id="test.double@1", fn=_double))


def test_an_unversioned_op_id_is_refused():
    with pytest.raises(ValueError, match="no version"):
        register_op(OpDef(id="test.unversioned", fn=_double))


# --- recurrence lives inside a container, not in the outer graph ----------
def test_container_encapsulates_recurrence():
    """The body iterates; the outer graph stays a DAG and stays cacheable."""
    from symbolic_ai_core.flow.container import FoldSpec

    body = FlowGraph(
        nodes=(Node(id="state", op="flow.const@1",
                    params={"artifact": Artifact(type="scalar", value=0)}),
               Node(id="step", op="test.add_one@1",
                    inputs={"in": Binding("state", "out")})),
        outputs={"next": Binding("step", "out")})
    spec = FoldSpec(body=body, state_in="state", state_out="next", steps=5)

    g = FlowGraph(nodes=(
        const_node("seed", 10),
        Node(id="loop", op="flow.fold@1", params={"spec": spec},
             inputs={"state": Binding("seed", "out")}),
    ), outputs={"out": Binding("loop", "state"),
                "steps": Binding("loop", "steps")})

    # the outer graph compiles, which it could not if the loop were an edge
    compiled = compile_flow(g)
    assert compiled.order == ("seed", "loop")

    outs, _ = evaluate(g)
    assert outs["out"].value == 15
    assert outs["steps"].value == 5


def test_a_fold_stops_at_a_fixed_point():
    """Convergence is decided on the content hash: unchanged means same bytes."""
    from symbolic_ai_core.flow.container import FoldSpec

    body = FlowGraph(
        nodes=(Node(id="state", op="flow.const@1",
                    params={"artifact": Artifact(type="scalar", value=0)}),
               Node(id="step", op="flow.identity@1",
                    inputs={"in": Binding("state", "out")})),
        outputs={"next": Binding("step", "out")})
    g = FlowGraph(nodes=(
        const_node("seed", 7),
        Node(id="loop", op="flow.fold@1",
             params={"spec": FoldSpec(body=body, state_in="state",
                                      state_out="next", steps=100)},
             inputs={"state": Binding("seed", "out")}),
    ), outputs={"out": Binding("loop", "state"),
                "steps": Binding("loop", "steps")})
    outs, _ = evaluate(g)
    assert outs["out"].value == 7
    assert outs["steps"].value == 1, "a fixed point should stop after one step"


def test_reframe_refuses_to_be_a_no_op():
    g = FlowGraph(nodes=(
        const_node("src", 1.0, frame="epsg:4978"),
        Node(id="r", op="flow.reframe@1", params={"to": "epsg:4978"},
             inputs={"in": Binding("src", "out")}),
    ), outputs={"out": Binding("r", "out")})
    with pytest.raises(ValueError, match="already in"):
        evaluate(g)
