"""``P_rigid`` : world -> bodies with a mass, a pose and a velocity.

The first **specialised world** kernel, and the first whose projection is about
physical state rather than about symbols. What it takes from the world is
narrow — ``scene.body`` for mass, ``scene.pose`` for position and velocity,
``scene.field`` for a uniform acceleration — and everything else is discarded by
name.

Two discards are worth reading, because they are the ones a physics integration
would otherwise get silently wrong:

* **a body with no stated frame** is discarded, not defaulted. Integrating a
  position in an unnamed frame produces a number that looks like a position and
  is a position in nothing.
* **a pose with no uncertainty** is projected, and the *absence* is recorded.
  A deterministic prediction fused against a noisy observation as though it were
  exact would dominate the fusion completely, which is the failure the
  inverse-variance rule exists to avoid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from symbolic_ai_core.world import Entity, Quantity, WorldSnapshot

from ..abi import Discard, Projection

__all__ = ["Body", "RigidProgram", "project_world", "SEMANTICS"]

SEMANTICS = ("classical", "temporal")


@dataclass(frozen=True)
class Body:
    """One body's state, in one frame, with units already checked."""

    id: str
    mass: float                 #: kg
    position: tuple[float, ...]
    velocity: tuple[float, ...]
    frame: str
    pos_stderr: float | None = None

    def dim(self) -> int:
        return len(self.position)


@dataclass
class RigidProgram:
    bodies: list[Body] = field(default_factory=list)
    gravity: tuple[float, ...] = ()
    frame: str = ""

    def __repr__(self) -> str:                                # pragma: no cover
        return f"RigidProgram({len(self.bodies)} bodies, frame {self.frame!r})"


def _vec(values: Any) -> tuple[float, ...] | None:
    if isinstance(values, (list, tuple)) and values and all(
            isinstance(v, (int, float)) and not isinstance(v, bool)
            for v in values):
        return tuple(float(v) for v in values)
    return None


def project_world(world: WorldSnapshot) -> Projection:
    """``P_rigid(world)``."""
    prog = RigidProgram()
    discards: list[Discard] = []
    covered: set[str] = set()

    for eid, e in sorted(world.entities.items()):
        body = e.facet("scene.body")
        pose = e.facet("scene.pose")
        if body is None or pose is None:
            continue
        frame = str(pose.values.get("frame", ""))
        if not frame:
            discards.append(Discard(
                "entity", eid,
                "no coordinate frame on scene.pose; integrating a position in "
                "an unnamed frame produces a number that looks like a position "
                "and is a position in nothing"))
            continue
        pos = _vec(pose.values.get("position"))
        vel = _vec(pose.values.get("velocity")) or (
            tuple(0.0 for _ in pos) if pos else None)
        mass = body.values.get("mass_kg")
        if pos is None or vel is None or not isinstance(mass, (int, float)):
            discards.append(Discard(
                "entity", eid,
                f"incomplete state: position={pose.values.get('position')!r} "
                f"velocity={pose.values.get('velocity')!r} mass_kg={mass!r}"))
            continue
        if len(vel) != len(pos):
            discards.append(Discard(
                "entity", eid,
                f"position is {len(pos)}-dimensional and velocity is "
                f"{len(vel)}-dimensional"))
            continue
        stderr = pose.values.get("stderr_m")
        if stderr is None:
            discards.append(Discard(
                "uncertainty", eid,
                "no stderr on the pose; a deterministic prediction fused "
                "against a noisy observation as though exact would dominate "
                "the fusion completely"))
        prog.bodies.append(Body(id=eid, mass=float(mass), position=pos,
                                velocity=vel, frame=frame,
                                pos_stderr=(float(stderr)
                                            if isinstance(stderr, (int, float))
                                            else None)))
        covered.add(eid)

    frames = {b.frame for b in prog.bodies}
    if len(frames) > 1:
        raise ValueError(
            f"bodies arrive in {sorted(frames)}. There is no transform here on "
            f"purpose: a reframe belongs in an explicit flow node where the "
            f"trace can show it, exactly as with units.")
    prog.frame = next(iter(frames), "")

    for c in world.claims:
        if c.predicate == "gravity" and isinstance(c.roles.get("value"), Quantity):
            pass                                   # scalar magnitude, see below
    field_e = [e for e in world.entities.values() if e.facet("scene.field")]
    for e in field_e:
        g = _vec((e.facet("scene.field").values or {}).get("acceleration"))
        if g is not None:
            prog.gravity = g
            covered.add(e.id)
    if prog.bodies and not prog.gravity:
        prog.gravity = tuple(0.0 for _ in prog.bodies[0].position)

    if prog.bodies and len(prog.gravity) != prog.bodies[0].dim():
        raise ValueError(
            f"the field is {len(prog.gravity)}-dimensional and the bodies are "
            f"{prog.bodies[0].dim()}-dimensional")

    return Projection(
        kernel="rigid@1", program=prog, semantics=SEMANTICS,
        covered_entities=frozenset(covered), covered_claims=(),
        discarded=tuple(discards),
        meta={"n_bodies": len(prog.bodies), "frame": prog.frame,
              "gravity": list(prog.gravity),
              "without_uncertainty": sum(1 for b in prog.bodies
                                         if b.pos_stderr is None)})
