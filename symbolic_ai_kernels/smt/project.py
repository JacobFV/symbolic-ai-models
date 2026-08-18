"""``P_smt`` : world -> a unit-checked constraint system.

This projection is the complement of the datalog one, and that is the clearest
demonstration in the repo of why there is no universal inference language: the
claims datalog **discards** — the ones whose roles are ``Quantity`` values with
units — are exactly the claims SMT is for. One world, two projections, disjoint
strengths, and neither is the world.

Two rules that are not negotiable here:

* **A dimensional mismatch is a refusal, not a discard.** Comparing a mass to a
  length is a malformed question rather than an unrepresentable part of the
  world, and answering it would be worse than declining. See
  :mod:`symbolic_ai_kernels.smt.units`.
* **A free variable must be declared.** A constraint referring to a variable
  nothing introduced would silently become satisfiable-by-choosing-anything,
  which is the most flattering wrong answer an SMT kernel can give.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from symbolic_ai_core.world import Claim, EntityRef, Quantity, WorldSnapshot

from ..abi import Discard, Projection
from .units import DIMENSIONLESS, UnitError, div, mul, same

__all__ = ["SmtProgram", "Variable", "project_world", "SEMANTICS"]

SEMANTICS = ("classical", "constraint")

#: Comparisons and sums require both sides in the same unit; products and
#: quotients compose. Anything else is not in the language.
COMPARISONS = {"<", "<=", ">", ">=", "==", "!="}
ADDITIVE = {"+", "-"}
MULTIPLICATIVE = {"*", "/"}


@dataclass(frozen=True)
class Variable:
    """One unknown, with the unit it is measured in and where it came from."""

    name: str
    unit: str
    sort: str = "real"          #: real | int | bool
    entity: str = ""
    fixed: float | None = None  #: a measured value, asserted as an equation

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "unit": self.unit, "sort": self.sort,
                "entity": self.entity, "fixed": self.fixed}


@dataclass
class SmtProgram:
    """Variables and constraint expressions, in the JSON form, unit-checked."""

    variables: dict[str, Variable] = field(default_factory=dict)
    constraints: list[Mapping[str, Any]] = field(default_factory=list)

    def __repr__(self) -> str:                                # pragma: no cover
        return (f"SmtProgram({len(self.variables)} vars, "
                f"{len(self.constraints)} constraints)")


def _var_name(pred: str, entity: str) -> str:
    return f"{pred}@{entity}"


def project_world(world: WorldSnapshot, *,
                  constraints: Sequence[Mapping[str, Any]] = (),
                  variables: Mapping[str, Mapping[str, Any]] = (),
                  ) -> Projection:
    """``P_smt(world)``."""
    prog = SmtProgram()
    discards: list[Discard] = []
    covered: set[str] = set()
    covered_claims: list[int] = []

    # --- declared unknowns, from logic.constraint facets ---------------
    for eid, e in sorted(world.entities.items()):
        facet = e.facet("logic.constraint")
        if facet is None:
            continue
        covered.add(eid)
        for name, spec in sorted((facet.values.get("variables") or {}).items()):
            v = Variable(name=_var_name(name, eid),
                         unit=str(spec.get("unit", DIMENSIONLESS)),
                         sort=str(spec.get("sort", "real")), entity=eid)
            prog.variables[v.name] = v
        for c in (facet.values.get("constraints") or []):
            prog.constraints.append(c)

    # --- measured quantities, from claims datalog could not carry ------
    for i, c in enumerate(world.claims):
        q = [(k, v) for k, v in c.roles.items() if isinstance(v, Quantity)]
        if not q:
            continue
        subjects = [v.id for v in c.roles.values() if isinstance(v, EntityRef)]
        if len(q) != 1 or len(subjects) != 1:
            discards.append(Discard(
                "claim", str(i),
                f"{len(q)} quantity roles and {len(subjects)} entity roles; "
                f"this projection reads one measured quantity of one entity, "
                f"and guessing which is which would invent a reading"))
            continue
        if c.modality != "asserted" or c.polarity == "negative":
            discards.append(Discard(
                "claim", str(i),
                f"a {c.polarity} {c.modality} quantity is not a measurement; "
                f"asserting it as an equation would make it one"))
            continue
        (_, quantity), entity = q[0], subjects[0]
        name = _var_name(c.predicate, entity)
        prog.variables[name] = Variable(name=name, unit=quantity.unit,
                                        entity=entity, fixed=quantity.value)
        covered.add(entity)
        covered_claims.append(i)
        if quantity.stderr is not None:
            discards.append(Discard(
                "uncertainty", str(i),
                f"stderr {quantity.stderr} projected as an exact equation; SMT "
                f"has no distribution and treating the mean as the value is a "
                f"choice, not a translation"))

    for name, spec in dict(variables or {}).items():
        prog.variables[name] = Variable(
            name=name, unit=str(spec.get("unit", DIMENSIONLESS)),
            sort=str(spec.get("sort", "real")))
    prog.constraints.extend(constraints)

    # --- the check that makes the answer mean something ----------------
    for expr in prog.constraints:
        unit_of(expr, prog.variables)          # raises UnitError, deliberately

    return Projection(
        kernel="smt@1", program=prog, semantics=SEMANTICS,
        covered_entities=frozenset(covered),
        covered_claims=tuple(covered_claims),
        discarded=tuple(discards),
        meta={"variables": {k: v.to_dict() for k, v in sorted(prog.variables.items())},
              "n_constraints": len(prog.constraints)})


def unit_of(expr: Any, variables: Mapping[str, Variable]) -> str:
    """The unit of an expression, checking every comparison on the way down."""
    if not isinstance(expr, Mapping):
        raise UnitError(f"an expression is a mapping, got {expr!r}")
    if "var" in expr:
        name = str(expr["var"])
        v = variables.get(name)
        if v is None:
            raise UnitError(
                f"constraint refers to {name!r}, which nothing declared. A free "
                f"variable would make this satisfiable by choosing anything, "
                f"which is the most flattering wrong answer available. Declare "
                f"it on a logic.constraint facet or supply it in `variables`. "
                f"Known: {sorted(variables)}")
        return v.unit
    if "q" in expr:
        q = expr["q"]
        return str(q.get("unit", DIMENSIONLESS))
    if "const" in expr:
        return DIMENSIONLESS
    op = expr.get("op")
    args = expr.get("args") or ()
    if op in ("and", "or", "not"):
        for a in args:
            unit_of(a, variables)
        return "bool"
    units = [unit_of(a, variables) for a in args]
    if op in COMPARISONS:
        if len(units) != 2:
            raise UnitError(f"{op} takes two arguments, got {len(units)}")
        same(units[0], units[1], where=f"the comparison {op}")
        return "bool"
    if op in ADDITIVE:
        out = units[0]
        for u in units[1:]:
            out = same(out, u, where=f"the sum {op}")
        return out
    if op == "*":
        out = DIMENSIONLESS
        for u in units:
            out = mul(out, u)
        return out
    if op == "/":
        out = units[0]
        for u in units[1:]:
            out = div(out, u)
        return out
    raise UnitError(f"unknown operator {op!r}; have "
                    f"{sorted(COMPARISONS | ADDITIVE | MULTIPLICATIVE | {'and', 'or', 'not'})}")
