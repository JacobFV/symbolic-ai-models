"""The control: tokenize and stop.

Every other parser is read against this one. It assigns no classes, finds no
brackets and extracts no facts, so a reasoner paired with it is working from the
raw surface — which is exactly what "does parsing help?" needs on the other side
of the comparison.
"""

from __future__ import annotations

from ..data.tokenizer import split_words
from .base import ParseResult, Parser, register

__all__ = ["NoParser"]


@register("none", doc="No structure at all: the control every parser is read against.")
class NoParser(Parser):
    """Tokens in, tokens out."""

    def parse(self, text: str) -> ParseResult:
        return ParseResult(tokens=split_words(text))
