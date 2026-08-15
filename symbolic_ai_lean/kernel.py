"""The kernel: whnf, unification with metavariables, inference, and checking.

Small, native, **total**, and it runs inside a sweep — which real Lean cannot,
for the reason ``APPROACH.md`` gives: the whole premise here is a CPU cost
budget, and a subprocess elaborator per candidate filler would end the line on
arithmetic rather than on evidence. Real Lean 4 is an outside conformance
oracle (:mod:`symbolic_ai_lean.emit`), never a dependency of a number.

Total, concretely: every recursive function is fuel-bounded and every loop has a
decreasing measure. A kernel that can diverge on an adversarial term is a kernel
that can hang a 179-lesson sweep, and the failure would look like a slow machine
rather than a bug.

The one piece of mutable state is :class:`MetaCtx`. It carries the assignment
*and a trail*, so a speculative unification can be undone in O(number of
assignments made). That is what makes the gating diagnostic affordable: filling
a hole with each of ~55 candidates is 55 speculative unifications against one
elaboration, not 55 elaborations.
"""

from __future__ import annotations

from .expr import (App, Const, Expr, Lam, Lit, MVar, Pi, Sort, Var, pretty,
                   spine)

__all__ = ["MetaCtx", "TypeError_", "whnf", "unify", "infer", "check",
           "FUEL"]

#: Reduction steps allowed before :func:`whnf` gives up and returns what it has.
#: Nothing the elaborator builds needs more than a handful; the bound exists so
#: that a hand-written adversarial term cannot spin.
FUEL = 1_000


class TypeError_(Exception):
    """Raised by :func:`infer` when a term has no type. Named with a trailing
    underscore so it cannot shadow the builtin in a ``from … import *``."""


class MetaCtx:
    """Metavariable assignment plus an undo trail.

    ``bind`` records the index it assigned; ``undo(mark)`` unbinds everything
    assigned since ``mark``. Assignments are never overwritten in place, so a
    ``deref`` chain is acyclic by construction (``bind`` refuses a binding whose
    right-hand side mentions the variable being bound).
    """

    __slots__ = ("assign", "trail", "_n")

    def __init__(self) -> None:
        self.assign: dict[int, Expr] = {}
        self.trail: list[int] = []
        self._n = 0

    def fresh(self) -> MVar:
        self._n += 1
        return MVar(self._n - 1)

    @property
    def n_metas(self) -> int:
        return self._n

    def mark(self) -> int:
        return len(self.trail)

    def undo(self, mark: int) -> None:
        while len(self.trail) > mark:
            del self.assign[self.trail.pop()]

    def deref(self, e: Expr) -> Expr:
        """Follow assignments at the head. Bounded by the number of metas."""
        seen = 0
        while isinstance(e, MVar) and e.idx in self.assign:
            e = self.assign[e.idx]
            seen += 1
            if seen > self._n + 1:                    # pragma: no cover
                raise RuntimeError("cyclic metavariable assignment")
        return e

    def bind(self, idx: int, e: Expr) -> None:
        self.assign[idx] = e
        self.trail.append(idx)

    def instantiate(self, e: Expr, fuel: int = FUEL) -> Expr:
        """Replace every assigned metavariable, everywhere, once."""
        if fuel <= 0:                                 # pragma: no cover
            return e
        e = self.deref(e)
        if isinstance(e, App):
            return App(self.instantiate(e.fn, fuel - 1),
                       self.instantiate(e.arg, fuel - 1))
        if isinstance(e, Pi):
            return Pi(e.name, self.instantiate(e.dom, fuel - 1),
                      self.instantiate(e.body, fuel - 1))
        if isinstance(e, Lam):
            return Lam(e.name, self.instantiate(e.dom, fuel - 1),
                       self.instantiate(e.body, fuel - 1))
        return e


