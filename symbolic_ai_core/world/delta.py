"""What a kernel returns instead of a mutation.

A kernel is never handed a mutable world and left to race the other kernels to
overwrite it. It returns a **delta** — entities to add, facets to set, claims to
assert, claims to retract — and something above it decides how deltas combine.
That decision is property-specific and cannot be defaulted: forces sum,
probabilities fuse, poses need covariance, proof validity is a veto, and
averaging two arbitrary state vectors is meaningless.

``apply`` therefore does the *unambiguous* half only — union of entities and
claims, facet-by-facet replacement — and refuses when two deltas set the same
facet of the same entity to different values. That refusal is the point at which
a fusion policy has to be named rather than assumed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from .claim import Alignment, Claim
from .entity import Entity, Facet
from .snapshot import WorldSnapshot

__all__ = ["WorldDelta"]


@dataclass(frozen=True)
class WorldDelta:
    """Additions and retractions. Applying one returns a *new* snapshot."""

    entities: tuple[Entity, ...] = ()
    facets: Mapping[str, tuple[Facet, ...]] = field(default_factory=dict)
    claims: tuple[Claim, ...] = ()
    alignments: tuple[Alignment, ...] = ()
    retracted: tuple[int, ...] = ()          #: indices into the snapshot's claims

    def is_empty(self) -> bool:
        return not (self.entities or self.facets or self.claims
                    or self.alignments or self.retracted)

    def apply(self, world: WorldSnapshot) -> WorldSnapshot:
        """``world`` is not modified. The returned snapshot is a new object."""
        ents = dict(world.entities)
        for e in self.entities:
            ents[e.id] = e if e.id not in ents else _merge_entity(ents[e.id], e)
        for eid, facets in self.facets.items():
            base = ents.get(eid, Entity(id=eid))
            for f in facets:
                base = base.with_facet(f)
            ents[eid] = base
        kept = tuple(c for i, c in enumerate(world.claims)
                     if i not in set(self.retracted))
        return replace(world, entities=ents, claims=kept + self.claims,
                       alignments=world.alignments + self.alignments)

    def to_dict(self) -> dict[str, Any]:
        return {"entities": [e.to_dict() for e in self.entities],
                "facets": {k: [f.to_dict() for f in v]
                           for k, v in sorted(self.facets.items())},
                "claims": [c.to_dict() for c in self.claims],
                "alignments": [a.to_dict() for a in self.alignments],
                "retracted": list(self.retracted)}


def _merge_entity(old: Entity, new: Entity) -> Entity:
    """Union the types, replace facets profile by profile.

    Replacing rather than merging *within* a profile is deliberate: two values
    for ``scene.pose`` are two hypotheses, and picking one silently is exactly
    the last-writer-wins that the claim/fuse split exists to prevent. A caller
    that has two poses should be emitting two claims and naming a fusion rule.
    """
    facets = dict(old.facets)
    facets.update(new.facets)
    return Entity(id=old.id,
                  types=tuple(dict.fromkeys(old.types + new.types)),
                  facets=facets)
