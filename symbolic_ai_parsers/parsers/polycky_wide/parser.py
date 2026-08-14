"""``polycky-wide``: ``polycky-001`` with the wildcard beam taken off.

Registered after the first result, to try to break it. ``polycky-1class`` beat
the full class induction on every held-out metric, and there is a way that could
be an artefact rather than a finding: an unknown token is tried against at most
``WILDCARD_BEAM`` class symbols, and the one-class control has exactly one class
and therefore **no beam at all**. A bound tight enough to starve the full
induction would look exactly like "the class identities carry nothing".

So this arm sets the beam to 64 — wider than the class count at any trie state
this grammar builds, which makes the search exhaustive over classes. If it
closes the gap to ``polycky-1class``, the earlier reading was a search bound
wearing a finding's clothes and the write-up is wrong. If it does not, the beam
was never binding and the finding stands.
"""

from __future__ import annotations

from ...base import register
from ..polyglot import PolyParser


@register("polycky-wide", learned=True,
          doc="refuter: polycky-001 with the wildcard beam widened to 64")
class PolyCKYWide(PolyParser):
    segment = "v2"
    abstract = "classes"
    condition = "none"
    oov = "lolo"
    beam = 64
