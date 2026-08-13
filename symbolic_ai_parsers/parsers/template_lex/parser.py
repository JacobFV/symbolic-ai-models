"""``template-lex``: ``template-001`` with the lexicon handed to it.

The isolated half of the dictionary shortcut. Same lookup as ``template-001``,
same everything else; the only difference is that the frame/content judgement
comes from :meth:`~symbolic_ai_parsers.lexicon.Lexicon.from_curriculum` instead
of being estimated from the training episodes. It exists so that "the dictionary
helped" and "word-identity retrieval helped" are separable, since
``template-seeded`` changes both at once and a bundle that moves a number only
tells you a number moved.

Word-suffixed on purpose: a bare ``template`` must never resolve to it.
"""

from __future__ import annotations

from ...base import register
from ..template import TemplateParser


@register("template-lex", learned=True,
          doc="Layout lookup, lexicon seeded from the full curriculum vocabulary.")
class TemplateSeededLexicon(TemplateParser):
    lookup = "layout"
    seeded = True
