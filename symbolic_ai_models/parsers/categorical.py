"""The syllogism fragment, behind the :class:`Parser` interface.

``syllogism`` owns a real parser for a small fragment of English — four
categorical forms and two individual forms — and it refuses anything outside it
rather than guessing. That refusal is the interesting property, and it was
invisible: fused to one reasoner, the fragment's coverage could only be observed
through that reasoner's accuracy, where a miss might be a parse failure or a bad
inference and the number does not say which.

Wrapping it here separates the two questions. The fragment stays in
:mod:`symbolic_ai_models.parsers.primitives.syllogistic` and its lexicon and is
imported, not copied, so there is one definition of what counts as a quantifier.
The work done here is the part the fused parser never needed: putting the logical
form back onto token offsets.

That is a genuine approximation and worth being plain about.
``parse_statement`` normalizes as it goes — it drops articles, singularizes,
rewrites the interrogative inversion — so the statement it returns no longer
knows which words it came from. The spans are therefore recovered by walking the
same lexicon over the tokens (find the copula; strip the quantifier and any
conclusion marker in front of the subject), which agrees with the statement on
the fragment and is why a sentence with no locatable copula is left unclassified
instead of being bracketed on a guess.

Statements outside the fragment contribute nothing: no class, no bracket, no
fact. A prompt entirely outside it parses to tokens and nothing else, which is
the same honest failure the reasoner has always had.
"""

from __future__ import annotations

from typing import Any

from symbolic_ai_core.data.tokenizer import split_words
from .primitives import lexicon
from .primitives.syllogistic import (Categorical, Fact, Statement,
                                       parse_prompt, parse_statement)
from .base import Constituent, ParseResult, Parser, register

__all__ = ["CategoricalParser"]

#: Copulas as token sequences, longest first, because ``split_words`` breaks
#: contractions into three tokens ("aren't" -> aren ' t) and the two-token
#: "are not" must not be tried against them the other way round.
_COPULAS: tuple[tuple[str, ...], ...] = tuple(sorted(
    (tuple(split_words(c)) for c in lexicon.COPULAS), key=len, reverse=True))
_MARKERS: tuple[tuple[str, ...], ...] = tuple(sorted(
    (tuple(split_words(m)) for m in lexicon.CONCLUSION_MARKERS),
    key=len, reverse=True))
#: What ``parse_statement`` drops between the quantifier and the noun
#: ("at least one dog", "there are some dogs").
_FILLERS = frozenset({"least", "one", "of"}) | lexicon.ARTICLES

#: ``(lead, copula, subject, predicate)``, each a half-open token span.
_Layout = tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]


@register("categorical", learned=False,
          doc="A narrow fragment of English: quantified statements and individual facts.")
class CategoricalParser(Parser):
    """Subject/predicate brackets and categorical facts. Nothing is learned."""

    def parse(self, text: str) -> ParseResult:
        try:
            toks = split_words(text)
        except Exception:
            return ParseResult()
        result = ParseResult(tokens=toks)
        try:
            self._fill(text, result)
        except Exception:
            return ParseResult(tokens=toks)
        return result

    # ---- structure ----------------------------------------------------
    def _fill(self, text: str, result: ParseResult) -> None:
        raws = lexicon.sentences(text)
        statements = [_statement(raw) for raw in raws]
        if not any(s is not None for s in statements):
            # Nothing in the fragment. Tokens and silence, rather than a
            # structure the parser does not actually believe.
            return

        # ``parse_prompt`` decides which statement is being *asked* about — the
        # last question that parses, not merely the last sentence — so that rule
        # is taken from it rather than restated here.
        prompt = _prompt(text)
        query = prompt.query if prompt is not None else None
        query_index = _last_index(statements, query)

        classes = {i: "other" for i in range(len(result.tokens))}
        facts: list[tuple] = []
        at = 0
        for raw, statement in zip(raws, statements):
            found = _locate(result.tokens, split_words(raw), at)
            if found is None:
                continue
            start, end = found
            at = end
            if statement is None:
                continue
            facts.append(_fact(statement))
            layout = _layout(result.tokens, start, end)
            if layout is None:
                continue
            _apply(result, classes, statement, layout)

        result.classes = classes
        result.facts = facts
        result.meta = {
            "query": _fact(query) if query is not None else None,
            "query_index": query_index,
            "unparsed": list(prompt.unparsed) if prompt is not None else [],
            "coverage": prompt.coverage if prompt is not None else 0.0,
        }


def _apply(result: ParseResult, classes: dict[int, str], statement: Statement,
           layout: _Layout) -> None:
    """Write one statement's spans into the classes and the brackets."""
    lead, copula, subject, predicate = layout
    for i in range(*lead):
        # A leading word is a quantifier if the lexicon says so; a conclusion
        # marker or an article in the same position is not.
        if result.tokens[i].lower() in lexicon.QUANTIFIERS:
            classes[i] = "quantifier"
    for i in range(*copula):
        classes[i] = "copula"
    # The subject of a Fact is a name, and naming it "term" would put individuals
    # and classes in one bucket — the distinction the fragment exists to draw.
    subject_class = "individual" if isinstance(statement, Fact) else "term"
    for i in range(*subject):
        classes[i] = subject_class
    for i in range(*predicate):
        classes[i] = "term"
    if subject[1] > subject[0]:
        result.constituents.append(Constituent(*subject, "subject"))
    if predicate[1] > predicate[0]:
        result.constituents.append(Constituent(*predicate, "predicate"))


