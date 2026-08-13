"""``template-001``: layout lookup, lexicon estimated from the training episodes.

The first learned parser written here, and the one whose pre-registered
prediction was refuted. Its lookup uses ``layout_features``, which were meant to
be language-independent and are not: they count tokens and measure their length,
which is a fact about the tokenisation rather than the document. It is left
registered, unedited, because ``template-002`` is the correction and the pair is
the measurement — see :mod:`symbolic_ai_parsers.features`.
"""

from __future__ import annotations

from ...base import register
from ..template import TemplateParser


@register("template-001", learned=True,
          doc="Layout lookup, lexicon estimated from training episodes.")
class TemplateLayout(TemplateParser):
    lookup = "layout"
    seeded = False
