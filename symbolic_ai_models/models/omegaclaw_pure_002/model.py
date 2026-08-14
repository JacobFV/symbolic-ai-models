"""The same four models with the shared memorising fallback switched off.

``RuleBasedModel.structural_fallback`` donates every rule-based model a lookup
table of the commonest label per structural context. It is worth a real slice of
accuracy that nobody attributes to it, and it is *the same* table for every row,
so a difference between two models that both lean on it is a difference measured
through a shared denominator. The precedent is ``vsa_perm_pure-002``, registered
for exactly this reason.

Here it matters more than usual, because the contrasts being drawn are small by
design. ``omegaclaw_lang-002`` differs from ``omegaclaw_ctx-001`` only in the
context key, and ``omegaclaw_textlang-002`` from ``omegaclaw_text-002`` only in
whether the language is in it. A shared floor that answers a good share of the
questions compresses exactly those gaps towards zero, so a null read off the
fallback-on rows alone would be weaker evidence than it looks. These four rows
are how the same contrasts are read without it.

They inherit their siblings' behaviour and change one class attribute, so the
pairs cannot drift.
"""

from __future__ import annotations

from ..omegaclaw_const_002 import OmegaClawConstant
from ..omegaclaw_ctx_001 import OmegaClawContext
from ..omegaclaw_lang_002 import OmegaClawLanguage
from ..omegaclaw_text_002 import OmegaClawText
from ..omegaclaw_textlang_002 import OmegaClawTextLanguage
from ..registry import register

__all__ = ["OmegaClawContextPure", "OmegaClawConstantPure",
           "OmegaClawLanguagePure", "OmegaClawTextPure",
           "OmegaClawTextLanguagePure"]


@register("omegaclaw_ctx_pure-002",
          doc="omegaclaw_ctx-001 without the shared memorising fallback.")
class OmegaClawContextPure(OmegaClawContext):
    """The anchor, on its own reasoning. Everything else here reads against it."""

    structural_fallback = False


@register("omegaclaw_const_pure-002",
          doc="omegaclaw_const-002 without the shared memorising fallback.")
class OmegaClawConstantPure(OmegaClawConstant):
    """The constant control, with the floor removed as well.

    Registered rather than argued: the bijection argument says this must equal
    ``omegaclaw_ctx_pure-002`` exactly, and the cheapest way to be sure the
    fallback was not quietly hiding a difference is to print both rows.
    """

    structural_fallback = False


@register("omegaclaw_lang_pure-002",
          doc="omegaclaw_lang-002 without the shared memorising fallback.")
class OmegaClawLanguagePure(OmegaClawLanguage):
    """What the language partition costs when nothing else is answering."""

    structural_fallback = False


@register("omegaclaw_text_pure-002",
          doc="omegaclaw_text-002 without the shared memorising fallback.")
class OmegaClawTextPure(OmegaClawText):
    """The surface reach on its own. The zero for the row below."""

    structural_fallback = False


@register("omegaclaw_textlang_pure-002",
          doc="omegaclaw_textlang-002 without the shared memorising fallback.")
class OmegaClawTextLanguagePure(OmegaClawTextLanguage):
    """The experiment, read without a shared floor underneath it."""

    structural_fallback = False
