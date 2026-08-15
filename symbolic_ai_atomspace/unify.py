"""Unification with variables, and substitution — the one operation everything
above is built out of.

Syntactic, first-order, with an occurs check. That is the whole of it, and the
omissions are deliberate and listed in :mod:`symbolic_ai_atomspace.metta`.

The occurs check is on, which is unusual for a fast unifier and is the right
call here for a reason that is about *cost*, not about correctness theatre.
Without it, unifying ``$x`` against ``(f $x)`` builds a cyclic structure, and the
next thing that walks it — :func:`substitute`, or the atom hash — recurses
forever. A pattern matcher inside a 179-lesson sweep must not be able to hang,
and an ``O(size)`` check on a binding is far cheaper than the alternative of
bounding recursion everywhere downstream.

Bindings are plain ``dict[str, Atom]`` keyed on the variable *name*, and they are
never mutated in place by :func:`unify` — it returns a new dict or ``None``.
That costs a copy per successful binding and buys the thing a conjunctive query
needs: a partial binding can be handed to several branches without one branch's
failure corrupting another's.
"""

from __future__ import annotations

from typing import Mapping

from .atoms import Atom, Expression, Grounded, Symbol, Variable

__all__ = ["unify", "substitute", "match_atom", "Bindings"]

#: Variable name -> the atom it stands for.
Bindings = dict[str, Atom]


def walk(atom: Atom, bindings: Mapping[str, Atom]) -> Atom:
    """Follow variable chains until the atom is not a bound variable."""
    seen = 0
    while isinstance(atom, Variable) and atom.name in bindings:
        atom = bindings[atom.name]
        seen += 1
        if seen > len(bindings) + 1:                         # pragma: no cover
            raise RecursionError("cyclic binding chain")
    return atom


def _occurs(name: str, atom: Atom, bindings: Mapping[str, Atom]) -> bool:
    atom = walk(atom, bindings)
    if isinstance(atom, Variable):
        return atom.name == name
    if isinstance(atom, Expression):
        return any(_occurs(name, c, bindings) for c in atom.children)
    return False


def unify(a: Atom, b: Atom,
          bindings: Mapping[str, Atom] | None = None) -> Bindings | None:
    """Most general unifier of ``a`` and ``b``, or ``None`` if there is none.

    ``bindings`` is an optional starting substitution; it is read, never
    written. The result is a fresh dict.
    """
    out: Bindings = dict(bindings or {})
    return out if _unify_into(a, b, out) else None


def _unify_into(a: Atom, b: Atom, bindings: Bindings) -> bool:
    a = walk(a, bindings)
    b = walk(b, bindings)
    if a == b:
        return True
    if isinstance(a, Variable):
        if _occurs(a.name, b, bindings):
            return False
        bindings[a.name] = b
        return True
    if isinstance(b, Variable):
        if _occurs(b.name, a, bindings):
            return False
        bindings[b.name] = a
        return True
    if isinstance(a, Expression) and isinstance(b, Expression):
        if len(a.children) != len(b.children):
            return False
        return all(_unify_into(x, y, bindings)
                   for x, y in zip(a.children, b.children))
    # Two distinct symbols, two distinct grounded values, or a type mismatch.
    return False


def match_atom(pattern: Atom, ground: Atom,
               bindings: Mapping[str, Atom] | None = None) -> Bindings | None:
    """One-way match: only ``pattern``'s variables may bind.

    This is what an :class:`~symbolic_ai_atomspace.space.AtomSpace` query wants.
    Full unification would let a variable *inside the space* bind to a pattern's
    subterm, so a stored atom containing ``$x`` would match everything — which is
    a fine thing for a rewrite engine and a disastrous thing for a query, since
    a single stray variable atom in the space would make every query true.
    """
    out: Bindings = dict(bindings or {})
    return out if _match_into(pattern, ground, out) else None


def _match_into(pattern: Atom, ground: Atom, bindings: Bindings) -> bool:
    if isinstance(pattern, Variable):
        prior = bindings.get(pattern.name)
        if prior is not None:
            return prior == ground
        bindings[pattern.name] = ground
        return True
    if isinstance(pattern, Expression):
        if not isinstance(ground, Expression):
            return False
        if len(pattern.children) != len(ground.children):
            return False
        return all(_match_into(p, g, bindings)
                   for p, g in zip(pattern.children, ground.children))
    return pattern == ground


def substitute(atom: Atom, bindings: Mapping[str, Atom]) -> Atom:
    """Replace every bound variable in ``atom``, recursively."""
    if isinstance(atom, Variable):
        bound = bindings.get(atom.name)
        return atom if bound is None else substitute(bound, bindings)
    if isinstance(atom, Expression):
        kids = tuple(substitute(c, bindings) for c in atom.children)
        return atom if kids == atom.children else Expression(*kids)
    return atom


# Re-exported for the doctest-ish readability of `isinstance` checks elsewhere.
_ = (Symbol, Grounded)
