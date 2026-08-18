"""The handful of operations the flow layer itself needs.

Nothing domain-specific lives here. A constant, an identity, an explicit unit
conversion and an explicit reframe — the last two exist so that the type checker
in :mod:`.compile` can *refuse* an implicit conversion and still leave the caller
a legal way to say what they meant.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from ..artifact.value import Artifact
from .port import Port
from .registry import OpDef, register_op

__all__ = ["const", "CONST_OP", "IDENTITY_OP", "CONVERT_UNIT_OP", "REFRAME_OP"]


def _const(inputs, params: Mapping[str, Any], ctx) -> dict[str, Artifact]:
    """Emit a fixed artifact. The entry point of every graph."""
    from .store_helpers import artifact_from_dict
    a = params["artifact"]
    return {"out": a if isinstance(a, Artifact) else artifact_from_dict(a)}


def _identity(inputs: Mapping[str, Artifact], params, ctx) -> dict[str, Artifact]:
    return {"out": inputs["in"]}


def _convert_unit(inputs: Mapping[str, Artifact], params: Mapping[str, Any],
                  ctx) -> dict[str, Artifact]:
    """Multiply by a stated factor and relabel the unit. Explicit on purpose.

    There is no unit *database* here and that is deliberate: a conversion that
    the graph can see, with its factor written in the node's params, is auditable
    from the trace. A silent lookup is not, and the whole reason the port checker
    refuses a mismatch is to force this node to exist.
    """
    a = inputs["in"]
    factor = float(params["factor"])
    to = str(params["to"])
    if not a.present:
        return {"out": a}
    if not isinstance(a.value, (int, float)):
        raise TypeError(f"flow.convert_unit@1 needs a numeric value, got "
                        f"{type(a.value).__name__}")
    return {"out": replace(a, value=a.value * factor, unit=to)}


def _reframe(inputs: Mapping[str, Artifact], params: Mapping[str, Any],
             ctx) -> dict[str, Artifact]:
    """Relabel the coordinate frame. Refuses to be a no-op in disguise.

    This op does not transform coordinates — it asserts that the caller has
    already done so, and records it. It raises when the frames already match,
    because a reframe that changes nothing is a node somebody left in after
    fixing the real problem elsewhere, and it will read as a conversion that
    happened.
    """
    a = inputs["in"]
    to = str(params["to"])
    if a.present and a.frame == to:
        raise ValueError(f"flow.reframe@1 to {to!r} but the artifact is already "
                         f"in {to!r}: this node asserts a transform that did not "
                         f"happen")
    return {"out": replace(a, frame=to)}


def const(artifact: Artifact) -> dict[str, Any]:
    """Params for a ``flow.const@1`` node carrying ``artifact``."""
    return {"artifact": artifact}


CONST_OP = register_op(OpDef(id="flow.const@1", fn=_const, family="source",
                             outputs=(Port("out", "any"),),
                             doc="Emit a fixed artifact."))
IDENTITY_OP = register_op(OpDef(id="flow.identity@1", fn=_identity,
                                inputs=(Port("in", "any"),),
                                outputs=(Port("out", "any"),),
                                doc="Pass an artifact through unchanged."))
CONVERT_UNIT_OP = register_op(OpDef(
    id="flow.convert_unit@1", fn=_convert_unit, family="transform",
    inputs=(Port("in", "any"),), outputs=(Port("out", "any"),),
    doc="Multiply by a stated factor and relabel the unit."))
REFRAME_OP = register_op(OpDef(
    id="flow.reframe@1", fn=_reframe, family="transform",
    inputs=(Port("in", "any"),), outputs=(Port("out", "any"),),
    doc="Relabel the coordinate frame, recording that a transform happened."))
