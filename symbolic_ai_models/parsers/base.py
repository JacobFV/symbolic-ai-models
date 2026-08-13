"""A parser is a thing that turns text into structure — and nothing else.

Until now every symbolic model in this repo carried its own parser welded on.
``syllogism`` owns a categorical fragment, ``symbolalg`` a clause regex,
``grammar`` a class induction. That conflates two independent choices — *how to
read the text* and *how to reason over what was read* — and it means a better
parser cannot be dropped underneath an existing reasoner without rewriting the
reasoner.

So a :class:`Parser` is separated out here, and it is deliberately a small
interface. It is fitted on training episodes, it maps a string to a
:class:`ParseResult`, and it knows nothing about tasks, losses, masking or
graphs. A reasoner names the parser it wants and must work with any of them,
including :class:`~symbolic_ai_models.parsers.none.NoParser`, which does nothing
at all and is the control every other parser is read against.

The payoff is that ``parser x reasoner`` becomes a matrix rather than a list, so
"is this reasoner better" and "is this parser better" become separately
answerable questions.

What a parser may return
------------------------

``ParseResult`` is a union of the things the parsers in this repo actually
produce, and a parser fills in only what it has:

* ``tokens`` — the surface, always;
* ``classes`` — a class name per token, for parsers that induce or assign
  categories ("this is the sort of word that goes here");
* ``constituents`` — brackets over token spans, for parsers that group;
* ``facts`` — a relational reading, for parsers that go all the way to
  predicate-argument form.

A reasoner consuming a parse asks for what it needs and tolerates absence. That
is what lets one reasoner sit on top of a bracketing chunker and a first-order
fact extractor alike.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence, TypeVar

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer

__all__ = ["Parser", "ParseResult", "Constituent", "register", "get", "build",
           "parser_names", "REGISTRY"]


@dataclass(frozen=True)
class Constituent:
    """A bracket over ``tokens[start:end]``, optionally named."""

    start: int
    end: int
    label: str = ""

    def __len__(self) -> int:
        return self.end - self.start

    def span(self) -> tuple[int, int]:
        return (self.start, self.end)


@dataclass
class ParseResult:
    """Whatever structure a parser managed to recover. Fields may be empty."""

    tokens: list[str] = field(default_factory=list)
    #: token index -> class name. The categories the parser thinks exist.
    classes: dict[int, str] = field(default_factory=dict)
    #: brackets over token spans, innermost-first by convention
    constituents: list[Constituent] = field(default_factory=list)
    #: a relational reading: ``(predicate, *arguments)``
    facts: list[tuple] = field(default_factory=list)
    #: anything a particular parser wants to carry through
    meta: dict[str, Any] = field(default_factory=dict)

    def class_of(self, index: int) -> str:
        """The class of a token, or the token itself when the parser has no
        opinion — so a consumer never has to branch on whether classes exist."""
        return self.classes.get(index) or (
            self.tokens[index] if 0 <= index < len(self.tokens) else "")

    def spans(self) -> set[tuple[int, int]]:
        return {c.span() for c in self.constituents}


class Parser:
    """Fit on training text; map a string to structure.

    Subclasses override :meth:`fit` if they learn anything and :meth:`parse`
    always. Nothing here knows what the structure will be *used for*.
    """

    #: registry name, set by ``@register``
    name: str = ""
    #: one line, printed by ``symbolic-ai-models parsers``
    summary: str = ""
    #: whether this parser induces its categories rather than being told them.
    #: Printed alongside results, because "learned" and "hand-written" are not
    #: the same claim and a table that mixes them silently is misleading.
    learned: bool = False

    def fit(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Learn from training episodes. Hand-written parsers do nothing here."""

    def parse(self, text: str) -> ParseResult:
        raise NotImplementedError

    def n_parameters(self) -> int:
        """Discrete things learned. Zero for a parser that was written down."""
        return 0

    def render(self) -> str:
        """What the parser knows, as text, when that is short enough to read."""
        return f"{self.name}: {self.summary}"


REGISTRY: dict[str, type[Parser]] = {}
T = TypeVar("T", bound=type[Parser])


def register(name: str, *, doc: str = "", learned: bool = False) -> Callable[[T], T]:
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
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown parser {name!r}; have {parser_names()}") from None


def build(name: str, **kw: Any) -> Parser:
    return get(name)(**kw)


def parser_names() -> list[str]:
    return sorted(REGISTRY)
