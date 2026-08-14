"""``polycky-literal``: the abstraction turned off, everything else held.

Right-hand sides carry literal words, as ``cky-001``'s do, so there is no
wildcard and nothing to match in a language whose frame words are all unseen.
Same segmentation, same mixture, same decode, same floors -- which is what
makes the gap between this and ``polycky-001`` the abstraction, and not the
four other things that changed at the same time.
"""

from __future__ import annotations

from ...base import register
from ..polyglot import PolyParser


@register("polycky-literal", learned=True,
          doc="control: literal words in the right-hand side, abstraction off")
class PolyCKYLiteral(PolyParser):
    segment = "v2"
    abstract = "literal"
    condition = "none"
    oov = "lolo"
