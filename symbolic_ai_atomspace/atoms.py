"""The four atom types MeTTa has, and the source syntax they print as.

``Symbol``, ``Variable``, ``Expression``, ``Grounded``. Nothing else is an atom,
which is the whole reason the layer is small enough to be trustworthy: an
``AtomSpace`` is a set of these, a pattern is one of these containing
``Variable``s, and every operation in :mod:`symbolic_ai_atomspace.metta` is
defined by structural recursion over the four cases.

Why atoms are frozen and hashed by content
------------------------------------------
A real AtomSpace stores each atom **once**: two occurrences of ``(parent alice
frank)`` are the same atom, not two copies of one. That is the property the
whole pattern-matching story rests on — a query returns bindings over a *set*,
so it cannot double-count — and it is reproduced here by making atoms frozen
value objects.

It is also, and this was measured rather than assumed, exactly what makes
``Graph -> atomspace`` non-invertible if you encode a term as its own nested
expression. A curriculum graph is a tree of **occurrences**; an atomspace is a
set of **values**; and two sibling leaves labelled ``a`` collapse into one atom
the moment the encoding forgets where they sat. See
:mod:`symbolic_ai_atomspace.encode`, which names occurrences for that reason and
reports how much collapse the naming is preventing.

Source syntax, and the one thing that is not obvious
----------------------------------------------------
``print_atom`` emits MeTTa source and :func:`parse_atoms` reads it back. Symbol
names on this curriculum are **not** identifiers: ``context_free_language``
renders bracket strings, so ``(`` and ``)`` are genuine one-character labels,
prose words carry underscores, and a ``field`` name may be empty. A printer that
assumed identifiers would emit source that reparses into a different space, and
would do it silently — which is the exact shape of the tokenizer bug that cost
this repo a published number. So symbols quote themselves whenever they are not
plainly atomic, and ``tests/test_atomspace.py`` asserts the round trip over
every graph of all 179 lessons rather than over a fixture.
"""

from __future__ import annotations

import re
from typing import Any, Iterator

__all__ = ["Atom", "Symbol", "Variable", "Expression", "Grounded",
           "S", "V", "E", "G", "print_atom", "parse_atoms", "parse_atom",
           "is_ground", "variables_in"]


class Atom:
    """Base of the four. Frozen, hashed by content, never mutated."""

    __slots__ = ()

    def __repr__(self) -> str:                              # pragma: no cover
        return print_atom(self)


class Symbol(Atom):
    """A name. Any string at all, including ``(``, ``_`` and the empty one."""

    __slots__ = ("name", "_hash")

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "name", str(name))
        object.__setattr__(self, "_hash", hash(("S", self.name)))

    def __eq__(self, other: Any) -> bool:
        return type(other) is Symbol and other.name == self.name

    def __hash__(self) -> int:
        return self._hash

    def __setattr__(self, *a: Any) -> None:
        raise AttributeError("atoms are frozen")


class Variable(Atom):
    """``$x``. Binds to any atom under unification."""

    __slots__ = ("name", "_hash")

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "name", str(name))
        object.__setattr__(self, "_hash", hash(("V", self.name)))

    def __eq__(self, other: Any) -> bool:
        return type(other) is Variable and other.name == self.name

    def __hash__(self) -> int:
        return self._hash

    def __setattr__(self, *a: Any) -> None:
        raise AttributeError("atoms are frozen")


class Expression(Atom):
    """``(a b c)``. A tuple of atoms; the empty expression ``()`` is legal."""

    __slots__ = ("children", "_hash")

    def __init__(self, *children: Atom) -> None:
        kids = tuple(children)
        object.__setattr__(self, "children", kids)
        object.__setattr__(self, "_hash", hash(("E", kids)))

    def __eq__(self, other: Any) -> bool:
        return type(other) is Expression and other.children == self.children

    def __hash__(self) -> int:
        return self._hash

    def __setattr__(self, *a: Any) -> None:
        raise AttributeError("atoms are frozen")

    def __len__(self) -> int:
        return len(self.children)

    def __getitem__(self, i: int) -> Atom:
        return self.children[i]

    def __iter__(self) -> Iterator[Atom]:
        return iter(self.children)

    @property
    def head(self) -> Atom | None:
        return self.children[0] if self.children else None


class Grounded(Atom):
    """A Python value carried into the space — here only ``int`` and ``str``.

    Deliberately narrow. A real MeTTa ``Grounded`` can hold an executable
    object, and executing arbitrary Python inside a pattern match is precisely
    the thing that would make this layer's cost unbounded and its semantics
    unverifiable. What is kept is the data half: an integer slot index is a
    grounded atom rather than a symbol spelled ``3``, so arithmetic on it is
    possible without parsing.
    """

    __slots__ = ("value", "_hash")

    def __init__(self, value: Any) -> None:
        if not isinstance(value, (int, str)) or isinstance(value, bool):
            raise TypeError(f"Grounded holds int or str, not {type(value).__name__}")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "_hash", hash(("G", type(value).__name__, value)))

    def __eq__(self, other: Any) -> bool:
        return (type(other) is Grounded and type(other.value) is type(self.value)
                and other.value == self.value)

    def __hash__(self) -> int:
        return self._hash

    def __setattr__(self, *a: Any) -> None:
        raise AttributeError("atoms are frozen")


# Short constructors. The encoder builds millions of these and
# ``Symbol("child")`` five times per node reads worse than ``S("child")``.
S = Symbol
V = Variable
E = Expression
G = Grounded


