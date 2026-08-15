"""The space itself: a set of atoms, an index, and the conjunctive query.

An ``AtomSpace`` is a **set**. Adding the same atom twice is a no-op, iteration
order is insertion order (a Python dict, so it is deterministic — this repo has
been bitten by set iteration order reaching a published number), and the only
interesting operation is :meth:`AtomSpace.query`.

Why the query is the point, in one paragraph
--------------------------------------------
The twelve ``CLAWS`` routes are a written-down enum: ``sibling0``,
``prev_sibling``, ``parent``, and so on. ``ilp`` — the one model here whose
hypothesis space is not a written-down list — discovered that its strongest
clause is a *typed, slot-selected sibling*, and ``CLAWS`` has no way to say
which sibling, so ``omegaclaw_reach-001`` had to add an ``if``. Here that clause
is a query and nothing else::

    ((child $p $i $q) (child $p $j $s) (: $s pred))

one more pattern rather than one more branch. Whether that expressiveness is
worth anything on this curriculum is the pre-registered question, and the
pre-registration predicts it is not — see
``notes/decisions/2026-08-14-atomspace-metta-ir-preregistration.md``.

The index, and why it is (head, arity)
---------------------------------------
Every atom this repo's encoder puts in a space is an ``Expression`` whose first
child is a plain ``Symbol`` — ``(child …)``, ``(: …)``, ``(label …)``. A pattern
almost always fixes that symbol and the arity too, so a dict keyed on the pair
turns a scan over the whole space into a scan over one relation. Patterns that
do *not* fix it fall back to a full scan, which is correct and slow, and the
distinction is visible in :meth:`AtomSpace.match`'s first three lines rather
than hidden behind a query planner. There is no planner here on purpose: a cost
model that mis-estimates is a silent performance cliff inside a sweep, and the
conjunctive join below simply evaluates the patterns in the order written, which
makes the cost a property of the caller's source text.
"""

from __future__ import annotations

from typing import Iterable, Iterator, Mapping

from .atoms import Atom, Expression, Symbol, print_atom
from .unify import Bindings, match_atom, substitute

__all__ = ["AtomSpace"]


def _index_key(atom: Atom) -> tuple | None:
    """``(head name, arity)`` for an indexable atom, else ``None``."""
    if isinstance(atom, Expression) and atom.children:
        head = atom.children[0]
        if isinstance(head, Symbol):
            return (head.name, len(atom.children))
    return None


class AtomSpace:
    """A set of atoms with a ``(head, arity)`` index over the expressions."""

    __slots__ = ("_atoms", "_index")

    def __init__(self, atoms: Iterable[Atom] = ()) -> None:
        #: Insertion-ordered set. A ``dict`` rather than a ``set`` because set
        #: iteration order varies with hash randomisation between processes,
        #: and this repo has already had a per-process ordering reach a number.
        self._atoms: dict[Atom, None] = {}
        self._index: dict[tuple, list[Atom]] = {}
        for atom in atoms:
            self.add(atom)

    # ---- the set ---------------------------------------------------------
    def add(self, atom: Atom) -> bool:
        """Add one atom. Returns whether it was new."""
        if atom in self._atoms:
            return False
        self._atoms[atom] = None
        key = _index_key(atom)
        if key is not None:
            self._index.setdefault(key, []).append(atom)
        return True

    def add_all(self, atoms: Iterable[Atom]) -> int:
        return sum(1 for a in atoms if self.add(a))

    def __contains__(self, atom: object) -> bool:
        return atom in self._atoms

    def __iter__(self) -> Iterator[Atom]:
        return iter(self._atoms)

    def __len__(self) -> int:
        return len(self._atoms)

    def relation(self, head: str, arity: int) -> list[Atom]:
        """Every atom of one relation, in insertion order. Never a copy's copy."""
        return self._index.get((head, arity), [])

    # ---- matching --------------------------------------------------------
    def match(self, pattern: Atom,
              bindings: Mapping[str, Atom] | None = None) -> Iterator[Bindings]:
        """Every binding under which ``pattern`` names an atom of the space.

        One-way matching (see :func:`~symbolic_ai_atomspace.unify.match_atom`):
        only the pattern's variables bind. A variable stored *inside* the space
        is data, not a wildcard.
        """
        key = _index_key(pattern)
        candidates = (self._index.get(key, ()) if key is not None
                      else self._atoms)
        for atom in candidates:
            found = match_atom(pattern, atom, bindings)
            if found is not None:
                yield found

    def query(self, *patterns: Atom,
              bindings: Mapping[str, Atom] | None = None) -> Iterator[Bindings]:
        """Conjunctive query: every binding satisfying **all** the patterns.

        A left-to-right nested loop, each pattern matched under the bindings the
        ones before it produced. No reordering — see the module docstring on why
        there is no planner.
        """
        if not patterns:
            yield dict(bindings or {})
            return
        first, rest = patterns[0], patterns[1:]
        for found in self.match(first, bindings):
            if not rest:
                yield found
            else:
                yield from self.query(*rest, bindings=found)

    def contains_pattern(self, *patterns: Atom) -> bool:
        """Whether the conjunctive query has at least one solution."""
        for _ in self.query(*patterns):
            return True
        return False

    def collect(self, template: Atom, *patterns: Atom) -> list[Atom]:
        """``template`` instantiated once per solution of the query.

        The read direction of a rewrite rule, and what a MeTTa ``match`` with a
        result template does.
        """
        return [substitute(template, b) for b in self.query(*patterns)]

    # ---- source ----------------------------------------------------------
    def to_metta(self) -> str:
        """The whole space as MeTTa source, one atom per line.

        Used by the out-of-band ``hyperon`` conformance oracle and by the
        round-trip test — a space that prints to source which reparses into a
        different space would be an encoding bug that no downstream number would
        reveal.
        """
        return "\n".join(print_atom(a) for a in self._atoms)

    @classmethod
    def from_metta(cls, text: str) -> "AtomSpace":
        from .atoms import parse_atoms
        return cls(parse_atoms(text))

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, AtomSpace)
                and set(self._atoms) == set(other._atoms))

    def __hash__(self) -> int:                               # pragma: no cover
        raise TypeError("AtomSpace is mutable and not hashable")

    def __repr__(self) -> str:                               # pragma: no cover
        return f"<AtomSpace {len(self._atoms)} atoms, {len(self._index)} relations>"
