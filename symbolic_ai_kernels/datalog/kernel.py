"""The datalog kernel: the hot relational path, and the first ABI implementation.

``run`` computes the least model and returns the **derived** facts as claims —
the ones the rules produced, not the ones the projection put in. That distinction
matters more than it looks: returning the whole model would make the kernel
appear to have derived everything it was told, and a delta full of facts that
were already in the world is a delta nothing can be measured against.

Incremental use is what this kernel is really for. :meth:`run_delta` takes a
``WorldDelta`` and computes only its consequences, which is the shape the flow
layer's world reconciliation already has: a delta arrives, and the cost is
proportional to what changed rather than to the size of the world.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from symbolic_ai_core.artifact.value import Provenance
from symbolic_ai_core.world import (Claim, EntityRef, WorldDelta, WorldSnapshot)

from ..abi import (Discard, KernelCost, KernelManifest, KernelRequest,
                   KernelResult, Projection, check_entitlement, register_kernel,
                   timed)
from .engine import Fact, Program, Rule, add_facts_report, evaluate
from .project import DatalogProgram, project_world, rule_from_dict

__all__ = ["DatalogKernel", "DATALOG"]

MANIFEST = KernelManifest(
    id="datalog@1",
    requires=("core.identity",),
    provides=("logic.proposition",),
    semantics=("closed_world", "non_monotonic"),
    pure=True, deterministic=True, incremental=True, differentiable=False,
    clocks="none", runtime="native", dependencies=(),
    # Datalog derives; it does not adjudicate. Nothing it says overrides an
    # exact kernel, and a derived fact is a proposal like any other -- the
    # closed-world assumption behind it is exactly the thing another kernel may
    # have grounds to reject.
    authority={"derived_fact": "propose"},
    doc="Semi-naive fixed point with stratified negation, over the relational "
        "projection of a world.")


class DatalogKernel:
    """``P_datalog`` and ``R_datalog``, behind the ABI."""

    manifest = MANIFEST

    # ---- availability -------------------------------------------------
    def available(self) -> tuple[bool, str]:
        """Native, so always. Kept because the ABI requires every kernel to
        answer it, and the answer for clingo, z3 and Lean will not be this."""
        return True, ""

    # ---- P_K ----------------------------------------------------------
    def project(self, world: WorldSnapshot,
                request: KernelRequest) -> Projection:
        p = project_world(world, extra_rules=_request_rules(request))
        # A rule author may name the roles of a predicate the rules *derive*.
        # Without it a derived predicate has no role names to keep -- it never
        # had any -- and its claim comes back as arg0/arg1, which is honest but
        # unhelpful when the author knew.
        named = dict(request.params.get("role_names") or {})
        if not named:
            return p
        return replace(p, meta={**p.meta,
                                "roles": {**p.meta.get("roles", {}), **named}})

    # ---- R_K ----------------------------------------------------------
    def run(self, projection: Projection,
            request: KernelRequest) -> KernelResult:
        prog: DatalogProgram = projection.program
        if not prog.program.rules:
            return KernelResult(
                kernel=self.manifest.id,
                refused="no rules: a datalog kernel with an empty program "
                        "derives nothing, and returning an empty delta would "
                        "read as 'no consequences' rather than 'nothing asked'",
                diagnostics={"n_facts": len(prog.facts)})
        model, ns = timed(lambda: evaluate(prog.program, prog.facts))
        derived = model - prog.facts
        return self._result(projection, derived, ns, extra={"full": True})

    def run_delta(self, projection: Projection,
                  delta: WorldDelta) -> KernelResult:
        """Consequences of a ``WorldDelta`` only. ``projection`` is not modified.

        The delta is **projected through the same P_K** rather than handed over
        as raw facts, which is what keeps the entitlement rule honest: entities
        the delta introduces become covered by the extended projection, and a
        role the projection would have discarded is discarded here too. Passing
        raw tuples would let a fact about an entity nobody projected slip in as a
        bare string, which reads as an answer and is not one.
        """
        prog: DatalogProgram = projection.program
        sub = WorldSnapshot(
            entities={e.id: e for e in delta.entities},
            claims=delta.claims)
        dproj = project_world(sub)
        extended = replace(
            projection,
            covered_entities=projection.covered_entities | dproj.covered_entities,
            discarded=projection.discarded + dproj.discarded,
            meta={**projection.meta,
                  "roles": {**projection.meta.get("roles", {}),
                            **dproj.meta.get("roles", {})}})
        new_facts = dproj.program.facts - prog.facts
        known = evaluate(prog.program, prog.facts)
        (added, full), ns = timed(
            lambda: add_facts_report(prog.program, known, new_facts))
        return self._result(extended, added, ns,
                            extra={"recomputed_from_scratch": full,
                                   "new_facts": len(new_facts)})

    # ---- shared -------------------------------------------------------
    def _result(self, projection: Projection, facts: set[Fact], ns: int,
                extra: dict[str, Any]) -> KernelResult:
        roles = projection.meta.get("roles", {})
        claims = tuple(_fact_to_claim(f, roles, projection) for f in sorted(facts))
        check_entitlement(projection, claims)
        return KernelResult(
            kernel=self.manifest.id,
            claims=claims,
            delta=WorldDelta(claims=claims),
            diagnostics={"derived": len(facts),
                         "discarded": len(projection.discarded),
                         "semantics": list(projection.semantics), **extra},
            cost=KernelCost(cpu_ns=ns))


def _request_rules(request: KernelRequest) -> list[Rule]:
    raw = request.params.get("rules") or ()
    out: list[Rule] = []
    for r in raw:
        out.append(r if isinstance(r, Rule) else rule_from_dict(r))
    return out


def _fact_to_claim(fact: Fact, roles: dict[str, list[str]],
                   projection: Projection) -> Claim:
    """A derived fact, back as a claim with its original role names.

    Terms that name an entity the projection covered become ``EntityRef``;
    anything else stays a literal. Getting this wrong in the other direction —
    making every term an entity — would invent identities out of strings that
    were only ever attribute values.
    """
    pred, *terms = fact
    names = roles.get(pred) or [f"arg{i}" for i in range(len(terms))]
    if len(names) != len(terms):                          # pragma: no cover
        names = [f"arg{i}" for i in range(len(terms))]
    filled = {n: (EntityRef(t) if projection.covers(t) else t)
              for n, t in zip(names, terms)}
    return Claim(
        predicate=pred, roles=filled, modality="asserted",
        provenance=Provenance(
            producer="datalog@1",
            method="stratified datalog, closed world, negation as failure"))


DATALOG = register_kernel(DatalogKernel())