# ---------------------------------------------------------------------------
# de Bruijn plumbing
# ---------------------------------------------------------------------------
def _lift(e: Expr, by: int, cutoff: int = 0) -> Expr:
    if isinstance(e, Var):
        return Var(e.idx + by) if e.idx >= cutoff else e
    if isinstance(e, App):
        return App(_lift(e.fn, by, cutoff), _lift(e.arg, by, cutoff))
    if isinstance(e, Pi):
        return Pi(e.name, _lift(e.dom, by, cutoff), _lift(e.body, by, cutoff + 1))
    if isinstance(e, Lam):
        return Lam(e.name, _lift(e.dom, by, cutoff), _lift(e.body, by, cutoff + 1))
    return e


def _subst(body: Expr, val: Expr, idx: int = 0) -> Expr:
    """``body[idx := val]``, the substitution a beta step performs."""
    if isinstance(body, Var):
        if body.idx == idx:
            return _lift(val, idx)
        return Var(body.idx - 1) if body.idx > idx else body
    if isinstance(body, App):
        return App(_subst(body.fn, val, idx), _subst(body.arg, val, idx))
    if isinstance(body, Pi):
        return Pi(body.name, _subst(body.dom, val, idx),
                  _subst(body.body, val, idx + 1))
    if isinstance(body, Lam):
        return Lam(body.name, _subst(body.dom, val, idx),
                   _subst(body.body, val, idx + 1))
    return body


# ---------------------------------------------------------------------------
# reduction
# ---------------------------------------------------------------------------
def whnf(e: Expr, ctx: MetaCtx | None = None, fuel: int = FUEL) -> Expr:
    """Weak head normal form: beta only. Fuel-bounded, hence total."""
    while fuel > 0:
        fuel -= 1
        if ctx is not None:
            e = ctx.deref(e)
        if isinstance(e, App):
            fn = whnf(e.fn, ctx, fuel)
            if isinstance(fn, Lam):
                e = _subst(fn.body, e.arg)
                continue
            return App(fn, e.arg) if fn is not e.fn else e
        return e
    return e                                          # pragma: no cover


# ---------------------------------------------------------------------------
# unification
# ---------------------------------------------------------------------------
def _occurs(idx: int, e: Expr, ctx: MetaCtx, fuel: int = FUEL) -> bool:
    if fuel <= 0:                                     # pragma: no cover
        return True
    e = ctx.deref(e)
    if isinstance(e, MVar):
        return e.idx == idx
    if isinstance(e, App):
        return (_occurs(idx, e.fn, ctx, fuel - 1)
                or _occurs(idx, e.arg, ctx, fuel - 1))
    if isinstance(e, (Pi, Lam)):
        return (_occurs(idx, e.dom, ctx, fuel - 1)
                or _occurs(idx, e.body, ctx, fuel - 1))
    return False


def unify(a: Expr, b: Expr, ctx: MetaCtx, fuel: int = FUEL) -> bool:
    """Structural unification up to beta, assigning metavariables.

    Returns ``False`` rather than raising: a failed unification is the normal
    answer to "can this filler go here", not an error. On failure the trail is
    **not** rewound — the caller owns the mark, because a caller that is testing
    fifty-five candidates wants one mark and fifty-five undos, not fifty-five
    marks.
    """
    if fuel <= 0:                                     # pragma: no cover
        return False
    a, b = whnf(a, ctx, fuel), whnf(b, ctx, fuel)
    if isinstance(a, MVar):
        if isinstance(b, MVar) and b.idx == a.idx:
            return True
        if _occurs(a.idx, b, ctx):
            return False
        ctx.bind(a.idx, b)
        return True
    if isinstance(b, MVar):
        if _occurs(b.idx, a, ctx):
            return False
        ctx.bind(b.idx, a)
        return True
    if isinstance(a, Sort) and isinstance(b, Sort):
        return a.level == b.level
    if isinstance(a, Const) and isinstance(b, Const):
        return a.name == b.name
    if isinstance(a, Lit) and isinstance(b, Lit):
        return a.value == b.value
    if isinstance(a, Var) and isinstance(b, Var):
        return a.idx == b.idx
    if isinstance(a, App) and isinstance(b, App):
        return (unify(a.fn, b.fn, ctx, fuel - 1)
                and unify(a.arg, b.arg, ctx, fuel - 1))
    if isinstance(a, Pi) and isinstance(b, Pi):
        return (unify(a.dom, b.dom, ctx, fuel - 1)
                and unify(a.body, b.body, ctx, fuel - 1))
    if isinstance(a, Lam) and isinstance(b, Lam):
        return (unify(a.dom, b.dom, ctx, fuel - 1)
                and unify(a.body, b.body, ctx, fuel - 1))
    return False


