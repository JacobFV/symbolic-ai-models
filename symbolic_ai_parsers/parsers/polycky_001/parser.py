"""``polycky-001``: one class-based rule set over a mixture of languages.

The head of the family, and the arm every other one is a single change away
from. Script-aware segmentation, frame words replaced by induced classes with
a wildcard for the unseen ones, out-of-vocabulary argument rate estimated for
the held-out-language case, and **no conditioning** -- one global weight per
rule.

Unconditioned on purpose: the claim tested here is that a grammar over classes
transfers, and conditioning is a separate claim with a separate control
(``polycky-crc``). Reading a conditioned number as evidence for abstraction is
how two effects become one story.
"""

from __future__ import annotations

from ...base import register
from ..polyglot import PolyParser


@register("polycky-001", learned=True,
          doc="seg=v2, classes, unconditioned; the multilingual rule set")
class PolyCKY001(PolyParser):
    segment = "v2"
    abstract = "classes"
    condition = "none"
    oov = "lolo"
