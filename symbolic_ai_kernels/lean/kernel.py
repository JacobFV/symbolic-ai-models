"""The Lean kernel: the verifier, and the only thing in the stack that vetoes.

Tier 4. The stack's division of labour, from the decision note:

```
omegaclaw / ASP / datalog / search / LM
        |  candidate claims
        v
     lean / smt
        |  a proof, or a refutation
```

**The exploratory reasoner does not need to be sound. The verifier does.** So
this kernel is the one whose manifest declares `type_valid: veto`, and the one
whose negative claims survive fusion against any number of positive proposals.

What it actually checks here is **role confusion**: that a predicate is applied
to the sorts it was first applied to. `link(truck_0, region_1)` is a well-formed
datalog fact and a well-formed ASP atom, and neither can notice. It typechecks
against `link : region -> region -> Prop` and fails, by name.

That is narrower than "Lean proves theorems" and the manifest says so. The
kernel is native and total — real Lean 4 stays the out-of-band conformance
oracle it already was for `symbolic_ai_lean`, because a subprocess elaborator
inside a sweep breaks the cost budget the whole repo is arguing about.
"""

from __future__ import annotations

from typing import Any

from symbolic_ai_core.artifact.value import Provenance
from symbolic_ai_core.world import Claim, EntityRef, WorldDelta, WorldSnapshot
from symbolic_ai_lean import MetaCtx, infer, pretty
from symbolic_ai_lean.kernel import TypeError_

from ..abi import (KernelCost, KernelManifest, KernelRequest, KernelResult,
                   Projection, check_entitlement, price_cpu_ns, register_kernel,
                   timed)
from .project import LeanProgram, PROP, project_world

__all__ = ["LeanKernel", "LEAN"]

MANIFEST = KernelManifest(
    id="lean@1",
    requires=("core.identity", "core.type"),
    provides=("logic.proof",),
    semantics=("classical", "monotonic"),
    pure=True, deterministic=True, incremental=False, differentiable=False,
    clocks="none", runtime="native", dependencies=(),
    # The only veto in the stack that is about *validity* rather than about
    # feasibility. A refutation from an exact checker is not one vote: no
    # completion any other kernel proposes can make an ill-typed claim well
    # typed. `type_valid` positive is only a proposal, because a claim this
    # kernel accepted may still be false.
    authority={"type_valid": "veto"},
    doc="Typecheck each claim against a signature inferred from the world's own "
        "entity types. Catches role confusion the untyped kernels cannot.")


class LeanKernel:
    manifest = MANIFEST

    def available(self) -> tuple[bool, str]:
        """Native and total. Real Lean 4 is an out-of-band oracle, not this."""
        return True, ""

    def project(self, world: WorldSnapshot,
                request: KernelRequest) -> Projection:
        return project_world(world)

    def run(self, projection: Projection,
            request: KernelRequest) -> KernelResult:
        prog: LeanProgram = projection.program
        if not prog.terms:
            return KernelResult(
                kernel=self.manifest.id,
                refused="no terms: nothing in this world projected to a "
                        "checkable proposition, so 'everything typechecks' "
                        "would be true and empty",
                diagnostics={"discarded": len(projection.discarded)})

        def work():
            out = []
            for index, term in prog.terms:
                ctx = MetaCtx()
                try:
                    got = infer(term, prog.sig, ctx)
                    ok = isinstance(got, type(PROP)) and got.level == PROP.level
                    why = "" if ok else f"inferred {pretty(got)}, not Prop"
                except TypeError_ as e:
                    ok, why = False, str(e)
                except RecursionError:                    # pragma: no cover
                    ok, why = False, "checker ran out of stack"
                out.append((index, ok, why, pretty(term)))
            return out

        checked, ns = timed(work)
        bad = [(i, why, term) for i, ok, why, term in checked if not ok]

        claims = tuple(
            Claim("type_valid", {"claim": f"claim#{i}"},
                  polarity="negative", modality="asserted",
                  provenance=Provenance(
                      producer=self.manifest.id, derivation="derived",
                      method=f"typecheck failed: {why}"))
            for i, why, _ in bad)
        check_entitlement(projection, claims)

        cpu, wall = ns
        return KernelResult(
            kernel=self.manifest.id,
            claims=claims,
            # Only refutations go into the delta. "This claim typechecks" is
            # not a fact about the world -- it is a fact about the projection --
            # and writing one per claim would bury the world in bookkeeping.
            delta=WorldDelta(claims=claims),
            artifacts={"refutations": [
                {"claim": i, "term": term, "why": why} for i, why, term in bad]},
            cost=KernelCost(cpu_ns=cpu, wall_ns=wall, usd=price_cpu_ns(cpu)),
            diagnostics={
                "checked": len(checked), "refuted": len(bad),
                "declarations": len(prog.sig),
                "untyped_entities": prog.untyped,
                "vacuous": prog.untyped > 0,
                "discarded": len(projection.discarded),
                "semantics": list(projection.semantics)})


LEAN = register_kernel(LeanKernel())
