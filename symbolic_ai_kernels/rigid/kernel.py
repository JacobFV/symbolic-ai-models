"""The rigid-body kernel: one step forward, with the uncertainty it grew.

Tier 6, the first **specialised world** kernel. Deliberately small — semi-implicit
Euler under a uniform field — because the point is not the physics. The point is
that a domain engine sits behind the same narrow contract as datalog and Lean,
declares its clock, and returns *claims with uncertainty* rather than writing a
new pose into a shared world.

That last part is what makes the fusion gate reachable. A predicted pose and an
observed pose are two claims about one property, and something has to combine
them. This kernel's job is to produce the prediction **with an honest error
bar**, because a prediction whose stderr is missing would dominate an
inverse-variance fusion completely — and would look exactly like a very good
prediction while doing it.
"""

from __future__ import annotations

import math
from typing import Any

from symbolic_ai_core.artifact.value import Provenance
from symbolic_ai_core.world import (Claim, EntityRef, Facet, Quantity,
                                    WorldDelta, WorldSnapshot)

from ..abi import (KernelCost, KernelManifest, KernelRequest, KernelResult,
                   Projection, check_entitlement, price_cpu_ns, register_kernel,
                   timed)
from .project import Body, RigidProgram, project_world

__all__ = ["RigidKernel", "RIGID"]

MANIFEST = KernelManifest(
    id="rigid@1",
    requires=("scene.body", "scene.pose", "core.quantity", "core.time"),
    provides=("scene.pose",),
    semantics=("classical", "temporal"),
    pure=True, deterministic=True, incremental=False, differentiable=False,
    # The first kernel with a clock. Everything above it runs on demand; this
    # one advances a state by a stated dt, and a coupling node that hands it a
    # dt from a different clock is the thing the multi-clock design exists for.
    clocks="fixed_dt",
    runtime="native", dependencies=(),
    # A prediction is a proposal. It has no business overriding an observation,
    # and the inverse-variance rule is what decides between them.
    authority={"pose": "propose"},
    tolerances={"dt_s": 1.0},
    doc="Semi-implicit Euler under a uniform field, returning poses with the "
        "uncertainty the step grew.")


class RigidKernel:
    manifest = MANIFEST

    def available(self) -> tuple[bool, str]:
        return True, ""

    def project(self, world: WorldSnapshot,
                request: KernelRequest) -> Projection:
        return project_world(world)

    def run(self, projection: Projection,
            request: KernelRequest) -> KernelResult:
        prog: RigidProgram = projection.program
        if not prog.bodies:
            return KernelResult(
                kernel=self.manifest.id,
                refused="no body in this world carries both scene.body and a "
                        "framed scene.pose, so 'nothing moved' would be true "
                        "and empty",
                diagnostics={"discarded": len(projection.discarded)})
        dt = float(request.params.get("dt_s", 0.0))
        if dt <= 0:
            return KernelResult(
                kernel=self.manifest.id,
                refused=f"dt_s={dt}: a step of zero or negative duration is "
                        f"not a step, and defaulting one would invent a clock")
        if dt > self.manifest.tolerances["dt_s"]:
            return KernelResult(
                kernel=self.manifest.id,
                refused=f"dt_s={dt} exceeds the declared tolerance "
                        f"{self.manifest.tolerances['dt_s']}; explicit Euler "
                        f"diverges and a result past the tolerance would be a "
                        f"number rather than a prediction")

        stepped, ns = timed(lambda: [_step(b, prog.gravity, dt)
                                     for b in prog.bodies])
        claims = tuple(_claim(b, prog.frame, dt) for b in stepped)
        check_entitlement(projection, claims)
        cpu, wall = ns
        return KernelResult(
            kernel=self.manifest.id, claims=claims,
            delta=WorldDelta(facets={
                b.id: (Facet("scene.pose", {"position": list(b.position),
                                            "velocity": list(b.velocity),
                                            "frame": b.frame,
                                            "stderr_m": b.pos_stderr}),)
                for b in stepped}),
            cost=KernelCost(cpu_ns=cpu, wall_ns=wall, usd=price_cpu_ns(cpu)),
            diagnostics={"bodies": len(stepped), "dt_s": dt,
                         "frame": prog.frame,
                         "gravity": list(prog.gravity),
                         "without_uncertainty":
                             projection.meta.get("without_uncertainty", 0),
                         "discarded": len(projection.discarded),
                         "semantics": list(projection.semantics)})


def _step(b: Body, gravity: tuple[float, ...], dt: float) -> Body:
    """Semi-implicit Euler: velocity first, then position from the *new* one.

    Chosen over explicit Euler because it is stable for oscillatory systems at
    the same cost, and because a physics kernel whose energy drifts upward is a
    kernel whose long-horizon claims are confidently wrong.

    The uncertainty grows as ``sqrt(sigma^2 + (sigma_v * dt)^2)`` with the
    velocity error taken as a fixed fraction of the position error per second —
    a **stated modelling assumption**, not a derivation, and it is in the
    provenance of every claim this produces.
    """
    vel = tuple(v + g * dt for v, g in zip(b.velocity, gravity))
    pos = tuple(p + v * dt for p, v in zip(b.position, vel))
    stderr = b.pos_stderr
    if stderr is not None:
        stderr = math.sqrt(stderr ** 2 + (stderr * dt) ** 2)
    return Body(id=b.id, mass=b.mass, position=pos, velocity=vel,
                frame=b.frame, pos_stderr=stderr)


def _claim(b: Body, frame: str, dt: float) -> Claim:
    return Claim(
        "pose", {"of": EntityRef(b.id),
                 "value": Quantity(_norm(b.position), "m", b.pos_stderr)},
        modality="asserted",
        provenance=Provenance(
            producer="rigid@1",
            method=f"semi-implicit Euler, dt={dt}s, frame {frame}; position "
                   f"error grown as sqrt(s^2 + (s*dt)^2) with velocity error "
                   f"taken as s per second -- a stated assumption, not a "
                   f"derivation"))


def _norm(v: tuple[float, ...]) -> float:
    """Poses are reported as a scalar magnitude, which is a real loss.

    The `Quantity` role carries one number, so a 3-vector pose collapses to its
    norm and the direction is gone. That is fine for the fusion demonstration
    and wrong for anything else; a vector-valued claim is what this needs and
    the world IR does not have one yet.
    """
    return math.sqrt(sum(x * x for x in v))


RIGID = register_kernel(RigidKernel())
