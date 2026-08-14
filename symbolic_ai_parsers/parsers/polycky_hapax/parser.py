"""``polycky-hapax``: the old unseen-token argument estimator, kept as an arm.

``Grammar._fit_lexicon`` estimates ``P(ARG | unseen)`` from training hapaxes and
gets ~0.9 monolingually, on the sound reasoning that a token seen once is a
nonce symbol and nonce symbols are arguments.

**On a parallel corpus that reasoning inverts, and it was not obvious until it
was measured.** An argument is copied verbatim into all 46 renderings of the
same seed, so it is never a hapax; a rare *translated frame word* is a hapax in
exactly one language. The same estimator therefore returns something near zero
on the mixture and tells the parser that every unseen token is frame material.

So this arm is not "the old constant" — it is the old *estimator*, which is not
scale-free, and the point of keeping it registered is that the correction in
``polycky-001`` is measured against it rather than assumed.
"""

from __future__ import annotations

from ...base import register
from ..polyglot import PolyParser


@register("polycky-hapax", learned=True,
          doc="control: P(ARG | unseen token) from hapaxes, as cky-001 estimates it")
class PolyCKYHapax(PolyParser):
    segment = "v2"
    abstract = "classes"
    condition = "none"
    oov = "hapax"
