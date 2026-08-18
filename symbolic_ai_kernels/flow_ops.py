"""Flow-graph operations that run kernels. The join between phase 4 and phase 6.

Everything below is deliberately thin. A node names a kernel by id, the kernel
projects and runs, and the result travels on as ordinary artifacts. That is the
whole point of having both layers: **kernel selection is configuration, not
control flow.** Swapping ``datalog@1`` for ``asp@1`` at a node is a parameter
edit, and nothing above or below has to know.

Three artifact types are introduced here and nowhere else:

``world_snapshot``  a serialised :class:`~symbolic_ai_core.world.WorldSnapshot`
``world_delta``     a serialised :class:`~symbolic_ai_core.world.WorldDelta`
``claim_set``       a list of serialised claims, plus who produced them

The projection travels too, as ``projection`` — including its discard record —
because a claim set whose losses were dropped on the way out of the kernel is
back to being an answer that looks like every other answer.
"""

from __future__ import annotations

from typing import Any, Mapping

from symbolic_ai_core.artifact.value import Artifact
from symbolic_ai_core.flow.port import Port
from symbolic_ai_core.flow.registry import OpDef, register_op
from symbolic_ai_core.runtime.fusion import FUSION_RULES, fuse
from symbolic_ai_core.world import Claim, WorldDelta, WorldSnapshot

from .abi import KernelRequest, KernelUnavailable, get_kernel

__all__ = ["KERNEL_RUN", "APPLY_DELTA", "FUSE", "world_artifact",
           "claims_artifact", "read_world"]


def world_artifact(world: WorldSnapshot) -> Artifact:
    return Artifact(type="world_snapshot", value=world.to_dict(),
                    schema="sai.world@1", profiles=tuple(world.profiles()))


def claims_artifact(claims, producer: str) -> Artifact:
    return Artifact(type="claim_set",
                    value={"producer": producer,
                           "claims": [c.to_dict() for c in claims]},
                    schema="sai.world@1", profiles=("logic.proposition",))


def read_world(art: Artifact) -> WorldSnapshot:
    return WorldSnapshot.from_dict(art.value)


def _read_claims(art: Artifact) -> list[Claim]:
    if not art.present or art.value is None:
        return []
    return [Claim.from_dict(c) for c in art.value.get("claims", [])]


# ---------------------------------------------------------------------------
def _kernel_run(inputs: Mapping[str, Artifact], params: Mapping[str, Any],
                ctx) -> dict[str, Artifact]:
    """Project a world into one kernel's language, run it, carry the losses out."""
    kernel = get_kernel(str(params["kernel"]))
    ok, why = kernel.available()
    if not ok:
        # A refusal, not an empty result: the two are indistinguishable
        # downstream and only one of them means "nothing followed".
        raise KernelUnavailable(f"{params['kernel']}: {why}")
    world = read_world(inputs["world"])
    request = KernelRequest(goal=params.get("goal"),
                            params=dict(params.get("request") or {}),
                            budget_ns=params.get("budget_ns"),
                            budget_usd=params.get("budget_usd"))
    projection = kernel.project(world, request)
    result = kernel.run(projection, request)
    ctx.cost_usd = result.cost.usd
    return {
        "claims": claims_artifact(result.claims, result.kernel),
        "delta": Artifact(type="world_delta", value=result.delta.to_dict(),
                          schema="sai.world@1"),
        "projection": Artifact(type="projection", value=projection.to_dict()),
        "report": Artifact(type="json", value={
            "kernel": result.kernel, "refused": result.refused,
            # Without these a downstream node can only string-match `refused`,
            # which is how two generators came to assert "infeasible" from a
            # timeout. `settled` is the field a node should branch on before
            # it manufactures a negative claim from an absent positive one.
            "outcome": result.classification,
            "settled": result.conclusive,
            "diagnostics": dict(result.diagnostics),
            "cost": result.cost.to_dict(),
            "artifacts": {k: v for k, v in result.artifacts.items()}}),
    }


def _apply_delta(inputs: Mapping[str, Artifact], params, ctx
                 ) -> dict[str, Artifact]:
    """``world + delta -> world``. A new snapshot; the input is untouched."""
    world = read_world(inputs["world"])
    d = inputs["delta"]
    delta = WorldDelta(claims=tuple(
        Claim.from_dict(c) for c in (d.value or {}).get("claims", [])))
    return {"world": world_artifact(delta.apply(world))}


def _fuse(inputs: Mapping[str, Artifact], params: Mapping[str, Any], ctx
          ) -> dict[str, Artifact]:
    """Combine claim sets. Unresolved mixtures come out as their own artifact.

    They are a separate port rather than a field on the result because a caller
    that never looks at them has silently treated "nobody was entitled to settle
    this" as "settled", and a port is harder to not look at than a key.
    """
    claims: list[Claim] = []
    for name in ("a", "b", "c"):
        art = inputs.get(name)
        if art is not None:
            claims.extend(_read_claims(art))
    rule_names = dict(params.get("rules") or {})
    rules = {p: FUSION_RULES[r] if isinstance(r, str) else r
             for p, r in rule_names.items()}
    authority = dict(params.get("authority") or {})
    if params.get("authority_from_kernels"):
        for kid in params["authority_from_kernels"]:
            authority[kid] = dict(get_kernel(kid).manifest.authority)
    out = fuse(claims, rules=rules, authority=authority)
    return {
        "claims": claims_artifact(out.resolved, "fuse"),
        "unresolved": Artifact(type="json", value=[
            {"predicate": g.predicate, "subject": list(g.subject),
             "producers": list(g.producers()),
             "claims": [c.to_dict() for c in g.claims]}
            for g in out.unresolved]),
        "report": Artifact(type="json", value=out.to_dict()),
    }


KERNEL_RUN = register_op(OpDef(
    id="kernel.run@1", fn=_kernel_run, family="kernel",
    inputs=(Port("world", "world_snapshot"),),
    outputs=(Port("claims", "claim_set"), Port("delta", "world_delta"),
             Port("projection", "projection"), Port("report", "json")),
    doc="Project a world into one kernel's language, run it, and carry the "
        "projection's discard record out with the claims."))

APPLY_DELTA = register_op(OpDef(
    id="world.apply_delta@1", fn=_apply_delta, family="reconcile",
    inputs=(Port("world", "world_snapshot"), Port("delta", "world_delta")),
    outputs=(Port("world", "world_snapshot"),),
    doc="Apply a delta, returning a new snapshot."))

FUSE = register_op(OpDef(
    id="world.fuse@1", fn=_fuse, family="fuse",
    inputs=(Port("a", "claim_set"), Port("b", "claim_set", required=False),
            Port("c", "claim_set", required=False)),
    outputs=(Port("claims", "claim_set"), Port("unresolved", "json"),
             Port("report", "json")),
    doc="Combine claim sets property by property; unresolved mixtures come out "
        "on their own port."))
