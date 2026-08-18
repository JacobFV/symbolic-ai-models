"""Routers decide which operations run; choosers decide which value continues.

Collapsing the two looks harmless and is not: a router that also picks a value
has to run every branch to have values to pick from, which is exactly the cost
the routing existed to avoid.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.artifact import Artifact
from symbolic_ai_core.flow import Binding, Context, FlowGraph, Node, evaluate
from symbolic_ai_core.flow import ops as _ops
from symbolic_ai_core.flow import router as _router
from symbolic_ai_core.flow.router import (ROUTER_POLICIES, register_policy,
                                          routing_report)

assert _ops and _router

register_policy("test_first_only", lambda i, p: [p["branches"][0]])
register_policy("test_none", lambda i, p: [])


def _expensive(inputs, params, ctx):
    """Burns measurable CPU, so a skipped branch is a saving rather than noise."""
    total = 0
    for i in range(params.get("work", 200_000)):
        total += i * i
    a = inputs["in"]
    from dataclasses import replace
    return {"out": replace(a, value=a.value + (total % 2))}


from symbolic_ai_core.flow import OpDef, Port, register_op  # noqa: E402

register_op(OpDef(id="test.expensive@1", fn=_expensive,
                  inputs=(Port("in", "scalar"),),
                  outputs=(Port("out", "scalar"),)))


def graph(policy: str) -> FlowGraph:
    return FlowGraph(nodes=(
        Node(id="src", op="flow.const@1",
             params={"artifact": Artifact(type="scalar", value=7)}),
        Node(id="r", op="flow.route@1",
             params={"branches": ["cheap", "exact"], "policy": policy},
             inputs={"in": Binding("src", "out")}),
        Node(id="cheap", op="flow.identity@1", inputs={"in": Binding("r", "a")}),
        Node(id="exact", op="flow.identity@1", inputs={"in": Binding("r", "b")}),
        Node(id="pick", op="flow.choose@1", params={"order": ["a", "b"]},
             inputs={"a": Binding("cheap", "out"), "b": Binding("exact", "out")}),
    ), outputs={"out": Binding("pick", "out"),
                "picked": Binding("pick", "picked"),
                "decision": Binding("r", "decision")})


def test_an_unselected_branch_is_skipped_not_run():
    outs, ctx = evaluate(graph("test_first_only"))
    assert outs["out"].value == 7 and outs["picked"].value == "a"
    skipped = {r.node for r in ctx.trace.runs if r.skipped}
    assert skipped == {"exact"}


def test_the_skip_carries_the_policy_and_its_choice():
    _, ctx = evaluate(graph("test_first_only"))
    note = next(r.note for r in ctx.trace.runs if r.node == "exact")
    assert "test_first_only" in note and "cheap" in note


def test_routing_all_branches_off_leaves_the_chooser_absent():
    outs, ctx = evaluate(graph("test_none"))
    assert outs["out"].present is False
    assert outs["picked"].value is None
    assert {"cheap", "exact"} <= {r.node for r in ctx.trace.runs if r.skipped}


def test_the_default_policy_runs_everything():
    outs, ctx = evaluate(graph("all"))
    assert not any(r.skipped for r in ctx.trace.runs)
    assert outs["picked"].value == "a", "choose order was not respected"


def test_the_chooser_order_is_explicit_not_dict_order():
    g = graph("all")
    flipped = FlowGraph(nodes=tuple(
        n if n.id != "pick" else Node(id="pick", op="flow.choose@1",
                                      params={"order": ["b", "a"]},
                                      inputs=n.inputs)
        for n in g.nodes), outputs=g.outputs)
    outs, _ = evaluate(flipped)
    assert outs["picked"].value == "b"


def test_an_unknown_policy_is_refused_by_name():
    with pytest.raises(KeyError, match="unknown routing policy"):
        evaluate(graph("no_such_policy"))


def test_a_policy_cannot_be_silently_replaced():
    with pytest.raises(ValueError, match="already registered"):
        register_policy("all", lambda i, p: [])


def test_more_branches_than_ports_is_refused():
    from symbolic_ai_core.flow.router import BRANCH_PORTS

    g = FlowGraph(nodes=(
        Node(id="src", op="flow.const@1",
             params={"artifact": Artifact(type="scalar", value=1)}),
        Node(id="r", op="flow.route@1",
             params={"branches": [f"b{i}" for i in range(len(BRANCH_PORTS) + 1)],
                     "policy": "all"},
             inputs={"in": Binding("src", "out")}),
    ), outputs={"d": Binding("r", "decision")})
    with pytest.raises(ValueError, match="chain two routers"):
        evaluate(g)


def costly_graph(policy: str) -> FlowGraph:
    """Same shape, but the branch that gets skipped actually costs something."""
    g = graph(policy)
    return FlowGraph(nodes=tuple(
        Node(id="exact", op="test.expensive@1", inputs=n.inputs)
        if n.id == "exact" else n for n in g.nodes), outputs=g.outputs)


def test_routing_report_computes_the_saving_from_the_traces():
    _, base = evaluate(costly_graph("all"), ctx=Context())
    _, routed = evaluate(costly_graph("test_first_only"), ctx=Context())
    rep = routing_report(base, routed)
    assert rep["routed"]["skipped"] == ["exact"]
    assert rep["usd_saved"] > 0
    assert 0 < rep["usd_saved_share"] < 1
    assert rep["decisions"][0]["chosen"] == ["cheap"]


def test_routing_a_trivially_cheap_branch_is_a_NET_LOSS():
    """The guard against routing everything. A gate is itself a node, and when
    what it gates costs less than the gate, the saving is negative -- measured
    here at about -4e-12 USD on two identity ops. Routing pays in proportion to
    what is downstream of it, and nothing else."""
    _, base = evaluate(graph("all"), ctx=Context())
    _, routed = evaluate(graph("test_first_only"), ctx=Context())
    rep = routing_report(base, routed)
    assert rep["routed"]["skipped"] == ["exact"]
    assert rep["usd_saved"] <= 0, (
        "routing two identity ops came out ahead; either the gate became free "
        "or the measurement is not measuring the gate")


def test_the_report_says_how_much_of_the_total_is_only_a_cpu_floor():
    """A saving computed against unpriced nodes is a saving of something nobody
    measured."""
    _, base = evaluate(costly_graph("all"), ctx=Context())
    _, routed = evaluate(costly_graph("test_first_only"), ctx=Context())
    rep = routing_report(base, routed)
    assert rep["routed"]["cpu_only"] >= 1
    assert rep["routed"]["unpriced"] == 0
