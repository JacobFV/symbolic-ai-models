"""Name to architecture, with versioned identity.

Every model is registered under a versioned name — ``corefer-001``, ``ilp-001``
— and a *bare* name resolves to the highest version registered under it. So
``--models corefer`` keeps working and means "the current one", while
``corefer-001`` names a specific thing that cannot silently change underneath a
published number.

The reason is that this repo's whole output is a table of numbers attached to
model names, and those numbers only mean something if the name pins the model.
Several results here have already been invalidated by a model changing while its
name did not: `corefer`'s type head went 0.174 -> 0.612 in one commit, and
`workspace` moved from eighth to joint first when a cap was raised. Both were
improvements; both silently redefined what an earlier row meant.

Adding a variant is now cheap and honest. `corefer-002`, or `corefer-prose`, or
`corefer-noprose` sits beside `corefer-001` in the same sweep, and `compare`
prints them as separate rows because they are separate models.
"""

from __future__ import annotations

import re
from typing import Callable, TypeVar

from .base import ModelConfig, SymbolicModel

__all__ = ["register", "get", "build", "model_names", "base_name", "REGISTRY"]

REGISTRY: dict[str, type[SymbolicModel]] = {}
T = TypeVar("T", bound=type[SymbolicModel])

#: ``name-001``, ``name-002``, ``name-prose``. The suffix is free-form after the
#: dash so a variant can be named for what it does rather than counted.
_VERSIONED = re.compile(r"^(?P<base>.+?)-(?P<version>[A-Za-z0-9_]+)$")


def base_name(name: str) -> str:
    """``corefer-001`` -> ``corefer``; an unversioned name is its own base."""
    m = _VERSIONED.match(name)
    return m.group("base") if m else name


def register(name: str, *, doc: str = "") -> Callable[[T], T]:
    def deco(cls: T) -> T:
        if name in REGISTRY:
            raise ValueError(f"model {name!r} is already registered")
        cls.name = name
        cls.summary = doc or (cls.__doc__ or "").strip().split("\n")[0]
        REGISTRY[name] = cls
        return cls
    return deco


def get(name: str) -> type[SymbolicModel]:
    """Exact match first, then the highest version of a bare name.

    Exact-first matters: a model literally registered as ``foo`` must win over
    resolution, or a future ``foo-002`` would hijack a name someone pinned.
    """
    if name in REGISTRY:
        return REGISTRY[name]
    versions = sorted(n for n in REGISTRY if base_name(n) == name)
    if versions:
        return REGISTRY[versions[-1]]
    raise KeyError(f"unknown model {name!r}; have {model_names()}") from None


def build(name: str, cfg: ModelConfig) -> SymbolicModel:
    return get(name)(cfg)


def model_names() -> list[str]:
    return sorted(REGISTRY)
