"""The term language: a small ``Expr``, shaped like Lean 4's.

Lean's own ``Expr`` has twelve constructors; this has eight, and the eight are a
subset of Lean's rather than a reinterpretation of them:

===========  =====================  ==================================
here         Lean 4                 why it is needed
===========  =====================  ==================================
``Sort``     ``Expr.sort``          ``Prop`` is ``Sort 0``
``Const``    ``Expr.const``         every declared symbol
``Lit``      ``Expr.lit``           a label, verbatim, so the round trip
                                    can be the identity
``Var``      ``Expr.bvar``          de Bruijn, for ``Lam`` / ``Pi``
``MVar``     ``Expr.mvar``          elaboration without metavariables is
                                    not elaboration
``App``      ``Expr.app``           one argument at a time, as in Lean
``Lam``      ``Expr.lam``           unused by the curriculum, kept so the
                                    kernel is a kernel and not a matcher
``Pi``       ``Expr.forallE``       function types; ``a → b`` is a
                                    non-dependent ``Pi``
===========  =====================  ==================================

``notes/decisions/2026-08-14-lean-ir-preregistration.md`` names six of these —
``Sort | Const | Var | App | Lam | Pi``. ``MVar`` and ``Lit`` are additions and
they are written down here rather than absorbed silently. ``MVar`` is what makes
the difference between a typechecker and an *elaborator*: the gating diagnostic
asks whether a candidate filler is possible, which is a question about whether
an assignment to the unknowns exists, and that question cannot even be stated
without metavariables. ``Lit`` is what makes ``expr_to_graph(graph_to_expr(g))``
the identity — a label is an arbitrary string and encoding it as a ``Const``
name would collide with the signature's own constants.

Everything is frozen and hashable. The kernel takes no locks and mutates no
term; all mutable state lives in :class:`~symbolic_ai_lean.kernel.MetaCtx`,
which is what makes a candidate check cheap to undo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

__all__ = ["Expr", "Sort", "Const", "Lit", "Var", "MVar", "App", "Lam", "Pi",
           "apps", "spine", "arrow", "arrow_parts", "PROP", "TYPE"]


class Expr:
    """Base class. Every subclass is a frozen dataclass, so ``==`` is structural."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class Sort(Expr):
    """``Sort 0`` is ``Prop``; ``Sort 1`` is ``Type``."""

    level: int = 0


@dataclass(frozen=True, slots=True)
class Const(Expr):
    """A declared name. Signature constants and the episode's symbols share this
    constructor, and the elaborator keeps them apart by namespace prefix rather
    than by type, exactly as Lean keeps ``List.cons`` apart from ``cons``."""

    name: str


@dataclass(frozen=True, slots=True)
class Lit(Expr):
    """A label, verbatim. Never interpreted, never split, never normalised —
    the tokenizer's deleted underscore is in this repo's lesson list."""

    value: str


@dataclass(frozen=True, slots=True)
class Var(Expr):
    """A de Bruijn index into the binders above it."""

    idx: int


@dataclass(frozen=True, slots=True)
class MVar(Expr):
    """An unknown, to be solved by unification. Assignment lives in the
    :class:`MetaCtx`, not here, so the same term can be checked under many
    assignments and rolled back between them."""

    idx: int


@dataclass(frozen=True, slots=True)
class App(Expr):
    """One argument. ``f a b`` is ``App(App(f, a), b)``, as in Lean."""

    fn: Expr
    arg: Expr


@dataclass(frozen=True, slots=True)
class Lam(Expr):
    name: str
    dom: Expr
    body: Expr


@dataclass(frozen=True, slots=True)
class Pi(Expr):
    """``Pi("_", a, b)`` is ``a → b`` when ``b`` does not mention ``Var(0)``."""

    name: str
    dom: Expr
    body: Expr


#: ``Prop`` — where the curriculum's predicates land.
PROP = Sort(0)
#: ``Type`` — where its object types land.
TYPE = Sort(1)


def apps(head: Expr, args: Iterable[Expr]) -> Expr:
    """``head a1 a2 …``, left-nested."""
    out = head
    for a in args:
        out = App(out, a)
    return out


def spine(e: Expr) -> tuple[Expr, list[Expr]]:
    """Split ``f a1 … an`` into ``(f, [a1, …, an])``."""
    args: list[Expr] = []
    while isinstance(e, App):
        args.append(e.arg)
        e = e.fn
    args.reverse()
    return e, args


def arrow(doms: Iterable[Expr], cod: Expr) -> Expr:
    """``d1 → d2 → … → cod``. Non-dependent, so no index shifting is needed."""
    out = cod
    for d in reversed(list(doms)):
        out = Pi("_", d, out)
    return out


def arrow_parts(e: Expr) -> tuple[list[Expr], Expr]:
    """The inverse of :func:`arrow` for non-dependent chains."""
    doms: list[Expr] = []
    while isinstance(e, Pi):
        doms.append(e.dom)
        e = e.body
    return doms, e


def pretty(e: Expr) -> str:
    """Lean-ish source, for error messages, tests and the ``.lean`` emitter."""
    if isinstance(e, Sort):
        return "Prop" if e.level == 0 else ("Type" if e.level == 1
                                            else f"Sort {e.level}")
    if isinstance(e, Const):
        return e.name
    if isinstance(e, Lit):
        return '"' + e.value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(e, Var):
        return f"#{e.idx}"
    if isinstance(e, MVar):
        return f"?m{e.idx}"
    if isinstance(e, Pi):
        return f"({pretty(e.dom)} → {pretty(e.body)})"
    if isinstance(e, Lam):
        return f"(fun {e.name} : {pretty(e.dom)} => {pretty(e.body)})"
    if isinstance(e, App):
        head, args = spine(e)
        return "(" + " ".join([pretty(head)] + [pretty(a) for a in args]) + ")"
    raise TypeError(f"not an Expr: {e!r}")            # pragma: no cover
