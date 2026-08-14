"""``polycky-002``: ``polycky-001`` with rule weights conditioned on language.

One rule set, selectively applied -- the design ``APPROACH.md`` argues for,
with language as the conditioning variable. The weights back off onto the
global distribution, so a language never fitted on scores *exactly* the
unconditioned rule set and leave-one-language-out needs no special case.

What refutes it is not "does it beat ``polycky-001``" but "does it beat
``polycky-crc``", which buckets the same episodes into the same number of
meaningless groups. Language conditioning has already lost that comparison
once in this repo, on the reasoner side.
"""

from __future__ import annotations

from ...base import register
from ..polyglot import PolyParser


@register("polycky-002", learned=True,
          doc="seg=v2, classes, rule weights conditioned on language")
class PolyCKY002(PolyParser):
    segment = "v2"
    abstract = "classes"
    condition = "language"
    oov = "lolo"
