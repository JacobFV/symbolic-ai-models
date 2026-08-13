"""Name to architecture, with versioned identity.

The resolution rule and the reasoning behind it live in
:mod:`symbolic_ai_core.registry`, because ``symbolic_ai_parsers`` needs the same
rule and used to carry a hand-copied second implementation of it. What is here
is the model-shaped surface over it: ``register`` sets the class attributes the
sweep prints, and ``build`` takes a :class:`ModelConfig`.

Adding a variant is cheap and honest. ``corefer-002``, or ``corefer-prose``, or
``corefer-noprose`` sits beside ``corefer-001`` in the same sweep, and ``compare``
prints them as separate rows because they are separate models.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from symbolic_ai_core.registry import VersionedRegistry, base_name

from .base import ModelConfig, SymbolicModel

__all__ = ["register", "get", "build", "model_names", "base_name", "REGISTRY"]

_REGISTRY: VersionedRegistry[SymbolicModel] = VersionedRegistry("model")

#: The same dict the registry holds, not a copy — the CLI and the tests read it
#: directly and would otherwise see a snapshot taken at import time.
REGISTRY: dict[str, type[SymbolicModel]] = _REGISTRY.entries

T = TypeVar("T", bound=type[SymbolicModel])


def register(name: str, *, doc: str = "") -> Callable[[T], T]:
    def deco(cls: T) -> T:
        _REGISTRY.add(name, cls)
        cls.name = name
        cls.summary = doc or (cls.__doc__ or "").strip().split("\n")[0]
        return cls
    return deco


def get(name: str) -> type[SymbolicModel]:
    """Exact match first, then the highest numbered version of a bare name."""
    return _REGISTRY.get(name)


def build(name: str, cfg: ModelConfig) -> SymbolicModel:
    return get(name)(cfg)


def model_names() -> list[str]:
    return _REGISTRY.names()
