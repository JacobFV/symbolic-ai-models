"""``P_economy`` : world -> indicator observations with **both** times.

The third specialised world kernel, and the first whose projection is about a
*vintage* rather than a state. What it takes:

* ``economy.indicator`` claims — a quantity for an entity, over a period;
* ``economy.actor`` entities and the ownership claims between them;

and the thing it will not do without is **both times on every observation**:

``valid_time``
    the period the number is about — Q3 2026 revenue.
``transaction_time``
    when this system could have known it — the publication or revision date.

Published economic series are revised, sometimes substantially and sometimes for
years. A store with one time cannot answer *what did we believe on the day we
decided*, which is the only question a backtest is actually asking. ALFRED exists
beside FRED for exactly this, and the world IR has carried both fields since it
was written without anything using them.

So an observation missing either time is **discarded by name**. Defaulting
``transaction_time`` to "now" is the specific mistake that makes every historical
evaluation optimistic, and it is one line to write by accident.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from symbolic_ai_core.world import Claim, EntityRef, Quantity, WorldSnapshot

from ..abi import Discard, Projection

__all__ = ["Observation", "EconomyProgram", "project_world", "SEMANTICS"]

SEMANTICS = ("classical", "temporal")


@dataclass(frozen=True)
class Observation:
    """One number, for one entity, about one period, known from one date."""

    entity: str
    indicator: str
    value: float
    unit: str
    period: str          #: valid_time start -- the period it is *about*
    known_from: str      #: transaction_time start -- when we could have known it
    stderr: float | None = None


@dataclass
class EconomyProgram:
    observations: list[Observation] = field(default_factory=list)
    #: child -> parent, from ownership claims. A forest, checked for cycles.
    owner: dict[str, str] = field(default_factory=dict)
    actors: set[str] = field(default_factory=set)

    def children(self, parent: str) -> list[str]:
        return sorted(c for c, p in self.owner.items() if p == parent)

    def subtree(self, root: str) -> list[str]:
        """``root`` and everything it consolidates, depth first."""
        out, stack = [], [root]
        seen = set()
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            out.append(node)
            stack.extend(self.children(node))
        return out

    def __repr__(self) -> str:                                # pragma: no cover
        return (f"EconomyProgram({len(self.observations)} observations, "
                f"{len(self.actors)} actors)")


def project_world(world: WorldSnapshot) -> Projection:
    """``P_economy(world)``."""
    prog = EconomyProgram()
    discards: list[Discard] = []
    covered: set[str] = set()

    for eid, e in sorted(world.entities.items()):
        if e.facet("economy.actor") is not None or "actor" in e.types:
            prog.actors.add(eid)
            covered.add(eid)

    for i, c in enumerate(world.claims):
        if c.predicate == "owns":
            parent = _ent(c.roles.get("parent"))
            child = _ent(c.roles.get("child"))
            if parent and child:
                if child in prog.owner and prog.owner[child] != parent:
                    discards.append(Discard(
                        "claim", str(i),
                        f"{child} is already consolidated into "
                        f"{prog.owner[child]}; a second parent would double "
                        f"count it, and choosing one silently is worse than "
                        f"refusing the edge"))
                    continue
                prog.owner[child] = parent
                covered.update((parent, child))
            continue

        q = c.roles.get("value")
        subject = _ent(c.roles.get("of"))
        if not isinstance(q, Quantity) or subject is None:
            continue
        if c.modality != "asserted" or c.polarity == "negative":
            discards.append(Discard(
                "claim", str(i),
                f"a {c.polarity} {c.modality} figure is not an observation; "
                f"aggregating it would put a hypothesis into a total"))
            continue
        if not c.valid_time.start:
            discards.append(Discard(
                "claim", str(i),
                "no valid_time: a figure with no period is not an observation "
                "of anything, and summing it into a quarter would be an "
                "arbitrary choice of which quarter"))
            continue
        if not c.transaction_time.start:
            discards.append(Discard(
                "claim", str(i),
                "no transaction_time: this system cannot say when it could have "
                "known this number, so it cannot be used as-of any date. "
                "Defaulting it to 'now' is the one line that makes every "
                "historical evaluation optimistic."))
            continue
        prog.observations.append(Observation(
            entity=subject, indicator=c.predicate, value=q.value, unit=q.unit,
            period=c.valid_time.start, known_from=c.transaction_time.start,
            stderr=q.stderr))
        covered.add(subject)

    cycle = _cycle(prog.owner)
    if cycle:
        raise ValueError(
            f"ownership cycle {cycle}: consolidating it would count the same "
            f"revenue once per lap. Circular shareholdings are real and need a "
            f"proportional-consolidation model, which this kernel does not have.")

    return Projection(
        kernel="economy@1", program=prog, semantics=SEMANTICS,
        covered_entities=frozenset(covered), covered_claims=(),
        discarded=tuple(discards),
        meta={"observations": len(prog.observations),
              "actors": len(prog.actors),
              "consolidated": len(prog.owner),
              "indicators": sorted({o.indicator for o in prog.observations}),
              "periods": sorted({o.period for o in prog.observations})})


def _ent(role: Any) -> str | None:
    return role.id if isinstance(role, EntityRef) else None


def _cycle(owner: dict[str, str]) -> list[str]:
    for start in sorted(owner):
        seen, node = [], start
        while node in owner:
            node = owner[node]
            if node in seen or node == start:
                return sorted(set(seen + [node, start]))
            seen.append(node)
    return []
