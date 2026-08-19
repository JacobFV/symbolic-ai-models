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
from typing import Any, Iterable, Mapping

from symbolic_ai_core.artifact.value import Provenance
from symbolic_ai_core.runtime.estimate import PowerLawCost
from symbolic_ai_core.world import (Claim, EntityRef, WorldDelta, WorldSnapshot)

from ..abi import (Discard, KernelCost, KernelManifest, KernelRequest,
                   KernelResult, Projection, check_entitlement, price_cpu_ns,
                   register_kernel, timed, Witness)
from .engine import Fact, Program, Rule, add_facts_report, evaluate
from .proof import (derivation_tree, evaluate_with_derivations,
                    tree_size)
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
    cost_estimator=lambda facts=0, **_: estimate_cost(facts),
    doc="Semi-naive fixed point with stratified negation, over the relational "
        "projection of a world.")


#: Fitted on measured closures of the GLEIF ownership relation, 250 to 124,460
#: edges. **Read the exponent as a local slope, not a complexity class.** Fitted
#: over the small end it comes out near 1.04, because fixed overhead dominates
#: there; over the whole range it is 1.33; the large end alone behaves like
#: 1.56. Extrapolating the small-end fit under-predicts the full corpus by 7x
#: -- and orders every pair correctly anyway, which is why `Calibration`
#: reports error and ordering separately.
DATALOG_COST = PowerLawCost(a=1.55e-6, b=1.33, n=10)


def estimate_cost(facts: int) -> KernelCost:
    """What this kernel will cost on a world of ``facts`` relations.

    Systematically **low** beyond the fitted range, and saying so here rather
    than leaving a caller to discover it. Use it to *order* candidate plans,
    not to budget one.
    """
    if facts <= 0:
        return KernelCost(cpu_ns=0)
    return KernelCost(cpu_ns=int(DATALOG_COST(facts) * 1e9))


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
        # A witness here is OPT-IN, and the reason is in `proof.py`'s own
        # docstring: recording provenance costs memory proportional to the
        # closure and slows the fixed point, and a published number carrying
        # `evaluate`'s name must keep meaning what it meant. So the caller asks
        # for one goal and pays for it; the default path is byte-for-byte the
        # one every existing measurement used.
        goal = request.params.get("witness_for")
        if goal is None:
            model, ns = timed(lambda: evaluate(prog.program, prog.facts))
            derived = model - prog.facts
            return self._result(projection, derived, ns,
                                extra={"full": True,
                                       "witness": "not requested — pass "
                                                  "witness_for to pay for "
                                                  "derivation recording"})

        goal_fact = goal if isinstance(goal, Fact) else _fact_from(goal)

        def work():
            return evaluate_with_derivations(prog.program, prog.facts)

        (model, why), ns = timed(work)
        derived = model - prog.facts
        if goal_fact not in model:
            # Not derivable is the UNIVERSAL half and it has no witness: under
            # closed-world semantics it is a claim about the whole fixed point,
            # and nothing smaller than recomputing it establishes the absence.
            return self._result(projection, derived, ns,
                                extra={"full": True,
                                       "witness": "goal is not derivable; a "
                                                  "non-derivation has no tree"})
        tree = derivation_tree(goal_fact, why)
        return self._result(
            projection, derived, ns,
            extra={"full": True, "witness_nodes": tree_size(tree)},
            witness=Witness(
                kind="derivation",
                facts=tuple(sorted(str(f) for f in _leaves(tree))),
                claim=f"{goal_fact} follows from these base facts",
                verifies=("replay the rule applications over the named base "
                          "facts; `verify_derivation` reads the tree and the "
                          "base set and never the closure, which is why it "
                          "stays flat as the model grows")))

    def run_delta(self, projection: Projection, delta: WorldDelta, *,
                  known: set[Fact] | None = None) -> KernelResult:
        """Consequences of a ``WorldDelta`` only. ``projection`` is not modified.

        The delta is **projected through the same P_K** rather than handed over
        as raw facts, which is what keeps the entitlement rule honest: entities
        the delta introduces become covered by the extended projection, and a
        role the projection would have discarded is discarded here too. Passing
        raw tuples would let a fact about an entity nobody projected slip in as a
        bare string, which reads as an answer and is not one.

        ``known`` is the base model, which the caller is expected to hold across
        deltas — that is the entire point of an incremental kernel. **When it is
        not supplied this method computes it, and the reported cost includes
        doing so**, with ``base_recomputed`` set in the diagnostics. An earlier
        version timed only the incremental step while silently recomputing the
        base underneath it, which made an O(model) call report an O(delta)
        price: exactly the kind of number this repo has had to retract before.
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
        base_recomputed = known is None

        def work():
            base = (evaluate(prog.program, prog.facts) if base_recomputed
                    else known)
            return add_facts_report(prog.program, base, new_facts)

        (added, full), ns = timed(work)
        return self._result(extended, added, ns,
                            extra={"recomputed_from_scratch": full,
                                   "base_recomputed": base_recomputed,
                                   "new_facts": len(new_facts)})

    # ---- shared -------------------------------------------------------
    def _result(self, projection: Projection, facts: set[Fact],
                ns: tuple[int, int], extra: dict[str, Any],
                witness: Witness | None = None) -> KernelResult:
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
            witness=witness,
            cost=_cost(ns))


def _leaves(d) -> list:
    """The base facts a derivation actually rests on — its dependency set."""
    if d.is_base:
        return [d.fact]
    return [f for c in d.children for f in _leaves(c)]


def _fact_from(goal: Any) -> Fact:
    """A goal given as a mapping, or already as a fact.

    ``Fact`` is ``tuple`` and a fact is **flat** — ``(predicate, *constants)``,
    not ``(predicate, args)``. Building it the second way produces a two-element
    tuple whose second element is a tuple, which matches nothing in the model
    and fails silently as "not derivable" rather than loudly as a type error.
    """
    if isinstance(goal, Mapping):
        return (str(goal["predicate"]), *tuple(goal["args"]))
    return tuple(goal)


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
            producer="datalog@1", derivation="derived",
            method="stratified datalog, closed world, negation as failure"))


DATALOG = register_kernel(DatalogKernel())


def _cost(ns: tuple[int, int]) -> KernelCost:
    cpu, wall = ns
    return KernelCost(cpu_ns=cpu, wall_ns=wall, usd=price_cpu_ns(cpu))
