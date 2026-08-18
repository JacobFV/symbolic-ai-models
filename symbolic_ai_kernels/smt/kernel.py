"""The SMT kernel: arithmetic and logic together, with the units carried through.

Tier 3. ASP answers *which discrete completions are admissible*; SMT answers
*which values satisfy this mixture of logic and arithmetic*. The example the
decision note gives is the one this is built for:

```
mass(robot) < 20 kg
battery(robot) >= required(route)
arrival_time < 17:00
```

Three properties, in descending order of how easy they are to get wrong:

* **A model comes back as quantities with units**, because the variables went in
  with units and the projection checked them. An SMT kernel that returns bare
  numbers has thrown away the only thing that made the answer checkable.
* **UNSAT is a statement about the projection.** The refusal says how many
  things were discarded before the solver saw the problem, because "no solution
  exists" and "no solution exists among the constraints I could express" are
  different claims and only one of them is usually true.
* **A satisfying model is one witness, not the answer.** Claims come back as
  ``modality="possible"`` unless the caller asked for and got uniqueness; a
  witness asserted as a measurement is a fabricated observation.
"""

from __future__ import annotations

from typing import Any, Mapping

from symbolic_ai_core.artifact.value import Provenance
from symbolic_ai_core.world import (Claim, EntityRef, Quantity, WorldDelta,
                                    WorldSnapshot)

from ..abi import (KernelCost, KernelManifest, KernelRequest, KernelResult,
                   KernelUnavailable, Projection, check_entitlement,
                   price_cpu_ns, register_kernel, timed)
from .project import SmtProgram, Variable, project_world, unit_of
from .units import UnitError

__all__ = ["SmtKernel", "SMT"]

#: **Size does not order this kernel's cost, and no estimator is offered.**
#: Measured over random 3-SAT with z3, median of five instances per cell:
#:
#: ===========  =========  ==============
#: clauses      ratio      median
#: ===========  =========  ==============
#: 1,491        4.26       >15,000 ms (all five censored at the cap)
#: 2,250        15.0       1.9 ms
#: 5,250        15.0       6.0 ms
#: ===========  =========  ==============
#:
#: A problem 1.5x larger solved at least 7,892x faster. Size ordered cost on
#: 0.667 of pairs, against 1.000 for datalog, because difficulty here is a
#: property of *structure* -- distance from the satisfiability phase
#: transition -- and not of size.
#:
#: So the honest interface for this kernel is not an estimate. It is a
#: **budget**: give it a timeout, treat exhaustion as an outcome rather than
#: an error, and never let a planner conclude from a small instance that a
#: larger one costs more.
COST_IS_SIZE_ORDERABLE = False

MANIFEST = KernelManifest(
    id="smt@1",
    requires=("core.quantity",),
    provides=("logic.constraint",),
    semantics=("classical", "constraint"),
    pure=True, deterministic=True, incremental=False, differentiable=False,
    clocks="none", runtime="external", dependencies=("z3-solver>=4.13",),
    # An UNSAT from an exact solver over constraints it fully represented is a
    # veto: no completion any other kernel proposes can satisfy them either.
    # A satisfying witness is only a proposal.
    authority={"constraint_violation": "veto", "witness_value": "propose"},
    doc="SMT over the quantity projection: arithmetic and logic with units "
        "checked before the solver sees them.")