# ---- the fragment, guarded ---------------------------------------------
def _statement(raw: str) -> Statement | None:
    try:
        return parse_statement(raw)
    except Exception:
        return None


def _prompt(text: str) -> Any:
    try:
        return parse_prompt(text)
    except Exception:
        return None


def _fact(statement: Statement) -> tuple:
    """One statement as ``(predicate, *arguments)``.

    The quantifier *is* the predicate for a categorical, so the four forms come
    out as ``all``/``no``/``some``/``some_not`` and an individual as ``isa``. The
    two negative forms are named rather than folded into their positives: a
    consumer that cannot tell "some dogs are not mammals" from "some dogs are
    mammals" would draw the opposite conclusion from it.
    """
    if isinstance(statement, Categorical):
        return (statement.quantifier, statement.subject, statement.predicate)
    return ("not_isa" if statement.negated else "isa",
            statement.individual, statement.predicate)


def _last_index(statements: list[Statement | None],
                query: Statement | None) -> int:
    """Which sentence the query came from, or -1.

    Matched by value because the statements are frozen dataclasses and
    ``parse_prompt`` builds them from the same sentences; the *last* match is
    taken, which is the rule ``parse_prompt`` itself used to choose the query.
    """
    if query is None:
        return -1
    for i in range(len(statements) - 1, -1, -1):
        if statements[i] == query:
            return i
    return -1


# ---- token offsets ------------------------------------------------------
def _locate(toks: list[str], sentence: list[str], at: int) -> tuple[int, int] | None:
    """Where a sentence's tokens sit in the whole text's tokens, at or after ``at``.

    A scan rather than a running offset: ``lexicon.sentences`` strips bullets and
    whitespace, so the sentences do not always concatenate back to the text, and
    a running offset would silently shift every later span.
    """
    if not sentence:
        return None
    n = len(sentence)
    for start in range(at, len(toks) - n + 1):
        if toks[start:start + n] == sentence:
            return (start, start + n)
    return None


def _layout(toks: list[str], start: int, end: int) -> _Layout | None:
    """The ``(lead, copula, subject, predicate)`` spans of one sentence.

    ``None`` when there is no copula to hang the two halves off, which is most of
    what falls outside the fragment.
    """
    while end > start and not _is_word(toks[end - 1]):
        end -= 1
    lead_start = _skip_marker(toks, start, end)
    copula = _find_copula(toks, lead_start, end)
    if copula is None:
        return None
    c0, c1 = copula

    if c0 == lead_start:
        # "Is Socrates a man?" — ``parse_statement`` rewrites the inversion by
        # moving the copula behind the first word, so the subject is that word.
        subject = (c1, min(c1 + 1, end))
        lead = (start, lead_start)
        pred_start = subject[1]
    else:
        subject = (_skip_quantifier(toks, lead_start, c0), c0)
        lead = (start, subject[0])
        pred_start = c1
    while pred_start < end and toks[pred_start].lower() in lexicon.ARTICLES:
        pred_start += 1
    return (lead, (c0, c1), subject, (pred_start, end))


def _skip_marker(toks: list[str], start: int, end: int) -> int:
    """Past leading punctuation and a conclusion marker, if there is one."""
    while start < end and not _is_word(toks[start]):
        start += 1
    lowered = [t.lower() for t in toks[start:end]]
    for marker in _MARKERS:
        if lowered[:len(marker)] == list(marker):
            start += len(marker)
            break
    while start < end and not _is_word(toks[start]):
        start += 1
    return start


def _skip_quantifier(toks: list[str], start: int, stop: int) -> int:
    """Past the quantifier and the filler in front of the subject noun.

    Never past the last token, because a subject has to be something: a bare
    "Some are mammals" leaves "some" as the subject rather than nothing at all,
    the same shape of guess ``parse_statement`` makes.
    """
    i = start
    while i < stop - 1:
        word = toks[i].lower()
        if i == start and word in lexicon.QUANTIFIERS:
            i += 1
        elif word in _FILLERS or not _is_word(toks[i]):
            i += 1
        else:
            break
    return i


def _find_copula(toks: list[str], start: int, end: int) -> tuple[int, int] | None:
    lowered = [t.lower() for t in toks[start:end]]
    for offset in range(len(lowered)):
        for copula in _COPULAS:
            n = len(copula)
            if lowered[offset:offset + n] == list(copula):
                return (start + offset, start + offset + n)
    return None


def _is_word(token: str) -> bool:
    return any(ch.isalnum() for ch in token)
