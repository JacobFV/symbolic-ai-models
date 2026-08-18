"""The ASP kernel: world completion, and alternatives that are not collapsed.

Tier 2. Where datalog answers *what follows from this world*, ASP answers *which
completions of this world are admissible* — defaults with exceptions, mutually
exclusive hypotheses, combinatorial constraints, planning. That is already the
shape of this repo's central task, which is why the decision note ranks it above
Lean for agent cognition.

The property this kernel is built around, and the one most likely to be got
wrong by a naive integration:

> **Several answer sets are several hypotheses. It does not pick one.**

A world completion with three admissible answer sets is not a world with an
answer; it is a world with three. So the delta is asserted only when the
completion is *unique*. Otherwise the claims come back with
``modality="possible"``, every answer set is kept in ``artifacts["models"]``, and
the delta is empty — a caller that wants one must choose, with a rule it can
name, rather than receiving whichever the solver enumerated first.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from symbolic_ai_core.artifact.value import Provenance
from symbolic_ai_core.world import Claim, EntityRef, WorldDelta, WorldSnapshot

from ..abi import (KernelCost, KernelManifest, KernelRequest, KernelResult,
                   KernelUnavailable, Projection, check_entitlement,
                   price_cpu_ns, register_kernel, timed)
from .project import AspProgram, project_world

__all__ = ["AspKernel", "ASP"]

#: Enumerating every answer set of an unconstrained completion is exponential.
#: The cap is reported in the diagnostics when it bites, because a silently
#: truncated model set reads as "these are the possibilities".
DEFAULT_MAX_MODELS = 64

MANIFEST = KernelManifest(
    id="asp@1",
    requires=("core.identity",),
    provides=("logic.proposition",),
    semantics=("closed_world", "non_monotonic", "defeasible"),
    pure=True, deterministic=True, incremental=False, differentiable=False,
    clocks="none", runtime="external", dependencies=("clingo>=5.7",),
    # ASP proposes completions. An integrity constraint it enforces is a veto
    # over the completions IT enumerates, not over other kernels' claims -- a
    # constraint written from an incomplete projection has no business
    # overriding a measurement.
    authority={"admissible_completion": "propose"},
    doc="Answer set programming over the relational projection: defaults with "
        "exceptions, integrity constraints, and world completion.")


class AspKernel:
    manifest = MANIFEST

    def available(self) -> tuple[bool, str]:
        try:
            import clingo                                     # noqa: F401
        except Exception as e:                                # pragma: no cover
            return False, (f"clingo is not importable ({e}). Install the "
                           f"optional extra: `uv sync --extra solvers`.")
        return True, ""

    def _require(self) -> None:
        ok, why = self.available()
        if not ok:                                            # pragma: no cover
            raise KernelUnavailable(f"{self.manifest.id}: {why}")

    # ---- P_K ----------------------------------------------------------
    def project(self, world: WorldSnapshot,
                request: KernelRequest) -> Projection:
        self._require()
        p = request.params
        return project_world(world, program=str(p.get("program", "")),
                             choices=p.get("choices") or (),
                             constraints=p.get("constraints") or ())

    # ---- R_K ----------------------------------------------------------
    def run(self, projection: Projection,
            request: KernelRequest) -> KernelResult:
        self._require()
        import clingo

        prog: AspProgram = projection.program
        max_models = int(request.params.get("max_models", DEFAULT_MAX_MODELS))

        models: list[list[tuple[str, tuple[str, ...]]]] = []

        def collect(model: "clingo.Model") -> bool:
            models.append([(s.name, tuple(_term(a) for a in s.arguments))
                           for s in model.symbols(shown=True)])
            return len(models) < max_models

        def solve() -> Any:
            ctl = clingo.Control(["0"])          # 0 = enumerate all
            ctl.add("base", [], prog.text)
            ctl.ground([("base", [])])
            return ctl.solve(on_model=collect)

        try:
            result, ns = timed(solve)
        except RuntimeError as e:                             # syntax, mostly
            return KernelResult(
                kernel=self.manifest.id, refused=f"clingo rejected the program: {e}",
                diagnostics={"program_chars": len(prog.text)})

        if not models:
            return KernelResult(
                kernel=self.manifest.id,
                refused=("unsatisfiable: no completion of this world satisfies "
                         "the constraints. That is an answer about the "
                         "PROJECTION, not about the world -- "
                         f"{len(projection.discarded)} things were discarded "
                         "before the solver saw it."),
                cost=_cost(ns),
                diagnostics={"satisfiable": False,
                             "discarded": len(projection.discarded)})

        unique = len(models) == 1
        truncated = len(models) >= max_models and not result.exhausted
        claims = tuple(self._claims(projection, models[0],
                                    modality="asserted" if unique else "possible"))
        check_entitlement(projection, claims)
        return KernelResult(
            kernel=self.manifest.id,
            claims=claims,
            # A non-unique completion asserts nothing. Picking the first answer
            # set would be a choice the caller never made and cannot see.
            delta=WorldDelta(claims=claims) if unique else WorldDelta(),
            artifacts={"models": [self._readable(projection, m) for m in models]},
            cost=_cost(ns),
            diagnostics={"satisfiable": True, "n_models": len(models),
                         "unique": unique, "truncated": truncated,
                         "max_models": max_models,
                         "open_predicates": list(prog.open_predicates),
                         "discarded": len(projection.discarded),
                         "semantics": list(projection.semantics)})

    # ---- shared -------------------------------------------------------
    def _claims(self, projection: Projection,
                model: Sequence[tuple[str, tuple[str, ...]]], *,
                modality: str):
        prog: AspProgram = projection.program
        roles: Mapping[str, list[str]] = projection.meta.get("roles", {})
        for name, args in sorted(model):
            pred = prog.mangler.read(name)
            names = roles.get(pred) or [f"arg{i}" for i in range(len(args))]
            if len(names) != len(args):
                names = [f"arg{i}" for i in range(len(args))]
            yield Claim(
                predicate=pred,
                roles={n: (EntityRef(a) if projection.covers(a) else a)
                       for n, a in zip(names, args)},
                modality=modality,
                provenance=Provenance(
                    producer=self.manifest.id,
                    method="answer set programming, stable model semantics"))

    def _readable(self, projection: Projection, model) -> list[str]:
        prog: AspProgram = projection.program
        out = []
        for name, args in sorted(model):
            pred = prog.mangler.read(name)
            out.append(f"{pred}({', '.join(args)})" if args else pred)
        return out


def _cost(ns: tuple[int, int]) -> KernelCost:
    """clingo runs in-process here, so cpu and wall track each other closely.
    Both are recorded anyway: a container-hosted solver would not, and a cost
    table that only ever saw one of them would not notice."""
    cpu, wall = ns
    return KernelCost(cpu_ns=cpu, wall_ns=wall, usd=price_cpu_ns(cpu))


def _term(sym) -> str:
    """A clingo symbol back as the string it was projected from."""
    import clingo
    if sym.type == clingo.SymbolType.String:
        return sym.string
    return str(sym)


ASP = register_kernel(AspKernel())
