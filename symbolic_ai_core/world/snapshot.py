"""A world at a point in the system's knowledge. Arbitrary topology, on purpose.

A snapshot holds entities, the claims about them and the alignments between
sources. **Nothing here is required to be acyclic**: ``a adjacent_to b`` and
``b adjacent_to a`` are both ordinary claims, a road network is exactly that
shape, and a representation that refused it would be a representation of trees.

Contradictions are kept. Two sources that disagree produce two claims, and a
reconciled ``belief_view`` is *derived* for a particular task, authority policy
and time — it is never written back over the evidence. Collapsing at ingest
throws away the one thing that could later say which source was right.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping

from .claim import Alignment, Claim
from .entity import Entity

__all__ = ["WorldSnapshot"]


@dataclass(frozen=True)
class WorldSnapshot:
    """Entities, claims, alignments. Immutable; deltas produce new snapshots."""

    entities: Mapping[str, Entity] = field(default_factory=dict)
    claims: tuple[Claim, ...] = ()
    alignments: tuple[Alignment, ...] = ()

    # ---- reading -----------------------------------------------------
    def profiles(self) -> tuple[str, ...]:
        """Every profile any entity in this world carries."""
        out: set[str] = set()
        for e in self.entities.values():
            out.update(e.facets)
        return tuple(sorted(out))

    def provides(self, required: Iterable[str]) -> bool:
        have = set(self.profiles())
        return set(required) <= have

    def require(self, required: Iterable[str], *, who: str = "") -> None:
        """Refuse loudly when a kernel's capabilities are not present.

        A kernel that silently produced nothing because a facet was missing
        reads exactly like a kernel that had nothing to say, and this repo has
        twice mistaken one for the other.
        """
        missing = sorted(set(required) - set(self.profiles()))
        if missing:
            raise KeyError(
                f"{who or 'this consumer'} requires profile(s) {missing} which "
                f"this world does not carry; it has {list(self.profiles())}")

    def entity(self, entity_id: str) -> Entity:
        try:
            return self.entities[entity_id]
        except KeyError:
            raise KeyError(f"no entity {entity_id!r} in this world") from None

    def claims_about(self, entity_id: str) -> tuple[Claim, ...]:
        return tuple(c for c in self.claims if entity_id in c.entities())

    def neighbours(self, entity_id: str, *, predicate: str | None = None
                   ) -> tuple[str, ...]:
        """Every entity reachable by one claim. **May include ``entity_id``.**

        Self-loops and cycles are represented, not filtered — a river that flows
        into itself is a data error, but a bus route that returns to its depot
        is not, and this layer cannot tell them apart.
        """
        out: list[str] = []
        for c in self.claims:
            if predicate is not None and c.predicate != predicate:
                continue
            ids = c.entities()
            if entity_id in ids:
                out.extend(i for i in ids if i != entity_id or ids.count(i) > 1)
        return tuple(dict.fromkeys(out))

    def project(self, profiles: Iterable[str]) -> "WorldSnapshot":
        """A view carrying only these profiles' facets. Claims are untouched.

        This is how ``scene_view``, ``geo_view`` and ``logic_view`` are produced:
        one world, several projections, no copies of the identities.
        """
        keep = set(profiles)
        return replace(self, entities={
            eid: replace(e, facets={k: v for k, v in e.facets.items() if k in keep})
            for eid, e in self.entities.items()})

    # ---- wire --------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {"entities": {k: v.to_dict()
                             for k, v in sorted(self.entities.items())},
                "claims": [c.to_dict() for c in self.claims],
                "alignments": [a.to_dict() for a in self.alignments]}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "WorldSnapshot":
        from ..artifact.value import Provenance
        aligns = []
        for a in d.get("alignments") or []:
            p = a.get("provenance") or {}
            aligns.append(Alignment(
                left=a["left"], right=a["right"],
                relation=a.get("relation", "possibly_same"),
                confidence=a.get("confidence"), method=a.get("method", ""),
                evidence=tuple(a.get("evidence") or ()),
                provenance=Provenance(
                    producer=p.get("producer", ""),
                    inputs=tuple(p.get("inputs") or ()),
                    source=p.get("source", ""),
                    source_version=p.get("source_version", ""),
                    license=p.get("license", ""), method=p.get("method", ""),
                derivation=p.get("derivation", ""))))
        return cls(
            entities={k: Entity.from_dict(v)
                      for k, v in (d.get("entities") or {}).items()},
            claims=tuple(Claim.from_dict(c) for c in (d.get("claims") or [])),
            alignments=tuple(aligns))
