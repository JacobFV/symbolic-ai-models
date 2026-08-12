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
    """Exact match first, then the highest *numbered* version of a bare name.

    Exact-first matters: a model literally registered as ``foo`` must win over
    resolution, or a future ``foo-002`` would hijack a name someone pinned.

    **Numbered, not merely highest.** The convention this registry exists to
    support encourages naming a variant for what it changed — ``corefer-noprose``
    reads better than ``corefer-003`` — and a plain string sort puts every such
    name above every number, so ``corefer`` would have resolved to
    ``corefer-noprose``. The scheme's own recommendation broke its own
    resolution rule, and silently: a sweep asking for ``corefer`` would have
    trained the ablation and labelled it the model. It was caught when
    ``ptrgen-argmax``, a control, became what ``ptrgen`` meant.

    So a bare name resolves over ``-001``, ``-002``, … only. A word-suffixed
    variant is a side experiment and has to be asked for by its full name, which
    is what naming it for an ablation implies in the first place.
    """
    if name in REGISTRY:
        return REGISTRY[name]
    numbered = [(int(m.group("version")), n) for n in REGISTRY
                if (m := _VERSIONED.match(n)) and m.group("base") == name
                and m.group("version").isdigit()]
    if numbered:
        return REGISTRY[max(numbered)[1]]
    named = sorted(n for n in REGISTRY if base_name(n) == name)
    if named:
        raise KeyError(
            f"{name!r} has no numbered version; its variants are "
            f"{named} and must be named in full") from None
    raise KeyError(f"unknown model {name!r}; have {model_names()}") from None


def build(name: str, cfg: ModelConfig) -> SymbolicModel:
    return get(name)(cfg)


def model_names() -> list[str]:
    return sorted(REGISTRY)
