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

__all__ = ["flood_escalate"]


def flood_escalate(inputs: Mapping[str, Artifact],
                   params: Mapping[str, Any]) -> Sequence[str]:
    """``['full']`` when the solvers can still change the answer, else ``['cheap']``.

    Both gates are **provably lossless**, which is the only kind of routing
    worth doing before there is a utility model to trade against: a heuristic
    gate trades accuracy for cost and cannot be evaluated without one.
    """
    from .ops import needs_the_solvers

    world_art = inputs.get("in")
    reach_art = inputs.get("aux")
    if world_art is None or not world_art.present:
        return ["full"]
    reach = [Claim.from_dict(c)
             for c in ((reach_art.value or {}).get("claims", [])
                       if reach_art is not None and reach_art.present else [])]
    need, _why = needs_the_solvers(read_world(world_art), reach)
    return ["full"] if need else ["cheap"]


register_policy("flood_escalate", flood_escalate)
