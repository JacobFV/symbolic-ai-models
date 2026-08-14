"""``polycky-crc``: the nonsense split ``polycky-002`` has to beat.

Identical in every respect except that the conditioning value is
``crc32(instance_id)`` modulo the number of training languages. Same
cardinality, same expected bucket size, same backoff, no information: any gain
here is what conditioning-shaped machinery buys from splitting the data at
all.

Registered with a word suffix, so ``polycky`` can never resolve to it.
"""

from __future__ import annotations

from ...base import register
from ..polyglot import PolyParser


@register("polycky-crc", learned=True,
          doc="control: rule weights conditioned on a crc32 bucket of the same cardinality")
class PolyCKYCrc(PolyParser):
    segment = "v2"
    abstract = "classes"
    condition = "crc"
    oov = "lolo"
