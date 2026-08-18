"""The geo kernel: distances and budgets on a stated datum.

Tier 6, the second specialised world kernel. What it does that nothing else in
the stack can:

* **datalog and ASP have no arithmetic on coordinates.** They can say a road
  exists; they cannot say how long it is.
* **SMT could encode it and should not.** Vincenty's inverse method is an
  iteration with trigonometry in the loop; expressing it as constraints would be
  slow and would tell the solver nothing it could exploit.
* **rigid@1 integrates a pose and has no notion of a datum.** A geodesic on an
  ellipsoid is not a straight line in its frame.

Every distance comes back as a ``Quantity`` in km, so the fusion layer can
combine a computed distance with a surveyed one by inverse variance — and the
kernel states its own error bar rather than implying exactness.
"""

from __future__ import annotations

import math
from typing import Any

from symbolic_ai_core.artifact.value import Provenance
from symbolic_ai_core.world import (Claim, EntityRef, Quantity, WorldDelta,
                                    WorldSnapshot)

from ..abi import (KernelCost, KernelManifest, KernelRequest, KernelResult,
                   Projection, check_entitlement, price_cpu_ns, register_kernel,
                   timed)
from .geodesy import distance_km
from .project import GeoProgram, project_world

__all__ = ["GeoKernel", "GEO", "MODEL_STDERR_KM"]

#: The stated uncertainty on a computed geodesic, as a fraction of the distance.
#: Vincenty on WGS84 is accurate to ~0.5 mm on the ellipsoid; the error that
#: matters is that the ellipsoid is not the terrain. 0.1% is a **stated
#: modelling assumption** covering datum realisation and the fact that nothing
#: travels along a geodesic, and it is in the provenance of every claim.
MODEL_STDERR_FRACTION = 0.001
MODEL_STDERR_KM = 0.05          #: floor, so a 10 m hop still carries an error bar

MANIFEST = KernelManifest(
    id="geo@1",
    requires=("geo.place", "geo.crs", "core.space"),
    provides=("geo.network", "core.quantity"),
    semantics=("classical",),
    pure=True, deterministic=True, incremental=False, differentiable=False,
    clocks="none", runtime="native", dependencies=(),
    # A computed distance is a proposal: the ellipsoid is not the terrain, and a
    # surveyed road length beats it. Nothing here vetoes anything.
    # `geodesic_distance`, not `distance`. A road survey and a great-circle
    # computation are DIFFERENT PROPERTIES of the same pair -- 459 km by road
    # against 344 km across the ellipsoid -- and a shared predicate name would
    # let the fusion layer average them into 381 km, which is neither. The
    # fusion registry groups by predicate, so the predicate is the type.
    authority={"geodesic_distance": "propose"},
    tolerances={"stderr_fraction": MODEL_STDERR_FRACTION},
    doc="Geodesic distance and within-budget reachability on WGS84, with a "
        "stated error bar.")


class GeoKernel:
    manifest = MANIFEST

    def available(self) -> tuple[bool, str]:
        return True, ""

    def project(self, world: WorldSnapshot,
                request: KernelRequest) -> Projection:
        return project_world(world)

    def run(self, projection: Projection,
            request: KernelRequest) -> KernelResult:
        prog: GeoProgram = projection.program
        if len(prog.places) < 2:
            return KernelResult(
                kernel=self.manifest.id,
                refused=f"{len(prog.places)} located place(s): a distance needs "
                        f"two, and returning nothing would read as 'no places "
                        f"are near each other'",
                diagnostics={"discarded": len(projection.discarded)})

        method = str(request.params.get("method", "ellipsoid"))
        origin = request.params.get("from")
        budget = request.params.get("within_km")
        if origin is not None and origin not in prog.places:
            return KernelResult(
                kernel=self.manifest.id,
                refused=f"origin {origin!r} is not a located place in this "
                        f"projection; it has {sorted(prog.places)[:6]}...")

        def work():
            pairs = []
            ids = sorted(prog.places)
            sources = [origin] if origin is not None else ids
            for a in sources:
                for b in ids:
                    if a == b:
                        continue
                    p, q = prog.places[a], prog.places[b]
                    d = distance_km(p.lat, p.lon, q.lat, q.lon, method=method)
                    pairs.append((a, b, d))
            return pairs

        pairs, ns = timed(work)
        nan = [(a, b) for a, b, d in pairs if math.isnan(d)]
        pairs = [(a, b, d) for a, b, d in pairs if not math.isnan(d)]
        if budget is not None:
            pairs = [(a, b, d) for a, b, d in pairs if d <= float(budget)]

        claims = tuple(
            Claim("geodesic_distance",
                  {"from": EntityRef(a), "to": EntityRef(b),
                   "value": Quantity(d, "km",
                                     max(d * MODEL_STDERR_FRACTION,
                                         MODEL_STDERR_KM))},
                  modality="asserted",
                  provenance=Provenance(
                      producer="geo@1", derivation="derived",
                      method=f"{method} on {prog.crs}; stderr "
                             f"{MODEL_STDERR_FRACTION:.1%} of the distance, a "
                             f"stated assumption covering datum realisation and "
                             f"the fact that nothing travels along a geodesic"))
            for a, b, d in pairs)
        check_entitlement(projection, claims)
        cpu, wall = ns
        return KernelResult(
            kernel=self.manifest.id, claims=claims,
            delta=WorldDelta(claims=claims),
            cost=KernelCost(cpu_ns=cpu, wall_ns=wall, usd=price_cpu_ns(cpu)),
            diagnostics={"places": len(prog.places), "pairs": len(claims),
                         "method": method, "crs": prog.crs,
                         "within_km": budget,
                         # Antipodal pairs where Vincenty does not converge are
                         # DROPPED and counted, never silently replaced by the
                         # spherical answer -- that would be a number from a
                         # different method wearing this one's provenance.
                         "non_convergent": len(nan),
                         "discarded": len(projection.discarded),
                         "semantics": list(projection.semantics)})


GEO = register_kernel(GeoKernel())
