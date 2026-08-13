"""``template-002``: the token-counting features taken out of ``-001``'s lookup.

Registered as a new version rather than as an edit to ``-001``, so the correction
is a row in the same sweep. What changed and why is in
:mod:`symbolic_ai_parsers.features`: the features ``-001`` calls "layout" include
token counts and token lengths, and Chinese retokenises the same document
wholesale. Settled on held-out **training** episodes rendered in each language —
seeds 200-201, nowhere near the eval range — and only then run on eval.
"""

from __future__ import annotations

from ...base import register
from ..template import TemplateParser


@register("template-002", learned=True,
          doc="Shape lookup (punctuation and lines only), lexicon from training episodes.")
class TemplateShape(TemplateParser):
    lookup = "shape"
    seeded = False
