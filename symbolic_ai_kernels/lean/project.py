"""``P_lean`` : world -> a typed signature and one term per claim.

Datalog and ASP are **untyped**. `link(truck_0, region_1)` is a perfectly good
datalog fact and a perfectly good ASP atom, and both will happily compute a
closure over it. Nothing in the relational half of this substrate can notice
that a vehicle was passed where a region belongs.

This projection can, and that is the whole reason it exists. It reads the types
the world already carries — an entity's `types` tuple, which the relational
projection emits as an inert `type/2` fact and never consults — and turns them
into a **signature**: each entity type becomes a sort, each entity a constant of
its sort, and each predicate a Pi type inferred from its *first* use. Every later
use is then typechecked against that.

Two decisions worth stating:

**Modality and polarity are not filtered.** Datalog refuses to project a
hypothesis because asserting it as a fact would make it a measurement. Type
validity is a different question and is **independent of whether the claim is
asserted**: a badly-typed hypothesis is worth rejecting *before* anybody adopts
it, which is precisely the verifier's job in the stack. So everything
structurally projectable is checked.

**An entity with two types is a real loss.** `san_francisco` is a `geo.place`
and a `politics.jurisdiction`; a monomorphic signature holds one. The first is
taken, the rest are recorded as discards, and the consequence is stated there:
a predicate expecting the dropped sort will read as a type error that is really
a projection error. That is the honest failure and it is why the discard record
is not decoration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from symbolic_ai_core.world import Claim, EntityRef, Quantity, WorldSnapshot
from symbolic_ai_lean import Const, Expr, Sort, apps, arrow

from ..abi import Discard, Projection

__all__ = ["LeanProgram", "project_world", "SEMANTICS", "ENTITY", "PROP"]

SEMANTICS = ("classical", "monotonic")

#: The sort every untyped entity falls back to. A fallback, not a default: an
#: entity with no declared type constrains nothing, so every predicate position
#: it appears in accepts anything, and the check is vacuous there. The count is
#: reported so a reader can see how vacuous.
ENTITY = Const("Entity")
PROP = Sort(0)

#: Literal sorts. Deliberately coarse — this kernel checks *role confusion*
#: (a vehicle where a region belongs), not numeric domains, and a finer literal
#: lattice would only make it reject things SMT is better placed to judge.
STR = Const("Str")
NUM = Const("Num")
QUANTITY = Const("Quantity")


@dataclass
class LeanProgram:
    """The signature, the term per claim, and which claim each term came from."""

    sig: dict[str, Expr] = field(default_factory=dict)
    terms: list[tuple[int, Expr]] = field(default_factory=list)
    sorts: dict[str, str] = field(default_factory=dict)   #: entity -> sort name
    untyped: int = 0

    def __repr__(self) -> str:                                # pragma: no cover
        return (f"LeanProgram({len(self.sig)} declarations, "
                f"{len(self.terms)} terms)")


def _arg_sort(value: Any, sorts: Mapping[str, str]) -> Expr | None:
    if isinstance(value, EntityRef):
        return Const(sorts.get(value.id, "Entity"))
    if isinstance(value, Quantity):
        return QUANTITY
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return NUM
    if isinstance(value, str):
        return STR
    return None


def project_world(world: WorldSnapshot) -> Projection:
    """``P_lean(world)``."""
    prog = LeanProgram()
    discards: list[Discard] = []
    covered: set[str] = set()
    covered_claims: list[int] = []

    # --- sorts, from the types the world already carries ---------------
    for eid, e in sorted(world.entities.items()):
        if e.types:
            prog.sorts[eid] = e.types[0]
            if len(e.types) > 1:
                discards.append(Discard(
                    "entity", eid,
                    f"types {list(e.types)} collapsed to {e.types[0]!r}: a "
                    f"monomorphic signature holds one sort, so a predicate "
                    f"expecting {list(e.types[1:])} will read as a type error "
                    f"that is really a projection error"))
        else:
            prog.untyped += 1
        covered.add(eid)

    for sort in sorted(set(prog.sorts.values())):
        prog.sig[sort] = Sort(1)
    prog.sig["Entity"] = Sort(1)
    prog.sig["Str"] = Sort(1)
    prog.sig["Num"] = Sort(1)
    prog.sig["Quantity"] = Sort(1)
    for eid in sorted(covered):
        prog.sig[eid] = Const(prog.sorts.get(eid, "Entity"))

    # --- one term per claim, declaring each predicate on first use -----
    literals: dict[str, Expr] = {}
    for i, c in enumerate(world.claims):
        if any(isinstance(v, Claim) for v in c.roles.values()):
            discards.append(Discard(
                "claim", str(i),
                "a nested proposition needs a Prop-valued argument position; "
                "this projection declares predicates over data sorts only"))
            continue
        names = sorted(c.roles)
        args: list[Expr] = []
        arg_sorts: list[Expr] = []
        bad = ""
        for name in names:
            v = c.roles[name]
            sort = _arg_sort(v, prog.sorts)
            if sort is None:
                bad = (f"role {name!r} is a {type(v).__name__}, which has no "
                       f"sort in this signature")
                break
            arg_sorts.append(sort)
            if isinstance(v, EntityRef):
                args.append(Const(v.id))
            else:
                key = _literal_name(v)
                literals.setdefault(key, sort)
                args.append(Const(key))
        if bad:
            discards.append(Discard("claim", str(i), bad))
            continue
        prog.sig.setdefault(c.predicate, arrow(arg_sorts, PROP))
        prog.terms.append((i, apps(Const(c.predicate), args)))
        covered_claims.append(i)

    for key, sort in sorted(literals.items()):
        prog.sig.setdefault(key, sort)

    return Projection(
        kernel="lean@1", program=prog, semantics=SEMANTICS,
        covered_entities=frozenset(covered),
        covered_claims=tuple(covered_claims),
        discarded=tuple(discards),
        meta={"n_declarations": len(prog.sig), "n_terms": len(prog.terms),
              "untyped_entities": prog.untyped,
              "sorts": sorted(set(prog.sorts.values()))})


def _literal_name(v: Any) -> str:
    """A stable constant name for a literal.

    Prefixed, because a literal string ``"region_0"`` and an entity id
    ``region_0`` are different things and a signature that let them collide
    would typecheck a claim nobody made.
    """
    if isinstance(v, Quantity):
        return f"q#{v.value}#{v.unit}"
    if isinstance(v, bool):
        return f"b#{v}"
    if isinstance(v, (int, float)):
        return f"n#{v}"
    return f"s#{v}"
