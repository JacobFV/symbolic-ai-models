"""The e-graph kernel: many equivalent forms, and a cost model to choose one.

Tier 5. It is the only kernel here whose output is not a claim *about the world*
— it is a claim that two forms are **the same**, plus the cheaper of the two
under a stated cost model. That is why its authority is `propose`: an equality
is only as good as the rules that produced it, and the rules are supplied.

Read `notes/findings/2026-08-18-the-e-graph-costs-41x-what-it-optimises.md`
before reaching for this. Equality saturation is correct here and did not pay on
the one workload it was pointed at, for reasons that are about the workload and
not about the technique.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from symbolic_ai_core.artifact.value import Provenance
from symbolic_ai_core.world import Claim, WorldDelta, WorldSnapshot

from ..abi import (Discard, KernelCost, KernelManifest, KernelRequest,
                   KernelResult, Projection, price_cpu_ns, register_kernel,
                   timed)
from .constraints import RULES, simplify

__all__ = ["EGraphKernel", "EGRAPH"]

MANIFEST = KernelManifest(
    id="egraph@1",
    requires=("logic.constraint",),
    provides=("logic.term",),
    semantics=("classical", "monotonic"),
    pure=True, deterministic=True, incremental=False, differentiable=False,
    clocks="none", runtime="native", dependencies=(),
    # An equality is only as good as the rules that produced it, and the rules
    # come from the caller. Nothing here vetoes anything.
    authority={"equivalent_form": "propose"},
    doc="Equality saturation over a constraint set, extracting the cheapest "
        "equivalent form under a supplied cost model.")


class EGraphKernel:
    manifest = MANIFEST

    def available(self) -> tuple[bool, str]:
        return True, ""

    def project(self, world: WorldSnapshot,
                request: KernelRequest) -> Projection:
        """The constraints come from the **request**, not the world.

        Unlike every other kernel here, this one optimises a *program* rather
        than reasoning about a world, so its projection covers no entities and
        says so. A discard record with nothing in it would be misleading; the
        honest entry is that the world was not read.
        """
        cons = list(request.params.get("constraints") or ())
        return Projection(
            kernel=self.manifest.id, program=cons,
            semantics=("classical", "monotonic"),
            covered_entities=frozenset(), covered_claims=(),
            discarded=(Discard("world", "*", "this kernel optimises a program, "
                                              "not a world; no entity or claim "
                                              "was read"),),
            meta={"n_constraints": len(cons), "rules": [r.name for r in RULES]})

    def run(self, projection: Projection,
            request: KernelRequest) -> KernelResult:
        cons: Sequence[Mapping[str, Any]] = projection.program
        if len(cons) < 2:
            return KernelResult(
                kernel=self.manifest.id,
                refused="fewer than two constraints: there is nothing to "
                        "combine, and returning the input unchanged would read "
                        "as a simplification",
                diagnostics={"n_constraints": len(cons)})
        result, ns = timed(lambda: simplify(cons))
        cpu, wall = ns
        claim = Claim(
            "equivalent_form",
            {"before": len(cons), "after": len(result.constraints)},
            modality="asserted",
            provenance=Provenance(
                producer=self.manifest.id, derivation="derived",
                method=f"equality saturation, {result.report.stopped_by}"))
        return KernelResult(
            kernel=self.manifest.id, claims=(claim,),
            # An equivalent form is not a fact about the world.
            delta=WorldDelta(),
            artifacts={"constraints": list(result.constraints)},
            cost=KernelCost(cpu_ns=cpu, wall_ns=wall, usd=price_cpu_ns(cpu)),
            diagnostics={**result.to_dict(), "shrank": result.shrank})


EGRAPH = register_kernel(EGraphKernel())
