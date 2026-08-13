"""A parser is ``str -> Graph``. That is the whole interface.

Why a second parser package
---------------------------

``symbolic_ai_models.parsers`` already exists, is tested, and is not this. Its
codomain is a :class:`~symbolic_ai_models.parsers.base.ParseResult` — tokens,
per-token class names, brackets over token spans, and optionally a flat list of
``(predicate, *args)`` facts — and it is scored by *pairwise class agreement*:
did the parser put two words in one class when the generator used them in the
same position. That is a question about word categories, and it is answerable
without ever committing to a structure.

This package asks the other question. ``langcurriculum`` renders every episode
from a typed term and hands the term over, so for every string there is exactly
one right answer of type :class:`~symbolic_ai_models.data.graph.Graph`, with no
annotator and an unbounded supply of fresh episodes. A parser here has to
produce that object: the nodes, their types, their labels, and who each node's
parent is. Nothing partial, nothing optional.

**So this package supersedes the old one rather than reusing or wrapping it**,
for the objective — the two layers have different codomains and different
metrics, and a ``ParseResult`` cannot be turned into a ``Graph`` without
inventing the structure it declined to commit to. The old layer is not deleted
and its reasoners keep using it. One bridge is provided and registered as a
control: :mod:`symbolic_ai_parsers.parsers.legacy` lifts the ``facts`` field of
the old ``regex`` parser into a graph, which is the one place the old codomain
does determine a structure. It is registered so that "does the existing parser
layer, given the harder codomain, beat a five-line structural baseline" is a row
in the table rather than an opinion.

The registry
------------

Mirrors :mod:`symbolic_ai_models.models.registry`, *including* its bug fix: a
bare name resolves over ``-001``, ``-002``, … only, never over a word-suffixed
variant. That registry learned it the expensive way — ``ptrgen-argmax``, a
control, became what ``ptrgen`` meant, because a plain string sort puts every
word above every number. The same convention is wanted here for the same reason
(``template-seeded`` is a knob, not the model), so the same rule is enforced.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Sequence, TypeVar

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.graph import Graph

__all__ = ["Parser", "register", "get", "build", "parser_names", "base_name",
           "REGISTRY"]


class Parser:
    """Fit on training episodes; map a string to a :class:`Graph`.

    ``parse`` is the whole contract. ``fit`` is where a parser is allowed to see
    supervision, and it sees *episodes* — both surfaces of the same seed — so a
    learned parser has the text it will be given and the graph it must produce.
    """

    #: registry name, set by ``@register``
    name: str = ""
    #: one line, printed by ``symbolic-ai-parsers list``
    summary: str = ""
    #: whether the parser learns from the training episodes or was written down.
    #: Printed beside the scores: "learned" and "hand-written" are different
    #: claims and a table that mixes them silently is misleading.
    learned: bool = False

    def fit(self, episodes: Sequence[Episode]) -> None:
        """Learn from training episodes. Hand-written parsers do nothing here."""

    def parse(self, text: str) -> Graph:
        raise NotImplementedError

    def n_parameters(self) -> int:
        """Discrete things learned. Zero for a parser that was written down."""
        return 0

    def describe(self) -> str:
        return f"{self.name}: {self.summary}"


REGISTRY: dict[str, type[Parser]] = {}
T = TypeVar("T", bound=type[Parser])

#: ``name-001``, ``name-002``, ``name-seeded``. Free-form after the dash so a
#: variant can be named for what it changed rather than counted.
_VERSIONED = re.compile(r"^(?P<base>.+?)-(?P<version>[A-Za-z0-9_]+)$")


def base_name(name: str) -> str:
    """``template-001`` -> ``template``; an unversioned name is its own base."""
    m = _VERSIONED.match(name)
    return m.group("base") if m else name


def register(name: str, *, doc: str = "", learned: bool = False
             ) -> Callable[[T], T]:
    def deco(cls: T) -> T:
        if name in REGISTRY:
            raise ValueError(f"parser {name!r} is already registered")
        cls.name = name
        cls.summary = doc or (cls.__doc__ or "").strip().split("\n")[0]
        cls.learned = learned
        REGISTRY[name] = cls
        return cls
    return deco


def get(name: str) -> type[Parser]:
    """Exact match first, then the highest *numbered* version of a bare name.

    Exact-first matters: a parser literally registered as ``foo`` must win over
    resolution, or a later ``foo-002`` would hijack a name someone pinned.

    **Numbered, not merely highest** — see the module docstring. A word-suffixed
    variant such as ``template-seeded`` is a side experiment and has to be asked
    for in full, which is exactly what naming it for a knob implies.
    """
    if name in REGISTRY:
        return REGISTRY[name]
    numbered = [(int(m.group("version")), n) for n in REGISTRY
                if (m := _VERSIONED.match(n)) and m.group("base") == name
                and m.group("version").isdigit()]
    if numbered:
        return REGISTRY[max(numbered)[1]]
    named = sorted(n for n in REGISTRY if base_name(n) == name)
    if named:
        raise KeyError(
            f"{name!r} has no numbered version; its variants are "
            f"{named} and must be named in full") from None
    raise KeyError(f"unknown parser {name!r}; have {parser_names()}") from None


def build(name: str, **kw: Any) -> Parser:
    return get(name)(**kw)


def parser_names() -> list[str]:
    return sorted(REGISTRY)
