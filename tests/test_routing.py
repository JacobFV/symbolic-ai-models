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


def test_routing_a_trivially_cheap_branch_buys_essentially_nothing():
    """The guard against routing everything: a gate is itself a node, so when
    what it gates costs about what the gate costs, there is nothing to win.

    **This deliberately does not assert the sign of the saving.** An earlier
    version did -- `usd_saved <= 0`, from a measured -4e-12 USD -- and it passed
    inside its own file and failed 8/8 when run alone, because the difference is
    far smaller than process warm-up. Asserting the sign of a difference smaller
    than the measurement noise is not a test; it is a coin flip with a
    docstring.

    What is robust is the magnitude: whatever the sign, the saving is bounded by
    the cost of the node that was skipped, and that node is an identity op.
    """
    _, base = evaluate(graph("all"), ctx=Context())
    _, routed = evaluate(graph("test_first_only"), ctx=Context())
    rep = routing_report(base, routed)
    assert rep["routed"]["skipped"] == ["exact"]

    gate = next(r for r in routed.trace.runs if r.node == "r")
    assert gate.cost_usd is not None and gate.cost_usd > 0, (
        "the router node cost nothing, so there is nothing for it to fail to "
        "pay back")
    assert abs(rep["usd_saved"]) < 10 * gate.cost_usd, (
        "routing an identity op moved the total by more than ten times the "
        "gate's own cost, which would mean the saving is not coming from the "
        "skipped branch")


def test_routing_an_expensive_branch_is_a_clear_win():
    """The contrast, and the one whose sign IS above the noise."""
    _, base = evaluate(costly_graph("all"), ctx=Context())
    _, routed = evaluate(costly_graph("test_first_only"), ctx=Context())
    rep = routing_report(base, routed)
    assert rep["usd_saved"] > 0
    assert rep["usd_saved_share"] > 0.5, (
        "skipping the only expensive node saved less than half the total")


def test_the_report_says_how_much_of_the_total_is_only_a_cpu_floor():
    """A saving computed against unpriced nodes is a saving of something nobody
    measured."""
    _, base = evaluate(costly_graph("all"), ctx=Context())
    _, routed = evaluate(costly_graph("test_first_only"), ctx=Context())
    rep = routing_report(base, routed)
    assert rep["routed"]["cpu_only"] >= 1
    assert rep["routed"]["unpriced"] == 0
