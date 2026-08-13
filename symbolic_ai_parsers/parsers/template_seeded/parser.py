"""``template-seeded``: the whole dictionary shortcut, word lookup included.

Both halves at once — a lexicon from the full curriculum vocabulary *and* a
nearest-neighbour lookup on word identity. This is what one would actually build
to make an evaluation cheap, and it is registered as a knob with two controls
(``template-001`` unseeded, ``template-lex`` seeded but layout-looked-up) rather
than as a default that hides the comparison.
"""

from __future__ import annotations

from ...base import register
from ..template import TemplateParser


@register("template-seeded", learned=True,
          doc="Word lookup and seeded lexicon: the whole dictionary shortcut.")
class TemplateSeeded(TemplateParser):
    lookup = "words"
    seeded = True
