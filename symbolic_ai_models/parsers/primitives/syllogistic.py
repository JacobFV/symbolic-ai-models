"""A formal parser for a small fragment of English: categorical statements and
individual facts, plus the question the prompt is asking.

The fragment is intentionally narrow — four categorical forms and two individual
forms. Anything outside it parses to nothing, which is the honest answer: the
agent then reports `unknown` instead of guessing. That failure mode is the point
of having a symbolic agent in the matrix at all.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import lexicon

Quantifier = str  # "all" | "no" | "some" | "some_not"


@dataclass(frozen=True)
class Categorical:
    """`<quantifier> S are P`."""

    quantifier: Quantifier
    subject: str
    predicate: str

    def __str__(self) -> str:
        if self.quantifier == "some_not":
            return f"some {self.subject} are not {self.predicate}"
        return f"{self.quantifier} {self.subject} are {self.predicate}"


@dataclass(frozen=True)
class Fact:
    """`<individual> is (not) a P`."""

    individual: str
    predicate: str
    negated: bool = False

    def __str__(self) -> str:
        return f"{self.individual} is {'not ' if self.negated else ''}a {self.predicate}"


Statement = Categorical | Fact


@dataclass
class Parse:
    premises: list[Statement] = field(default_factory=list)
    query: Statement | None = None
    unparsed: list[str] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        seen = len(self.premises) + (1 if self.query else 0)
        total = seen + len(self.unparsed)
        return seen / total if total else 0.0


_SPLIT = re.compile(
    r"\b(are not|is not|aren't|isn't|are|is)\b", re.IGNORECASE
)
_INDIVIDUAL = re.compile(r"^[A-Z][a-z]+$")


def _strip_lead(text: str) -> str:
    lowered = text.lower()
    for marker in lexicon.CONCLUSION_MARKERS:
        if lowered.startswith(marker):
            return text[len(marker) :].lstrip(" ,")
    return text


def _is_individual(raw_subject: str) -> bool:
    """A capitalized single word with no quantifier is a name, not a class."""
    stripped = raw_subject.strip().strip(",")
    return bool(_INDIVIDUAL.match(stripped))


def parse_statement(raw: str) -> Statement | None:
    """One sentence to one logical form, or None when outside the fragment."""
    text = _strip_lead(raw.strip().rstrip(".?!;"))
    if not text:
        return None
    # Normalize the interrogative inversion: "Is X a B" -> "X is a B".
    lowered = text.lower()
    if lowered.startswith(("is ", "are ")):
        head, _, rest = text.partition(" ")
        parts = rest.split(" ", 1)
        if len(parts) == 2:
            text = f"{parts[0]} {head.lower()} {parts[1]}"
    if lowered.startswith(("does ", "do ")):
        text = text.split(" ", 1)[1] if " " in text else text

    pieces = _SPLIT.split(text, maxsplit=1)
    if len(pieces) != 3:
        return None
    left, copula, right = (p.strip() for p in pieces)
    negated = copula.lower() in ("are not", "is not", "aren't", "isn't")
    predicate = lexicon.term(right)
    if not predicate:
        return None

    tokens = lexicon.words(left)
    if not tokens:
        return None
    quantifier = lexicon.QUANTIFIERS.get(tokens[0])
    if quantifier is None:
        if _is_individual(left):
            return Fact(lexicon.term(left), predicate, negated=negated)
        # A bare plural ("dogs are mammals") is a universal.
        return Categorical("some_not" if negated else "all", lexicon.term(left), predicate)

    rest = tokens[1:]
    # "at least one", "there are some" — drop the filler before the noun.
    while rest and rest[0] in {"least", "one", "of", "are", "is", "the"}:
        rest = rest[1:]
    subject = lexicon.term(" ".join(rest))
    if not subject:
        return None
    if quantifier == "no":
        return Categorical("no", subject, predicate)
    if quantifier == "some":
        return Categorical("some_not" if negated else "some", subject, predicate)
    return Categorical("some_not" if negated else "all", subject, predicate)


def _is_question(raw: str) -> bool:
    lowered = raw.strip().lower()
    return raw.strip().endswith("?") or lowered.startswith(
        lexicon.CONCLUSION_MARKERS
    )


def parse_prompt(text: str) -> Parse:
    """Split a prompt into premises and the one thing it asks about.

    The query is the last question or conclusion-marked sentence; everything else
    that parses is a premise.
    """
    parse = Parse()
    raws = lexicon.sentences(text)
    parsed = [parse_statement(raw) for raw in raws]
    # The query is the LAST question-marked sentence that actually parses — a
    # prompt often ends with an unparseable "Does the conclusion follow?" after
    # stating the conclusion it means.
    query_index = next(
        (
            i
            for i in range(len(raws) - 1, -1, -1)
            if _is_question(raws[i]) and parsed[i] is not None
        ),
        None,
    )
    for i, (raw, statement) in enumerate(zip(raws, parsed)):
        if statement is None:
            parse.unparsed.append(raw)
        elif i == query_index:
            parse.query = statement
        else:
            parse.premises.append(statement)
    return parse
