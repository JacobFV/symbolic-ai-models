"""The symbolalg clause parser, behind the :class:`Parser` interface.

``symbolalg`` already carried a hand-written parser — clause splitting, word and
number tokenization, and a guess at which token names the relation. It was welded
to that one reasoner, so nothing else could use it and nothing could score it:
the only evidence it worked was that ``symbolalg`` worked, which confounds the
parse with the reasoning over it.

This wraps it and nothing more. The heuristics stay in
:mod:`symbolic_ai_models.models.symbolalg.parse` and are imported, not copied, so
there is exactly one clause splitter in the repo and the wrapper cannot drift
away from the thing it claims to expose. What is new is only the translation into
a :class:`ParseResult`:

* every clause becomes a bracket, so "did it group anything" is answerable;
* every token gets a coarse class from its position in its clause — a number, the
  clause-initial word, or an argument — which is the same three-way distinction
  ``facts_from_text`` already reasons with, made explicit;
* the ``Pred`` symbols become plain tuples, because a consumer of a parse should
  not have to import ``symbolalg``'s representation to read one.

It is a weak parser and it stays weak here. Clauses break on commas, so
``"Agent at (0, 3)"`` is two clauses; the head guess is a guess. The point of
putting it in the matrix is to find out how much a written-down parser buys over
:class:`~symbolic_ai_models.parsers.none.NoParser`, not to claim it is right.
"""

from __future__ import annotations

from typing import Any

from ..models.symbolalg.parse import (clauses, facts_from_text,
                                      options_from_text, question_of, tokens)
from .base import Constituent, ParseResult, Parser, register

__all__ = ["RegexParser"]


@register("regex", learned=False,
          doc="Clause brackets and head/argument classes, from symbolalg's written rules.")
class RegexParser(Parser):
    """Clauses to brackets, ``(head, *args)`` to facts. Nothing is learned."""

    def parse(self, text: str) -> ParseResult:
        try:
            raw = tokens(text)
        except Exception:
            # A parser that raises on odd input is unusable in an evaluation
            # loop, and "no structure" is a legitimate answer here.
            return ParseResult()
        result = ParseResult(tokens=[str(t) for t in raw])
        try:
            self._fill(text, raw, result)
        except Exception:
            return ParseResult(tokens=result.tokens)
        return result

    # ---- structure ----------------------------------------------------
    def _fill(self, text: str, raw: list[Any], result: ParseResult) -> None:
        # Numbers are already distinguished by the tokenizer — ``tokens`` coerces
        # them — so the class of a token is read off the token, not re-guessed
        # with a second regex that could disagree with the first.
        result.classes = {i: ("arg" if isinstance(t, str) else "num")
                          for i, t in enumerate(raw)}

        spans = _clause_spans(text, result.tokens)
        question = question_of(text)
        marked = False
        for start, end, clause in spans:
            # Only the first clause equal to the question clause is labelled, so
            # a prompt that repeats a sentence does not end up with two questions.
            is_question = not marked and clause == question
            marked = marked or is_question
            result.constituents.append(
                Constituent(start, end, "question" if is_question else "clause"))
            if result.classes.get(start) == "arg":
                result.classes[start] = "head"

        result.facts = [f for f in (_plain(s) for s in facts_from_text(text))
                        if f is not None]
        result.meta = {"question": question, "options": options_from_text(text)}


def _clause_spans(text: str, toks: list[str]) -> list[tuple[int, int, str]]:
    """``(start, end, clause)`` for each clause, by walking clauses in order.

    The clause splitter and the tokenizer are separate regexes and do not always
    agree: the splitter cuts on ``.`` and ``,``, which also occur *inside* tokens
    (``3.5``, ``1,000``), and where that happens a clause's tokens are not a
    slice of the whole text's tokens and every offset after it is wrong. So the
    slice is checked, and bracketing stops at the first disagreement rather than
    emitting spans that point at the wrong words. The classes survive it, which
    is why they are assigned independently of this walk.
    """
    spans: list[tuple[int, int, str]] = []
    at = 0
    for clause in clauses(text):
        ct = [str(t) for t in tokens(clause)]
        if not ct:
            continue
        if toks[at:at + len(ct)] != ct:
            break
        spans.append((at, at + len(ct), clause))
        at += len(ct)
    return spans


def _plain(sym: Any) -> tuple | None:
    """A ``Pred`` symbol as ``(name, *arguments)`` of plain str/number.

    Dropped rather than coerced when an argument is not an atom: a fact holding
    something a consumer cannot read is worse than one fewer fact.
    """
    value = getattr(sym, "value", None)
    if not isinstance(value, tuple) or not value:
        return None
    name, *args = value
    out: list[Any] = [str(name)]
    for arg in args:
        v = getattr(arg, "value", arg)
        if not isinstance(v, (str, int, float)) or isinstance(v, bool):
            return None
        out.append(v)
    return tuple(out)
