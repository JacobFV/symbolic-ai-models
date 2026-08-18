"""Names that survive the round trip into a solver's syntax and back.

An entity id here is ``wn:dog.n.01`` or ``artifact:blake2b:9f...``; a predicate
may be ``cites-precedent``. None of those are valid ASP identifiers, and the
tempting fix — lowercase it and replace the punctuation — is not injective:
``cites-precedent`` and ``cites_precedent`` collapse onto one name, and two
different relations silently become one.

So predicates are mangled through an explicit **bijection**, kept in the
projection so the result can be translated back exactly, with collisions
resolved by numbering rather than by hoping. Constants are not mangled at all —
they are emitted as quoted string terms, which ASP handles natively and which
cannot collide with anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["Mangler", "quote"]

_BAD = re.compile(r"[^a-z0-9_]")


def quote(value: str) -> str:
    """A constant as a quoted ASP string term. Never mangled, never collides."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


@dataclass
class Mangler:
    """``original <-> solver identifier``, injective in both directions."""

    forward: dict[str, str] = field(default_factory=dict)
    backward: dict[str, str] = field(default_factory=dict)

    def to_solver(self, name: str) -> str:
        got = self.forward.get(name)
        if got is not None:
            return got
        base = _BAD.sub("_", name.lower()).lstrip("_") or "p"
        if base[0].isdigit():
            base = "p" + base
        cand, i = base, 1
        while cand in self.backward:
            i += 1
            cand = f"{base}_{i}"
        self.forward[name] = cand
        self.backward[cand] = name
        return cand

    def from_solver(self, name: str) -> str:
        try:
            return self.backward[name]
        except KeyError:
            raise KeyError(
                f"the solver returned predicate {name!r}, which this projection "
                f"never emitted. Either the supplied program invented it -- in "
                f"which case name it in `role_names` so it can be read back -- "
                f"or the mangling is not a bijection.") from None

    def read(self, name: str) -> str:
        """A name coming *back* from the solver.

        A name this projection never emitted is not an error: the caller's own
        ASP program invents predicates (``flies``, ``reachable``), and those are
        exactly the interesting ones. They are already valid identifiers and
        cannot collide with a mangled name, because every mangled name is in
        ``backward`` by construction — so passing them through verbatim is
        unambiguous. :meth:`from_solver` stays strict for callers that want to
        know.
        """
        return self.backward.get(name, name)

    def to_dict(self) -> dict[str, str]:
        return dict(self.forward)
