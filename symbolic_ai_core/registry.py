"""Name to class, with versioned identity. Written once, used by both registries.

Every registered thing in this repo carries a versioned name — ``corefer-001``,
``template-001`` — and a *bare* name resolves to the highest numbered version
registered under it. So ``--models corefer`` keeps working and means "the current
one", while ``corefer-001`` names a specific thing that cannot silently change
underneath a published number.

The reason is that this repo's whole output is a table of numbers attached to
names, and those numbers only mean something if the name pins the thing. Several
results here have already been invalidated by a model changing while its name did
not: ``corefer``'s type head went 0.174 -> 0.612 in one commit, and ``workspace``
moved from eighth to joint first when a cap was raised. Both were improvements;
both silently redefined what an earlier row meant.

Numbered, not merely highest
----------------------------

The convention encourages naming a variant for what it changed — ``corefer-noprose``
reads better than ``corefer-003`` — and a plain string sort puts every such name
above every number, so ``corefer`` would have resolved to ``corefer-noprose``.
The scheme's own recommendation broke its own resolution rule, and silently: a
sweep asking for ``corefer`` would have trained the ablation and labelled it the
model. It was caught when ``ptrgen-argmax``, a control, became what ``ptrgen``
meant.

So a bare name resolves over ``-001``, ``-002``, … only. A word-suffixed variant
is a side experiment and has to be asked for by its full name, which is what
naming it for an ablation implies in the first place.

Why this module exists at all
-----------------------------

That fix was written in ``symbolic_ai_models/models/registry.py`` and then
**hand-carried** into ``symbolic_ai_parsers/base.py`` when the parsers package
wanted the same convention. Two copies of a rule whose entire job is to keep
published names honest is exactly the arrangement this repo has already watched
go wrong once — see the note in ``models/omegaclaw/base.py`` about ``routes.follow``
being reimplemented and the two copies left to drift. It exists here once now,
and the callers keep their own ``register``/``build`` signatures, which differ:
a model is built from a ``ModelConfig``, a parser from keywords, and a parser
carries a ``learned`` flag that a model does not.
"""

from __future__ import annotations

import re
from typing import Generic, TypeVar

__all__ = ["VersionedRegistry", "base_name"]

T = TypeVar("T")

#: ``name-001``, ``name-002``, ``name-prose``. The suffix is free-form after the
#: dash so a variant can be named for what it does rather than counted.
_VERSIONED = re.compile(r"^(?P<base>.+?)-(?P<version>[A-Za-z0-9_]+)$")


def base_name(name: str) -> str:
    """``corefer-001`` -> ``corefer``; an unversioned name is its own base."""
    m = _VERSIONED.match(name)
    return m.group("base") if m else name


class VersionedRegistry(Generic[T]):
    """A name -> class mapping under the resolution rule above.

    ``noun`` is what the thing is called in error messages — "model", "parser" —
    so a failed lookup names the registry it failed in rather than leaving the
    reader to guess which of the two raised.

    :attr:`entries` is a plain dict and is deliberately public: both callers
    export it as ``REGISTRY`` and code across the repo subscripts and iterates
    it directly.
    """

    def __init__(self, noun: str) -> None:
        self.noun = noun
        self.entries: dict[str, type[T]] = {}

    def add(self, name: str, cls: type[T]) -> None:
        """Register ``cls`` under ``name``. A duplicate name is an error, not a
        silent overwrite — an overwrite is how a published row gets redefined."""
        if name in self.entries:
            raise ValueError(f"{self.noun} {name!r} is already registered")
        self.entries[name] = cls

    def get(self, name: str) -> type[T]:
        """Exact match first, then the highest *numbered* version of a bare name.

        Exact-first matters: something literally registered as ``foo`` must win
        over resolution, or a future ``foo-002`` would hijack a name someone
        pinned.
        """
        if name in self.entries:
            return self.entries[name]
        numbered = [(int(m.group("version")), n) for n in self.entries
                    if (m := _VERSIONED.match(n)) and m.group("base") == name
                    and m.group("version").isdigit()]
        if numbered:
            return self.entries[max(numbered)[1]]
        named = sorted(n for n in self.entries if base_name(n) == name)
        if named:
            raise KeyError(
                f"{name!r} has no numbered version; its variants are "
                f"{named} and must be named in full") from None
        raise KeyError(f"unknown {self.noun} {name!r}; have {self.names()}") from None

    def names(self) -> list[str]:
        return sorted(self.entries)
