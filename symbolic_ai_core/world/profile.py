"""Semi-overlapping domain subsets, versioned apart from each other.

The alternative — one 50,000-type ontology settled before the first integrated
task runs — is the failure mode this file exists to refuse. A profile is a
*capability name*: a kernel declares that it requires ``scene.body`` and
``core.time`` and provides ``scene.contact``, and matching happens on those
names rather than on a shared schema import.

Only five families are declared here, because only five have a consumer:
``core``, ``language``, ``logic``, ``scene`` and ``geo``. ``economy``,
``politics``, ``biology`` and ``software`` are named in the architecture note
and are deliberately *not* here — a profile with no kernel behind it is a
speculative ontology wearing a registry entry.
"""

from __future__ import annotations

__all__ = ["CORE_PROFILES", "PROFILES", "known_profile", "check_profiles"]

#: The profiles every world carries, whatever domain it is about.
CORE_PROFILES: tuple[str, ...] = (
    "core.identity", "core.type", "core.time", "core.quantity", "core.space",
    "core.claim", "core.uncertainty", "core.provenance",
)

#: Every profile with something behind it, core first.
PROFILES: tuple[str, ...] = CORE_PROFILES + (
    # what a document says, and what part of it said it
    "language.document", "language.span", "language.mention",
    "language.reference", "language.discourse", "language.semantics",
    # terms, propositions, rules and their derivations
    "logic.term", "logic.proposition", "logic.rule", "logic.goal",
    "logic.constraint", "logic.proof",
    # things with a pose, a shape and a mass
    "scene.object", "scene.pose", "scene.shape", "scene.material",
    "scene.body", "scene.joint", "scene.contact", "scene.field",
    # things with a coordinate reference system
    "geo.crs", "geo.geometry", "geo.place", "geo.region", "geo.network",
    "geo.raster", "geo.terrain",
)

_KNOWN = frozenset(PROFILES)


def known_profile(name: str) -> bool:
    return name in _KNOWN


def check_profiles(names, *, where: str = "") -> tuple[str, ...]:
    """Reject an unregistered profile loudly, at the boundary.

    A typo'd profile name would otherwise be a kernel that silently never
    matches, which reads exactly like a kernel that had nothing to contribute —
    this repo has paid for that shape of failure more than once.
    """
    out = tuple(names)
    bad = [n for n in out if n not in _KNOWN]
    if bad:
        raise ValueError(
            f"unknown profile(s) {bad}{' in ' + where if where else ''}; "
            f"registered: {sorted(_KNOWN)}")
    return out
