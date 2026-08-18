"""Entities, the facets they carry, and quantities with units attached.

An entity is an **identity and nothing else**. Everything said about it lives in
a facet keyed by profile, which is what lets one identity be a place, a
jurisdiction and a market area at once without any of those three schemas having
to know about the other two.

Identity is *not* merged across sources. ``wn:dog.n.01``, ``wd:Q144`` and
``cn:/c/en/dog`` stay three entities; that they may be the same thing is an
:class:`~symbolic_ai_core.world.claim.Alignment`, which carries a confidence and
a method and can be wrong. Collapsing them at ingest would destroy the evidence
that says how confident the collapse was.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from .profile import check_profiles

__all__ = ["Entity", "EntityRef", "Facet", "Quantity"]


@dataclass(frozen=True)
class EntityRef:
    """A pointer to an entity by id. Distinguishable from a bare string.

    A role filled with ``"dog"`` and a role filled with ``EntityRef("dog")`` are
    different claims — one is a literal, one is a reference — and a
    representation that cannot tell them apart cannot say whether a predicate is
    about a word or about a thing.
    """

    id: str

    def to_dict(self) -> dict[str, Any]:
        return {"entity": self.id}


@dataclass(frozen=True)
class Quantity:
    """A number that knows its unit, and optionally how sure it is.

    ``unit`` is required and may not be empty. A dimensionless quantity says so
    (``"1"``); a quantity that declines to say is how a metre meets a foot in a
    kernel that adds them.
    """

    value: float
    unit: str
    stderr: float | None = None

    def __post_init__(self) -> None:
        if not self.unit:
            raise ValueError("a Quantity must name its unit; use '1' for "
                             "dimensionless. An unlabelled number is how a "
                             "metre and a foot get added.")

    def to_dict(self) -> dict[str, Any]:
        return {"quantity": {"value": self.value, "unit": self.unit,
                             "stderr": self.stderr}}


@dataclass(frozen=True)
class Facet:
    """What one profile has to say about one entity."""

    profile: str
    values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        check_profiles([self.profile], where="a Facet")

    def to_dict(self) -> dict[str, Any]:
        return {"profile": self.profile, "values": dict(self.values)}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Facet":
        return cls(profile=d["profile"], values=dict(d.get("values") or {}))


@dataclass(frozen=True)
class Entity:
    """An identity plus its facets. Immutable; ``with_facet`` returns a new one."""

    id: str
    types: tuple[str, ...] = ()
    facets: Mapping[str, Facet] = field(default_factory=dict)

    def profiles(self) -> tuple[str, ...]:
        return tuple(sorted(self.facets))

    def has(self, *profiles: str) -> bool:
        return all(p in self.facets for p in profiles)

    def facet(self, profile: str) -> Facet | None:
        return self.facets.get(profile)

    def with_facet(self, facet: Facet) -> "Entity":
        """A copy carrying ``facet``. Replaces any facet of the same profile.

        Returning a copy rather than mutating is what makes
        ``test_kernel_cannot_mutate_input`` provable: a kernel handed a snapshot
        has no way to change what its caller is holding.
        """
        return replace(self, facets={**self.facets, facet.profile: facet})

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "types": list(self.types),
                "facets": {k: v.to_dict() for k, v in sorted(self.facets.items())}}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Entity":
        return cls(id=d["id"], types=tuple(d.get("types") or ()),
                   facets={k: Facet.from_dict(v)
                           for k, v in (d.get("facets") or {}).items()})
