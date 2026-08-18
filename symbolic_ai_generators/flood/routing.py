"""The flood task's escalation policy, registered as data.

A routing policy is registered by name and referenced from the graph, for the
same reason a dataset recipe cannot name an arbitrary importable: a graph is
data, and data that can name any callable is a graph that can execute anything.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from symbolic_ai_core.artifact.value import Artifact
from symbolic_ai_core.flow.router import register_policy
from symbolic_ai_core.world import Claim
from symbolic_ai_kernels.flow_ops import read_world

__all__ = ["flood_escalate", "flood_learned", "needs_the_solvers_raw"]


def needs_the_solvers_raw(world: Mapping[str, Any],
                          reach: Sequence[Mapping[str, Any]]
                          ) -> tuple[bool, str]:
    """The escalation gates, read straight off the serialised world.

    Identical in meaning to :func:`symbolic_ai_generators.flood.ops.needs_the_solvers`
    and asserted equal to it by test. The difference is that it does **not**
    rebuild a `WorldSnapshot`: measured, the gate was the third most expensive
    node in the routed pipeline at 10.4% of its cost -- above datalog itself --
    entirely because `WorldSnapshot.from_dict` reconstructs every Entity and
    Claim so that two `if` statements can read six fields.

    That is the routing principle biting its own implementation. A gate has to be
    cheaper than what it gates, and this one was only 6.5x cheaper than the
    solvers it decides on, which is most of why lossless routing saved 4.5%
    rather than the double digits the skip rate implies.
    """
    depot = site = None
    limits: dict[str, float] = {}
    span: dict[str, tuple[str, str]] = {}
    mass: dict[str, float] = {}
    cap: dict[str, float] = {}
    demand = None
    for c in world.get("claims", ()):
        pred, roles = c.get("predicate"), c.get("roles") or {}
        if pred == "depot":
            depot = _ent(roles.get("where"))
        elif pred == "needs":
            site = _ent(roles.get("where"))
        elif pred == "bridge_on":
            a, b, via = (_ent(roles.get("a")), _ent(roles.get("b")),
                         _ent(roles.get("via")))
            if a and b and via:
                span[via] = tuple(sorted((a, b)))
        elif pred == "load_limit":
            q, of = _qty(roles.get("value")), _ent(roles.get("of"))
            if q is not None and of:
                limits[of] = q
        elif pred in ("mass", "capacity"):
            q, of = _qty(roles.get("value")), _ent(roles.get("of"))
            if q is not None and of:
                (mass if pred == "mass" else cap)[of] = q
        elif pred == "demand":
            demand = _qty(roles.get("value"))

    pairs = {(_ent(r.get("roles", {}).get("a")), _ent(r.get("roles", {}).get("b")))
             for r in reach if r.get("predicate") == "reach"}
    if depot and site and (depot, site) not in pairs:
        return False, ("the demand site is not reachable from the depot, so no "
                       "vehicle can serve it whatever the loads are")

    posted = [v for k, v in limits.items() if k in span]
    if demand is not None and posted:
        laden = [mass[v] + demand for v in mass
                 if v in cap and cap[v] >= demand]
        if laden and max(laden) <= min(posted):
            return False, (f"every qualifying vehicle's laden mass "
                           f"({max(laden):g} kg) clears the lightest posted "
                           f"limit ({min(posted):g} kg), so no bridge can bind")
    return True, ""


def _ent(role: Any) -> str | None:
    return role.get("entity") if isinstance(role, dict) else None


def _qty(role: Any) -> float | None:
    if isinstance(role, dict) and "quantity" in role:
        return float(role["quantity"]["value"])
    return None


def flood_escalate(inputs: Mapping[str, Artifact],
                   params: Mapping[str, Any]) -> Sequence[str]:
    """``['full']`` when the solvers can still change the answer, else ``['cheap']``.

    Both gates are **provably lossless**, which is the only kind of routing
    worth doing before there is a utility model to trade against: a heuristic
    gate trades accuracy for cost and cannot be evaluated without one.
    """
    world_art = inputs.get("in")
    reach_art = inputs.get("aux")
    if world_art is None or not world_art.present:
        return ["full"]
    need, _why = needs_the_solvers_raw(
        world_art.value,
        (reach_art.value or {}).get("claims", [])
        if reach_art is not None and reach_art.present else [])
    return ["full"] if need else ["cheap"]


register_policy("flood_escalate", flood_escalate)


def flood_learned(inputs: Mapping[str, Artifact],
                  params: Mapping[str, Any]) -> Sequence[str]:
    """``['cheap']`` when a fitted model says the cheap answer will match.

    Registered **beside** ``flood_escalate`` rather than replacing it, because
    the measured comparison is that the hand-written provable gate captures
    *more* headroom at zero accuracy loss. A learned gate is worth having when
    an accuracy bar below 1.000 is acceptable, and the policy name is how a
    graph says which trade it is making.

    The model comes in through ``params["model"]`` as a dict, so a graph stays
    data: a policy that could load a path would be a graph that reads the
    filesystem.
    """
    from .features import feature_vector
    from .gate_model import GateModel

    spec = params.get("model")
    if not spec:
        raise KeyError(
            "the learned gate needs params['model'] -- a GateModel dict. "
            "Without one it would fall back to some default policy, and a "
            "silent fallback is how a broken component reads as a working one.")
    model = spec if isinstance(spec, GateModel) else GateModel.from_dict(spec)

    world_art = inputs.get("in")
    reach_art = inputs.get("aux")
    if world_art is None or not world_art.present:
        return ["full"]
    reach = [Claim.from_dict(c)
             for c in ((reach_art.value or {}).get("claims", [])
                       if reach_art is not None and reach_art.present else [])]
    x = feature_vector(read_world(world_art), reach)
    return ["cheap"] if model.take_cheap(x) else ["full"]


register_policy("flood_learned", flood_learned)
