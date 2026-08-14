"""``polycky-v1seg``: the same parser on the repo's shared word splitter.

``split_words`` runs scriptio continua together -- ``alice和面包`` is one
token, so the argument cannot be found -- and shatters scripts whose combining
marks Python does not count as word characters. This arm exists because the
largest measured effects in this repo have been harness decisions rather than
architectures, and segmentation is a harness decision sitting underneath every
cross-language parser number ever quoted here.
"""

from __future__ import annotations

from ...base import register
from ..polyglot import PolyParser


@register("polycky-v1seg", learned=True,
          doc="control: the shared split_words segmentation instead of the script-aware one")
class PolyCKYV1Seg(PolyParser):
    segment = "v1"
    abstract = "classes"
    condition = "none"
    oov = "lolo"
