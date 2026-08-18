"""The economy kernel: consolidated aggregates **as known on a date**.

Tier 6. What it does that nothing else in the stack can:

* **datalog** can walk the ownership tree and cannot add up revenue;
* **SMT** can check a covenant and has no notion of which vintage of a figure
  was available;
* **geo** and **rigid** are about space, not about what was known when.

The whole kernel is one operation — sum an indicator over a consolidation
subtree, for a period, **using only observations whose ``transaction_time``
precedes the as-of date** — and the reason it is a kernel rather than a helper is
that last clause. Every backtest that has ever been optimistic got it wrong, and
the way it goes wrong is silent: the number is plausible, the code is short, and
the answer is the one you would have wanted rather than the one you could have
had.

``as_of`` is therefore **required**. There is no default, because the only
available default is "now", which is precisely the bug.
"""

from __future__ import annotations

from typing import Any

from symbolic_ai_core.artifact.value import Interval, Provenance
from symbolic_ai_core.world import (Claim, EntityRef, Quantity, WorldDelta,
                                    WorldSnapshot)

from ..abi import (KernelCost, KernelManifest, KernelRequest, KernelResult,
                   Projection, check_entitlement, price_cpu_ns, register_kernel,
                   timed)
from .project import EconomyProgram, Observation, project_world

__all__ = ["EconomyKernel", "ECONOMY", "as_of_value"]

MANIFEST = KernelManifest(
    id="economy@1",
    requires=("economy.actor", "economy.indicator", "core.time",
              "core.quantity"),
    provides=("economy.indicator", "core.quantity"),
    semantics=("classical", "temporal"),
    pure=True, deterministic=True, incremental=False, differentiable=False,
    # Two clocks, and the whole point of the kernel is that they are different.
    clocks="valid_and_transaction",
    runtime="native", dependencies=(),
    # A consolidated aggregate is a proposal: it is only as good as the
    # ownership tree and the vintage it was computed from, and a filed
    # consolidated statement beats it.
    authority={"consolidated": "propose"},
    doc="Sum an indicator over a consolidation subtree for a period, using only "
        "figures whose transaction_time precedes a required as-of date.")


def as_of_value(observations: list[Observation], entity: str, indicator: str,
                period: str, as_of: str) -> tuple[float | None, str, int]:
    """The latest vintage of one figure that existed on ``as_of``.

    Returns ``(value, known_from, n_vintages_available)``. ``None`` when the
    figure had not been published yet on that date — which is a real answer and
    must not be replaced by the first revision that came later.
    """
    candidates = [o for o in observations
                  if o.entity == entity and o.indicator == indicator
                  and o.period == period and o.known_from <= as_of]
    if not candidates:
        return None, "", 0
    latest = max(candidates, key=lambda o: o.known_from)
    return latest.value, latest.known_from, len(candidates)


class EconomyKernel:
    manifest = MANIFEST

    def available(self) -> tuple[bool, str]:
        return True, ""

    def project(self, world: WorldSnapshot,
                request: KernelRequest) -> Projection:
        return project_world(world)

    def run(self, projection: Projection,
            request: KernelRequest) -> KernelResult:
        prog: EconomyProgram = projection.program
        if not prog.observations:
            return KernelResult(
                kernel=self.manifest.id,
                refused="no observation carries both a period and a "
                        "publication date, so there is nothing that can be "
                        "read as-of any moment",
                diagnostics={"discarded": len(projection.discarded)})

        as_of = request.params.get("as_of")
        if not as_of:
            return KernelResult(
                kernel=self.manifest.id,
                refused="as_of is required. The only available default is "
                        "'now', and using it is exactly the look-ahead bias "
                        "this kernel exists to prevent -- a backtest that reads "
                        "the latest revision of a figure is answering a "
                        "question nobody could have asked at the time.")
        indicator = str(request.params.get("indicator", "revenue"))
        period = request.params.get("period")
        if not period:
            return KernelResult(
                kernel=self.manifest.id,
                refused="period is required; summing across periods would add "
                        "a quarter to a year")
        roots = request.params.get("of") or sorted(prog.actors)

        def work():
            out = []
            for root in roots:
                members = prog.subtree(root)
                total = 0.0
                unit = ""
                missing, used, vintages = [], [], 0
                for m in members:
                    v, known, n = as_of_value(prog.observations, m, indicator,
                                              str(period), str(as_of))
                    if v is None:
                        missing.append(m)
                        continue
                    total += v
                    vintages += n
                    used.append((m, known))
                    unit = unit or next(
                        (o.unit for o in prog.observations
                         if o.entity == m and o.indicator == indicator), "")
                out.append((root, total, unit, members, used, missing, vintages))
            return out

        rows, ns = timed(work)
        claims = []
        reports = []
        for root, total, unit, members, used, missing, vintages in rows:
            reports.append({"of": root, "members": len(members),
                            "reported": len(used), "missing": sorted(missing),
                            "vintages_seen": vintages,
                            "latest_known_from": max((k for _, k in used),
                                                     default="")})
            if not used:
                continue        # nothing had been published; not a zero
            claims.append(Claim(
                "consolidated", {"of": EntityRef(root),
                                 "indicator": indicator,
                                 "value": Quantity(total, unit or "1")},
                modality="asserted",
                valid_time=Interval(str(period), str(period)),
                transaction_time=Interval(str(as_of), str(as_of)),
                provenance=Provenance(
                    producer="economy@1", derivation="derived",
                    method=f"sum of {indicator} over {len(used)} of "
                           f"{len(members)} consolidated entities, using the "
                           f"latest vintage published on or before {as_of}")))
        check_entitlement(projection, claims)
        cpu, wall = ns
        return KernelResult(
            kernel=self.manifest.id, claims=tuple(claims),
            delta=WorldDelta(claims=tuple(claims)),
            artifacts={"coverage": reports},
            cost=KernelCost(cpu_ns=cpu, wall_ns=wall, usd=price_cpu_ns(cpu)),
            diagnostics={
                "as_of": as_of, "period": period, "indicator": indicator,
                "roots": len(roots), "claims": len(claims),
                # A subtree where some members had not reported yet produces a
                # total that is NOT comparable with a later one. Counted, never
                # smoothed over -- a partial sum silently labelled complete is
                # the second way a vintage-aware number goes wrong.
                "incomplete": sum(1 for r in reports if r["missing"]),
                "discarded": len(projection.discarded),
                "semantics": list(projection.semantics)})


ECONOMY = register_kernel(EconomyKernel())
