"""Name to agent. One decorator, one lookup, nothing clever."""

from __future__ import annotations

from typing import Any, Callable, Mapping, TypeVar

from .base import Agent

__all__ = ["register", "get", "build", "agent_names", "REGISTRY"]

REGISTRY: dict[str, type[Agent]] = {}
T = TypeVar("T", bound=type[Agent])


def register(name: str, *, doc: str = "") -> Callable[[T], T]:
    def deco(cls: T) -> T:
        if name in REGISTRY:
            raise ValueError(f"agent {name!r} is already registered")
        cls.name = name
        cls.summary = doc or (cls.__doc__ or "").strip().split("\n")[0]
        REGISTRY[name] = cls
        return cls
    return deco


def get(name: str) -> type[Agent]:
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown agent {name!r}; have {agent_names()}") from None


def build(name: str, extra: Mapping[str, Any] | None = None) -> Agent:
    return get(name)(extra)


def agent_names() -> list[str]:
    return sorted(REGISTRY)