def is_ground(atom: Atom) -> bool:
    """True when no :class:`Variable` occurs anywhere inside ``atom``."""
    if isinstance(atom, Variable):
        return False
    if isinstance(atom, Expression):
        return all(is_ground(c) for c in atom.children)
    return True


def variables_in(atom: Atom) -> set[str]:
    """Every variable name occurring in ``atom``."""
    if isinstance(atom, Variable):
        return {atom.name}
    if isinstance(atom, Expression):
        out: set[str] = set()
        for c in atom.children:
            out |= variables_in(c)
        return out
    return set()


# ---------------------------------------------------------------------------
# source syntax
# ---------------------------------------------------------------------------
#: Characters that force a symbol to be quoted. Whitespace and the delimiters,
#: plus ``$`` (which would reparse as a variable), ``;`` (comment) and ``"``.
_UNSAFE = set(' \t\r\n()";')

#: A bare token matching this reads back as a :class:`Grounded` integer.
_INT = re.compile(r"-?\d+")


def _needs_quoting(name: str) -> bool:
    """Whether a symbol name would reparse as something other than itself.

    The digit case is the one nobody predicts and it is why the source round
    trip is asserted separately from the object one. A ``num`` node's label
    **is** ``3``, so an unquoted ``Symbol("3")`` prints as ``3`` and reads back
    as ``Grounded(3)``: the space is unchanged in memory, the printed source is
    a different space, and the only thing that would ever have noticed is a
    conformance oracle nobody had run yet. Found by
    ``tests/test_atomspace.py::test_the_round_trip_survives_the_source_as_well_as_the_objects``
    on the first run, on the real curriculum.
    """
    return (name == "" or name.startswith("$") or name.startswith("'")
            or _INT.fullmatch(name) is not None
            or any(c in _UNSAFE for c in name))


def _quote(name: str) -> str:
    out = name.replace("\\", "\\\\").replace('"', '\\"')
    out = out.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
    return f'"{out}"'


def print_atom(atom: Atom) -> str:
    """MeTTa source for one atom.

    Grounded integers print bare and grounded strings print quoted with a
    leading ``'``, so that the reader can tell ``3`` the number from ``3`` the
    symbol without a type declaration. Nothing else in the language needs a
    disambiguator, because symbols and variables are separated by ``$``.
    """
    if isinstance(atom, Symbol):
        return _quote(atom.name) if _needs_quoting(atom.name) else atom.name
    if isinstance(atom, Variable):
        return "$" + (atom.name if not _needs_quoting(atom.name)
                      else _quote(atom.name))
    if isinstance(atom, Grounded):
        if isinstance(atom.value, int):
            return str(atom.value)
        return "'" + _quote(atom.value)
    if isinstance(atom, Expression):
        return "(" + " ".join(print_atom(c) for c in atom.children) + ")"
    raise TypeError(f"not an atom: {atom!r}")                # pragma: no cover


class _Reader:
    """A hand-written s-expression reader. Small enough to audit in one sitting."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.i = 0

    def skip(self) -> None:
        while self.i < len(self.text):
            c = self.text[self.i]
            if c in " \t\r\n":
                self.i += 1
            elif c == ";":                                    # comment to EOL
                while self.i < len(self.text) and self.text[self.i] != "\n":
                    self.i += 1
            else:
                return

    def at_end(self) -> bool:
        self.skip()
        return self.i >= len(self.text)

    def read(self) -> Atom:
        self.skip()
        if self.i >= len(self.text):
            raise ValueError("unexpected end of MeTTa source")
        c = self.text[self.i]
        if c == "(":
            self.i += 1
            kids: list[Atom] = []
            while True:
                self.skip()
                if self.i >= len(self.text):
                    raise ValueError("unclosed expression")
                if self.text[self.i] == ")":
                    self.i += 1
                    return Expression(*kids)
                kids.append(self.read())
        if c == ")":
            raise ValueError(f"unbalanced ')' at {self.i}")
        if c == "$":
            # No whitespace is skipped after the sigil: ``$ x`` is a malformed
            # variable with an empty name, not a variable named ``x``.
            self.i += 1
            return Variable(self._name())
        if c == "'":
            self.i += 1
            return Grounded(self._name())
        quoted = self.text[self.i] == '"'
        token = self._name()
        if not quoted and _INT.fullmatch(token):
            return Grounded(int(token))
        return Symbol(token)

    def _name(self) -> str:
        if self.i < len(self.text) and self.text[self.i] == '"':
            return self._quoted()
        start = self.i
        while self.i < len(self.text) and self.text[self.i] not in _UNSAFE:
            self.i += 1
        return self.text[start:self.i]

    def _quoted(self) -> str:
        self.i += 1                                            # opening quote
        out: list[str] = []
        while True:
            if self.i >= len(self.text):
                raise ValueError("unterminated string")
            c = self.text[self.i]
            self.i += 1
            if c == '"':
                return "".join(out)
            if c == "\\":
                if self.i >= len(self.text):
                    raise ValueError("dangling escape")
                nxt = self.text[self.i]
                self.i += 1
                out.append({"n": "\n", "t": "\t", "r": "\r"}.get(nxt, nxt))
            else:
                out.append(c)


def parse_atom(text: str) -> Atom:
    """Read exactly one atom, and object to anything after it."""
    reader = _Reader(text)
    atom = reader.read()
    if not reader.at_end():
        raise ValueError("trailing text after atom")
    return atom


def parse_atoms(text: str) -> list[Atom]:
    """Read a whole MeTTa source file into a list of atoms."""
    reader = _Reader(text)
    out: list[Atom] = []
    while not reader.at_end():
        out.append(reader.read())
    return out
