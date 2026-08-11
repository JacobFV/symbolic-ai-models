"""Name to architecture. One decorator, one lookup, nothing clever."""

from __future__ import annotations

from typing import Callable, TypeVar

from .base import ModelConfig, SymbolicModel

__all__ = ["register", "get", "build", "model_names", "REGISTRY"]

REGISTRY: dict[str, type[SymbolicModel]] = {}
T = TypeVar("T", bound=type[SymbolicModel])


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
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown model {name!r}; have {model_names()}") from None


def build(name: str, cfg: ModelConfig) -> SymbolicModel:
    return get(name)(cfg)


def model_names() -> list[str]:
    return sorted(REGISTRY)
