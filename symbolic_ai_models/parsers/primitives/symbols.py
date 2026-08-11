"""Symbols: one agent's internal representation of what it was told.

Ported verbatim from symbolic-ai-001 (`agents/base_symbolic_agent_002/symbols.py`).
It is this directory's representation, and the agents that reason over structure
import it from here rather than from a shared utils dump.

A ``Symbol`` is an immutable, hashable, typed, inspectable, serializable node.
Composite symbols hold other symbols in ``value`` (as a tuple), so trees,
records, applications and graphs are all built from the same primitive.

This used to live in ``core/`` and cross the agent/environment boundary, which
meant environments built observations out of the very constructors the agents
pattern-matched on -- the agent was handed the parse it was supposed to be
credited with computing. Symbols are now *this release's* representation: an
agent that wants structure builds it here, out of text, with ``parse.py``.

Nothing here knows about tensors, tasks, rewards or learning.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Sequence

__all__ = [
    "Symbol",
    "Tok", "Str", "Num", "Ident", "Pred", "Rel", "Tup", "Lst",
    "Node", "Ref", "App", "Rec", "Dist", "Nil",
    "walk", "leaves", "size", "depth", "sexpr", "to_jsonable", "from_jsonable",
]

# Symbol.type tags used by the framework. Environments may add their own tags;
# the framework never switches on unknown tags, it only carries them.
PRIMITIVE_TYPES = frozenset({"token", "str", "num", "ident", "nil"})
COMPOSITE_TYPES = frozenset({"tuple", "list", "pred", "rel", "node", "app", "record", "dist"})


def _freeze(v: Any) -> Any:
    if isinstance(v, Symbol):
        return v
    if isinstance(v, (list, tuple)):
        return tuple(_freeze(x) for x in v)
    if isinstance(v, dict):
        return tuple(sorted(((str(k), _freeze(x)) for k, x in v.items()), key=lambda kv: kv[0]))
    return v


class _Meta(dict):
    """dict that hashes by its items so Symbol stays hashable."""

    def __hash__(self) -> int:  # type: ignore[override]
        return hash(tuple(sorted((k, repr(v)) for k, v in self.items())))


@dataclass(frozen=True)
class Symbol:
    """type: what kind of symbol; value: payload (scalar or tuple of Symbols);
    meta: non-semantic annotations (provenance, spans, logprobs, ids)."""

    type: str
    value: Any = None
    meta: Mapping[str, Any] = field(default_factory=_Meta, compare=False, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _freeze(self.value))
        if not isinstance(self.meta, _Meta):
            object.__setattr__(self, "meta", _Meta(self.meta or {}))

    # ---- structure -------------------------------------------------
    @property
    def children(self) -> tuple["Symbol", ...]:
        """Sub-symbols, including the values of named fields (record/app), so
        traversal reaches every symbol in the structure."""
        if not isinstance(self.value, tuple):
            return ()
        out: list[Symbol] = []
        for x in self.value:
            if isinstance(x, Symbol):
                out.append(x)
            elif isinstance(x, tuple) and len(x) == 2 and isinstance(x[0], str) and isinstance(x[1], Symbol):
                out.append(x[1])
        return tuple(out)

    @property
    def is_composite(self) -> bool:
        return bool(self.children)

    def with_meta(self, **kw: Any) -> "Symbol":
        m = _Meta(self.meta)
        m.update(kw)
        return Symbol(self.type, self.value, m)

    def field(self, name: str, default: Any = None) -> Any:
        """Field lookup for record/app symbols (value is a tuple of (key, Symbol))."""
        if isinstance(self.value, tuple):
            for item in self.value:
                if isinstance(item, tuple) and len(item) == 2 and item[0] == name:
                    return item[1]
        return default

    def __iter__(self) -> Iterator["Symbol"]:
        return iter(self.children)

    def __len__(self) -> int:
        return len(self.children)

    def __bool__(self) -> bool:
        # a symbol is always a thing; without this, atoms (0 children) are falsy
        return True

    # ---- rendering -------------------------------------------------
    def __repr__(self) -> str:
        return sexpr(self)

    def __str__(self) -> str:
        return sexpr(self)


# --------------------------------------------------------------------------
# constructors (one per symbol kind the framework ships with)
# --------------------------------------------------------------------------
def Tok(t: Any, **meta: Any) -> Symbol:
    """A token: an atom drawn from a finite vocabulary."""
    return Symbol("token", t, meta)


def Str(s: str, **meta: Any) -> Symbol:
    return Symbol("str", s, meta)


def Num(x: float | int, **meta: Any) -> Symbol:
    return Symbol("num", x, meta)


def Ident(name: str, **meta: Any) -> Symbol:
    """A name/variable/constant identifier."""
    return Symbol("ident", name, meta)


def Nil(**meta: Any) -> Symbol:
    return Symbol("nil", None, meta)


def Pred(name: str, *args: Symbol, **meta: Any) -> Symbol:
    """Predicate application: on(a, b), even(x)."""
    return Symbol("pred", (name, *args), meta)


def Rel(name: str, src: Symbol, dst: Symbol, **meta: Any) -> Symbol:
    """Binary relation edge (a graph edge by another name)."""
    return Symbol("rel", (name, src, dst), meta)


def Tup(*xs: Symbol, **meta: Any) -> Symbol:
    return Symbol("tuple", xs, meta)


def Lst(xs: Iterable[Symbol], **meta: Any) -> Symbol:
    return Symbol("list", tuple(xs), meta)


def Node(label: str, children: Sequence[Symbol] = (), **meta: Any) -> Symbol:
    """AST / tree node."""
    return Symbol("node", (label, *children), meta)


def Ref(graph: str, key: Any, **meta: Any) -> Symbol:
    """Reference into an external structure the environment owns (graph, page, repo)."""
    return Symbol("ref", (graph, key), meta)


def App(fn: str, **kwargs: Symbol) -> Symbol:
    """Function/operator application with named arguments.

    ``App("search", query=Str("..."))`` -> Call(function="search", args={...})
    """
    meta = kwargs.pop("_meta", {})  # type: ignore[assignment]
    return Symbol("app", (fn, *sorted(((k, v) for k, v in kwargs.items()), key=lambda kv: kv[0])), meta)  # type: ignore[arg-type]


def Rec(**fields: Symbol) -> Symbol:
    """Structured record with named fields."""
    meta = fields.pop("_meta", {})  # type: ignore[assignment]
    return Symbol("record", tuple(sorted(fields.items(), key=lambda kv: kv[0])), meta)  # type: ignore[arg-type]


def Dist(support: Sequence[Symbol], probs: Sequence[float], **meta: Any) -> Symbol:
    """A distribution *over* symbols, itself a symbol.

    This is what lets supervised prediction be an *action*: the agent emits a
    predictive distribution and the environment scores it (log p).
    """
    assert len(support) == len(probs)
    m = dict(meta)
    m["probs"] = tuple(float(p) for p in probs)
    return Symbol("dist", tuple(support), m)


def dist_probs(sym: Symbol) -> tuple[float, ...]:
    return tuple(sym.meta.get("probs", ()))


# --------------------------------------------------------------------------
# traversal / inspection
# --------------------------------------------------------------------------
def walk(s: Symbol) -> Iterator[Symbol]:
    yield s
    for c in s.children:
        yield from walk(c)


def leaves(s: Symbol) -> Iterator[Symbol]:
    if not s.children:
        yield s
    for c in s.children:
        yield from leaves(c)


def size(s: Symbol) -> int:
    return sum(1 for _ in walk(s))


def depth(s: Symbol) -> int:
    return 1 + max((depth(c) for c in s.children), default=0)


def _atom_repr(v: Any) -> str:
    if isinstance(v, str):
        return v if v.isidentifier() or v.isdigit() else json.dumps(v)
    return repr(v)


def sexpr(s: Symbol) -> str:
    """Compact, human-readable, paste-able rendering."""
    if s.type in ("token", "str", "num", "ident"):
        return _atom_repr(s.value)
    if s.type == "nil":
        return "()"
    if s.type in ("pred", "rel", "node"):
        head, *rest = s.value
        inner = " ".join(sexpr(x) for x in rest if isinstance(x, Symbol))
        return f"({head}{' ' + inner if inner else ''})"
    if s.type == "tuple":
        return "(" + " ".join(sexpr(x) for x in s.children) + ")"
    if s.type == "list":
        return "[" + " ".join(sexpr(x) for x in s.children) + "]"
    if s.type == "ref":
        return f"@{s.value[0]}:{s.value[1]}"
    if s.type == "app":
        fn, *kvs = s.value
        args = ", ".join(f"{k}={sexpr(v)}" for k, v in kvs)
        return f"{fn}({args})"
    if s.type == "record":
        return "{" + ", ".join(f"{k}: {sexpr(v)}" for k, v in s.value) + "}"
    if s.type == "dist":
        ps = dist_probs(s)
        top = sorted(zip(s.children, ps), key=lambda t: -t[1])[:3]
        return "Dist{" + ", ".join(f"{sexpr(x)}:{p:.3f}" for x, p in top) + (", ...}" if len(ps) > 3 else "}")
    return f"<{s.type} {s.value!r}>"


# --------------------------------------------------------------------------
# serialization (trajectories must round-trip through JSONL)
# --------------------------------------------------------------------------
def to_jsonable(s: Any) -> Any:
    if isinstance(s, Symbol):
        out: dict[str, Any] = {"t": s.type}
        v = s.value
        if isinstance(v, tuple):
            out["v"] = [to_jsonable(x) for x in v]
        else:
            out["v"] = v
        if s.meta:
            out["m"] = {k: _json_safe(x) for k, x in s.meta.items()}
        return out
    if isinstance(s, tuple):
        return {"__kv__": [to_jsonable(x) for x in s]} if len(s) == 2 and isinstance(s[0], str) else [to_jsonable(x) for x in s]
    return s


def _json_safe(x: Any) -> Any:
    try:
        json.dumps(x)
        return x
    except TypeError:
        return repr(x)


def from_jsonable(d: Any) -> Any:
    if isinstance(d, dict) and "__kv__" in d:
        k, v = d["__kv__"]
        return (k, from_jsonable(v))
    if isinstance(d, dict) and "t" in d:
        v = d.get("v")
        if isinstance(v, list):
            v = tuple(from_jsonable(x) for x in v)
        return Symbol(d["t"], v, d.get("m", {}))
    if isinstance(d, list):
        return [from_jsonable(x) for x in d]
    return d