class SmtKernel:
    manifest = MANIFEST

    def available(self) -> tuple[bool, str]:
        try:
            import z3                                         # noqa: F401
        except Exception as e:                                # pragma: no cover
            return False, (f"z3 is not importable ({e}). Install the optional "
                           f"extra: `uv sync --extra solvers`.")
        return True, ""

    def _require(self) -> None:
        ok, why = self.available()
        if not ok:                                            # pragma: no cover
            raise KernelUnavailable(f"{self.manifest.id}: {why}")

    # ---- P_K ----------------------------------------------------------
    def project(self, world: WorldSnapshot,
                request: KernelRequest) -> Projection:
        self._require()
        return project_world(world,
                             constraints=request.params.get("constraints") or (),
                             variables=request.params.get("variables") or {})

    # ---- R_K ----------------------------------------------------------
    def run(self, projection: Projection,
            request: KernelRequest) -> KernelResult:
        self._require()
        import z3

        prog: SmtProgram = projection.program
        if not prog.constraints:
            return KernelResult(
                kernel=self.manifest.id,
                refused="no constraints: an SMT kernel with nothing to satisfy "
                        "would return the trivial model, which reads as an "
                        "answer",
                diagnostics={"n_variables": len(prog.variables)})

        z: dict[str, Any] = {}
        for name, v in prog.variables.items():
            z[name] = (z3.Int(name) if v.sort == "int"
                       else z3.Bool(name) if v.sort == "bool"
                       else z3.Real(name))
        solver = z3.Solver()
        for name, v in prog.variables.items():
            if v.fixed is not None:
                solver.add(z[name] == v.fixed)
        try:
            for c in prog.constraints:
                solver.add(_build(c, z))
        except (UnitError, ValueError) as e:
            return KernelResult(kernel=self.manifest.id,
                                refused=f"the constraint system is malformed: {e}")

        check, ns = timed(solver.check)
        if check == z3.unsat:
            return KernelResult(
                kernel=self.manifest.id,
                refused=("unsat: no assignment satisfies these constraints. "
                         f"That is a statement about the PROJECTION -- "
                         f"{len(projection.discarded)} things were discarded "
                         f"before the solver saw the problem."),
                cost=_cost(ns),
                diagnostics={"satisfiable": False,
                             "discarded": len(projection.discarded)})
        if check == z3.unknown:                               # pragma: no cover
            return KernelResult(
                kernel=self.manifest.id,
                refused=f"z3 returned unknown: {solver.reason_unknown()}",
                cost=_cost(ns))

        model = solver.model()
        claims = tuple(self._claims(projection, prog, model))
        check_entitlement(projection, claims)
        return KernelResult(
            kernel=self.manifest.id, claims=claims,
            # A witness is not a measurement. The delta stays empty; a caller
            # that wants to adopt one does so explicitly.
            delta=WorldDelta(),
            artifacts={"model": {k: str(model[z[k]]) for k in sorted(z)
                                 if model[z[k]] is not None}},
            cost=_cost(ns),
            diagnostics={"satisfiable": True, "n_variables": len(prog.variables),
                         "n_constraints": len(prog.constraints),
                         "discarded": len(projection.discarded),
                         "semantics": list(projection.semantics)})

    def _claims(self, projection: Projection, prog: SmtProgram, model):
        import z3
        for name, v in sorted(prog.variables.items()):
            if v.fixed is not None or not v.entity:
                continue                       # a measurement, or not an entity's
            raw = model[z3.Real(name) if v.sort == "real"
                        else z3.Int(name) if v.sort == "int" else z3.Bool(name)]
            if raw is None:
                continue                       # unconstrained: no witness to give
            pred = name.split("@", 1)[0]
            yield Claim(
                predicate=pred,
                roles={"of": EntityRef(v.entity),
                       "value": Quantity(_as_float(raw), v.unit)},
                modality="possible",
                provenance=Provenance(
                    producer=self.manifest.id,
                    method="SMT witness; one satisfying assignment, not a "
                           "measurement"))


def _cost(ns: tuple[int, int]) -> KernelCost:
    cpu, wall = ns
    return KernelCost(cpu_ns=cpu, wall_ns=wall, usd=price_cpu_ns(cpu))


def _as_float(raw) -> float:
    try:
        return float(raw.as_fraction())
    except AttributeError:
        return float(str(raw))


def _build(expr: Mapping[str, Any], z: Mapping[str, Any]):
    """The JSON constraint form as a z3 expression. Units already checked."""
    import z3
    if "var" in expr:
        return z[str(expr["var"])]
    if "q" in expr:
        return z3.RealVal(float(expr["q"]["value"]))
    if "const" in expr:
        v = expr["const"]
        return z3.BoolVal(v) if isinstance(v, bool) else z3.RealVal(float(v))
    op = expr.get("op")
    args = [_build(a, z) for a in expr.get("args") or ()]
    if op == "and":
        return z3.And(*args)
    if op == "or":
        return z3.Or(*args)
    if op == "not":
        return z3.Not(args[0])
    if op == "<":
        return args[0] < args[1]
    if op == "<=":
        return args[0] <= args[1]
    if op == ">":
        return args[0] > args[1]
    if op == ">=":
        return args[0] >= args[1]
    if op == "==":
        return args[0] == args[1]
    if op == "!=":
        return args[0] != args[1]
    if op == "+":
        return z3.Sum(args)
    if op == "-":
        return args[0] - args[1] if len(args) == 2 else -args[0]
    if op == "*":
        out = args[0]
        for a in args[1:]:
            out = out * a
        return out
    if op == "/":
        out = args[0]
        for a in args[1:]:
            out = out / a
        return out
    raise ValueError(f"unknown operator {op!r}")


SMT = register_kernel(SmtKernel())
