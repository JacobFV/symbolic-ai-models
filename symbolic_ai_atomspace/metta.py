"""The MeTTa subset: rewrite rules, forward chaining, and what was left out.

A rule is written the way MeTTa writes one::

    (= (sibling $a $b) (, (child $p $i $a) (child $p $j $b)))

read here as *derive the left side for every binding satisfying the right side*.
``,`` is conjunction. Applying a rule set is forward chaining to a fixed point,
bounded, adding derived atoms into the same space the premises came from — which
is the AtomSpace stance: a derived fact and a given fact are the same kind of
thing and live together.

What is deliberately **not** in this subset
--------------------------------------------
Writing the omissions down is the point of this section; an IR that quietly
implements half a language and is compared against a full one is not a
measurement of anything.

``eval`` and grounded execution
    :class:`~symbolic_ai_atomspace.atoms.Grounded` holds ``int`` and ``str`` and
    nothing callable. There is no arithmetic, no ``println``, no Python escape
    hatch. This bounds the cost of a match — which
    ``notes/decisions/2026-08-14-the-ir-is-a-knob.md`` requires, since the whole
    line has to fit inside ``APPROACH.md``'s CPU budget — and it bounds what a
    reader can do, which is why the leak surface is arguable at all.

Non-determinism as a first-class effect
    Real MeTTa's ``superpose`` / ``collapse`` make a computation return many
    results and let later steps branch over them. Here a query returns a *list*
    of bindings and the caller decides; there is no monadic threading, no
    ``empty``, no ``case``. The expressiveness lost is real and is not needed by
    anything the models below do.

Backward chaining and recursion
    :func:`chain` runs forward, breadth-first, to a bounded depth. There is no
    goal-directed proof search and no fixpoint over recursive rules; a rule set
    whose closure is infinite is cut off by ``max_rounds`` rather than detected.
    A recursive ancestor relation is therefore *bounded* ancestry here.

Type checking
    ``(: a T)`` is an ordinary atom. Nothing checks it, nothing infers it,
    nothing rejects an ill-typed expression. That is the whole difference
    between this line and ``006`` — see the fork table in
    ``notes/decisions/2026-08-14-the-ir-is-a-knob.md``: ``005`` scores a bad
    answer low, ``006`` refuses it. Implementing a checker here would collapse
    the two arms into one and destroy the comparison.

Nested spaces, ``&self``, tokenisers, modules
    Absent. One flat space per episode.

Equality as reduction
    In real MeTTa ``(= lhs rhs)`` is also the *function definition* form and the
    interpreter reduces ``lhs`` to ``rhs`` on evaluation. Here it only ever adds
    ``lhs`` when ``rhs`` is satisfied. That is a genuine semantic difference and
    is why the conformance oracle emits *queries*, not programs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .atoms import Atom, Expression, Symbol, parse_atom, print_atom
from .space import AtomSpace
from .unify import substitute

__all__ = ["Rule", "rule", "chain", "CONJ", "EQ"]

#: The conjunction head, spelled as MeTTa spells it.
CONJ = Symbol(",")
#: The rule head.
EQ = Symbol("=")


@dataclass(frozen=True)
class Rule:
    """``(= conclusion (, premise ...))``.

    Frozen, because a rule set is shared between the fitting pass and the
    prediction pass of a model and a mutable one could differ between them —
    the same hazard ``vsa_spec-004``'s ``_shape_hash`` exists to close.
    """

    conclusion: Atom
    premises: tuple[Atom, ...]

    def to_atom(self) -> Atom:
        body = (self.premises[0] if len(self.premises) == 1
                else Expression(CONJ, *self.premises))
        return Expression(EQ, self.conclusion, body)

    def __str__(self) -> str:                                # pragma: no cover
        return print_atom(self.to_atom())

    @classmethod
    def from_atom(cls, atom: Atom) -> "Rule":
        if (not isinstance(atom, Expression) or len(atom.children) != 3
                or atom.children[0] != EQ):
            raise ValueError(f"not a rule: {print_atom(atom)}")
        _, conclusion, body = atom.children
        if (isinstance(body, Expression) and body.children
                and body.children[0] == CONJ):
            return cls(conclusion, tuple(body.children[1:]))
        return cls(conclusion, (body,))


def rule(source: str) -> Rule:
    """Read one rule from MeTTa source."""
    return Rule.from_atom(parse_atom(source))


def chain(space: AtomSpace, rules: Sequence[Rule], *,
          max_rounds: int = 4, max_atoms: int | None = None) -> int:
    """Forward-chain ``rules`` into ``space``. Returns how many atoms were added.

    Breadth-first: every rule is applied against the space as it stood at the
    start of a round, and the conclusions land together. Applying rules against
    a space being mutated underneath them would make the result depend on rule
    order, which is the kind of hidden ordering dependency this repo has already
    had reach a published number.

    ``max_atoms`` is a hard stop. A rule set over ``n`` nodes can be quadratic —
    ``sibling`` genuinely is — and a sweep must not be able to exhaust memory on
    one unusually wide graph.
    """
    added = 0
    for _ in range(max(max_rounds, 0)):
        fresh: list[Atom] = []
        for r in rules:
            for bindings in space.query(*r.premises):
                fresh.append(substitute(r.conclusion, bindings))
        new = 0
        for atom in fresh:
            if max_atoms is not None and len(space) >= max_atoms:
                return added + new
            new += space.add(atom)
        added += new
        if new == 0:
            break
    return added
