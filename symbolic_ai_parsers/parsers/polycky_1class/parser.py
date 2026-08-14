"""``polycky-1class``: do the induced class *identities* carry anything?

The shared/translated split is kept -- punctuation and untranslated frame
words stay literal -- but every translated token collapses into one symbol. If
this matches ``polycky-001``, the grammar is a positional template over
punctuation and the class induction is decoration, which is ``template-002``'s
mechanism and would have to be written up as such.
"""

from __future__ import annotations

from ...base import register
from ..polyglot import PolyParser


@register("polycky-1class", learned=True,
          doc="control: every abstracted frame token collapsed into one class")
class PolyCKYOneClass(PolyParser):
    segment = "v2"
    abstract = "one"
    condition = "none"
    oov = "lolo"
