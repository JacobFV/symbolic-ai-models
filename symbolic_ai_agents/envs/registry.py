"""Name to environment. The same three functions the model registry has."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from .base import Environment

__all__ = ["register", "get", "build", "env_names", "REGISTRY"]

REGISTRY: dict[str, type[Environment]] = {}
T = TypeVar("T", bound=type[Environment])


def register(name: str, *, doc: str = "") -> Callable[[T], T]:
    def deco(cls: T) -> T:
        if name in REGISTRY:
            raise ValueError(f"environment {name!r} is already registered")
        cls.name = name
        cls.summary = doc or (cls.__doc__ or "").strip().split("\n")[0]
        REGISTRY[name] = cls
        return cls
    return deco


def get(name: str) -> type[Environment]:
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown environment {name!r}; have {env_names()}") from None


def build(name: str, **kw: Any) -> Environment:
    return get(name)(**kw)


def env_names() -> list[str]:
    return sorted(REGISTRY)
