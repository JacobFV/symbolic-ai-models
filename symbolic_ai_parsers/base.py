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
one right answer of type :class:`~symbolic_ai_core.data.graph.Graph`, with no
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

:mod:`symbolic_ai_core.registry`, which is where the resolution rule and the
``ptrgen-argmax`` story behind it are written down. This package used to carry a
hand-copied second implementation of that rule — copied *including* the bug fix,
which is the tell that it should never have been copied at all. The convention is
wanted here for the same reason it is wanted for models: ``template-seeded`` is a
knob, not the model.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence, TypeVar

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.graph import Graph
from symbolic_ai_core.registry import VersionedRegistry, base_name

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


_REGISTRY: VersionedRegistry[Parser] = VersionedRegistry("parser")

#: The same dict the registry holds, not a copy — the CLI and the tests read it
#: directly and would otherwise see a snapshot taken at import time.
REGISTRY: dict[str, type[Parser]] = _REGISTRY.entries

T = TypeVar("T", bound=type[Parser])


def register(name: str, *, doc: str = "", learned: bool = False
             ) -> Callable[[T], T]:
    def deco(cls: T) -> T:
        _REGISTRY.add(name, cls)
        cls.name = name
        cls.summary = doc or (cls.__doc__ or "").strip().split("\n")[0]
        cls.learned = learned
        return cls
    return deco


def get(name: str) -> type[Parser]:
    """Exact match first, then the highest *numbered* version of a bare name.

    **Numbered, not merely highest** — see :mod:`symbolic_ai_core.registry`. A
    word-suffixed variant such as ``template-seeded`` is a side experiment and
    has to be asked for in full, which is exactly what naming it for a knob
    implies.
    """
    return _REGISTRY.get(name)


def build(name: str, **kw: Any) -> Parser:
    return get(name)(**kw)


def parser_names() -> list[str]:
    return _REGISTRY.names()