# ---------------------------------------------------------------------------
# inference
# ---------------------------------------------------------------------------
def infer(e: Expr, sig: dict[str, Expr], ctx: MetaCtx,
          env: list[Expr] | None = None, mtypes: dict[int, Expr] | None = None,
          fuel: int = FUEL) -> Expr:
    """The type of ``e`` under ``sig``, or :class:`TypeError_`.

    ``sig`` maps a constant's name to its declared type; a name it does not
    carry is undeclared and is an error, which is the half of the kernel that
    the elaborator relies on — an episode's signature is exactly the set of
    symbols the episode may mention.
    """
    env = env or []
    if fuel <= 0:                                     # pragma: no cover
        raise TypeError_("out of fuel")
    e = ctx.deref(e)
    if isinstance(e, Sort):
        return Sort(e.level + 1)
    if isinstance(e, Const):
        if e.name not in sig:
            raise TypeError_(f"undeclared constant {e.name}")
        return sig[e.name]
    if isinstance(e, Lit):
        return Const("Name")
    if isinstance(e, Var):
        if not 0 <= e.idx < len(env):
            raise TypeError_(f"unbound variable #{e.idx}")
        return _lift(env[e.idx], e.idx + 1)
    if isinstance(e, MVar):
        if mtypes is not None and e.idx in mtypes:
            return mtypes[e.idx]
        raise TypeError_(f"?m{e.idx} has no type")
    if isinstance(e, Pi):
        d = whnf(infer(e.dom, sig, ctx, env, mtypes, fuel - 1), ctx)
        b = whnf(infer(e.body, sig, ctx, [e.dom] + env, mtypes, fuel - 1), ctx)
        if not isinstance(d, Sort) or not isinstance(b, Sort):
            raise TypeError_(f"Pi over a non-sort in {pretty(e)}")
        # Lean's impredicative Prop: `α → Prop` is a Prop.
        return Sort(0) if b.level == 0 else Sort(max(d.level, b.level))
    if isinstance(e, Lam):
        body = infer(e.body, sig, ctx, [e.dom] + env, mtypes, fuel - 1)
        return Pi(e.name, e.dom, body)
    if isinstance(e, App):
        fn = whnf(infer(e.fn, sig, ctx, env, mtypes, fuel - 1), ctx)
        if not isinstance(fn, Pi):
            raise TypeError_(f"{pretty(e.fn)} : {pretty(fn)} is not a function")
        arg = infer(e.arg, sig, ctx, env, mtypes, fuel - 1)
        if not unify(fn.dom, arg, ctx, fuel - 1):
            raise TypeError_(f"argument {pretty(e.arg)} : {pretty(arg)} "
                             f"does not fit {pretty(fn.dom)}")
        return _subst(fn.body, e.arg)
    raise TypeError_(f"not an Expr: {e!r}")           # pragma: no cover


def check(e: Expr, expected: Expr, sig: dict[str, Expr], ctx: MetaCtx,
          env: list[Expr] | None = None,
          mtypes: dict[int, Expr] | None = None) -> bool:
    """Does ``e`` have type ``expected``? Never raises."""
    try:
        got = infer(e, sig, ctx, env, mtypes)
    except TypeError_:
        return False
    except RecursionError:                            # pragma: no cover
        return False
    return unify(got, expected, ctx)
