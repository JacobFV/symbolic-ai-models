"""Deciding **which** operations run, and **which** produced value continues.

Two node families, and the architecture note is emphatic that they are not the
same thing:

``router``  determines which operations execute
``choose``  determines which produced value continues

Collapsing them looks harmless and is not. A router that also picks a value has
to run every branch to have values to pick from, which is precisely the cost the
routing existed to avoid; and a chooser that also gates execution cannot be used
to combine results that were all computed for good reason.

The mechanism is the one the flow layer already has: **absence propagates.** A
router emits a present artifact on the branch it selects and an *absent* one,
carrying its reason, on the branches it does not. Every node downstream of an
unselected branch is skipped with that reason in the trace, and a `choose` node
downstream takes the first branch that survived. Nothing new in the evaluator,
and the decision is visible in the trace rather than buried in a predicate.

**A router is priced by what it skipped, not by what it cost.** ``Trace`` already
separates self-priced nodes from CPU floors; a routed run's saving is the
difference between the two traces, and :func:`routing_report` computes it that
way rather than trusting a claim about it.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from ..artifact.value import Artifact
from .port import ANY, Port
from .registry import OpDef, register_op

__all__ = ["ROUTER_POLICIES", "register_policy", "ROUTE_OP", "CHOOSE_OP",
           "routing_report", "BRANCH_PORTS"]

#: ``name -> (inputs, params) -> the branch names to enable``.
#: A policy is registered rather than passed, for the same reason a dataset
#: recipe cannot name an arbitrary importable: a graph is data.
ROUTER_POLICIES: dict[str, Callable[[Mapping[str, Artifact], Mapping[str, Any]],
                                    Sequence[str]]] = {}


def register_policy(name: str, fn) -> None:
    if name in ROUTER_POLICIES:
        raise ValueError(
            f"routing policy {name!r} is already registered. Replacing one "
            f"would silently redefine which nodes ran in every recorded trace.")
    ROUTER_POLICIES[name] = fn


#: A router has **fixed output ports** and `params["branches"]` names them in
#: order. Dynamic ports would mean a graph whose shape depends on its parameters,
#: and compile-time port checking -- the thing that makes a graph fail before it
#: costs anything -- would go with it.
BRANCH_PORTS = ("a", "b", "c", "d")


def _route(inputs: Mapping[str, Artifact], params: Mapping[str, Any],
           ctx) -> dict[str, Artifact]:
    """Enable some branches, and say why the others are off.

    The reason travels on the absent artifact, so a reader of the trace sees
    *"branch 'exact' off: policy 'escalate' selected ['cheap']"* rather than a
    node that simply did not run.
    """
    branches = [str(b) for b in (params.get("branches") or ())]
    if not branches:
        raise ValueError("a router with no branches routes nothing")
    if len(branches) > len(BRANCH_PORTS):
        raise ValueError(
            f"{len(branches)} branches but only {len(BRANCH_PORTS)} ports "
            f"{BRANCH_PORTS}; chain two routers rather than growing the op")
    policy_name = str(params.get("policy", "all"))
    try:
        policy = ROUTER_POLICIES[policy_name]
    except KeyError:
        raise KeyError(f"unknown routing policy {policy_name!r}; registered: "
                       f"{sorted(ROUTER_POLICIES)}") from None
    chosen = [b for b in policy(inputs, params) if b in branches]
    ctx.env.setdefault("routing", []).append(
        {"policy": policy_name, "chosen": list(chosen),
         "skipped": [b for b in branches if b not in chosen]})

    payload = inputs.get("in")
    out: dict[str, Artifact] = {
        "decision": Artifact(type="json", value={"policy": policy_name,
                                                 "branches": branches,
                                                 "chosen": list(chosen)})}
    for port, label in zip(BRANCH_PORTS, branches):
        out[port] = (payload if label in chosen and payload is not None
                     else Artifact.absent(
                         payload.type if payload is not None else ANY,
                         why=f"branch {label!r} off: policy {policy_name!r} "
                             f"selected {chosen}"))
    for port in BRANCH_PORTS[len(branches):]:
        out[port] = Artifact.absent(ANY, why="branch not declared by this router")
    return out


def _choose(inputs: Mapping[str, Artifact], params: Mapping[str, Any],
            ctx) -> dict[str, Artifact]:
    """The first present input, in the order the params name.

    Order is explicit because "first" over a mapping is an implementation
    detail, and a chooser whose preference depends on dict ordering is a
    decision nobody made.
    """
    order = [str(n) for n in (params.get("order") or sorted(inputs))]
    for name in order:
        art = inputs.get(name)
        if art is not None and art.present:
            return {"out": art,
                    "picked": Artifact(type="json", value=name)}
    return {"out": Artifact.absent(
        ANY, why=f"no branch of {order} produced a value"),
        "picked": Artifact(type="json", value=None)}


def _all_branches(inputs, params) -> Sequence[str]:
    return [str(b) for b in (params.get("branches") or ())]


register_policy("all", _all_branches)


def routing_report(baseline_ctx, routed_ctx) -> dict[str, Any]:
    """What routing actually bought, from the two traces rather than a claim.

    Reports the **skipped** nodes and the dollar difference, and separately the
    share of the routed total that is a CPU floor rather than a self-reported
    price — because a saving computed against unpriced nodes is a saving of
    something nobody measured.
    """
    def summarise(ctx):
        runs = ctx.trace.runs
        return {"nodes": len(runs),
                "ran": sum(1 for r in runs if not r.skipped and not r.cached),
                "skipped": sorted(r.node for r in runs if r.skipped),
                "usd": ctx.trace.total_usd,
                "cpu_only": ctx.trace.cpu_only,
                "unpriced": ctx.trace.unpriced}

    base, routed = summarise(baseline_ctx), summarise(routed_ctx)
    saved = base["usd"] - routed["usd"]
    return {"baseline": base, "routed": routed, "usd_saved": saved,
            "usd_saved_share": (saved / base["usd"]) if base["usd"] else 0.0,
            "decisions": list(routed_ctx.env.get("routing") or [])}


ROUTE_OP = register_op(OpDef(
    id="flow.route@1", fn=_route, family="router",
    # `aux` exists because a routing decision usually needs more than the
    # payload it is gating -- here, the world AND what the previous kernel
    # derived from it. Two ports rather than N, because a policy needing three
    # inputs is a policy that should be a node.
    inputs=(Port("in", ANY, required=False), Port("aux", ANY, required=False)),
    outputs=(Port("decision", "json"),) + tuple(
        Port(p, ANY, required=False) for p in BRANCH_PORTS),
    doc="Enable some branches and mark the rest absent with the reason."))

CHOOSE_OP = register_op(OpDef(
    id="flow.choose@1", fn=_choose, family="choose",
    inputs=(Port("a", ANY, required=False), Port("b", ANY, required=False),
            Port("c", ANY, required=False)),
    outputs=(Port("out", ANY), Port("picked", "json")),
    doc="The first present input, in an explicitly named order."))
