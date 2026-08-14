"""``omegaclaw_ctx`` with three claws that read the prose. No language told.

The pair ``omegaclaw_text-002`` / ``omegaclaw_textlang-002`` is the real
experiment, and this is its zero. Both reach with the same fourteen claws — the
eleven graph claws plus the three surface ones in
:mod:`~symbolic_ai_models.models.omegaclaw.surface` — and only
``textlang`` is told which language rendered the prompt. Their difference is
therefore the value of **knowing the language**, with the reach held fixed, which
is the one contrast the whole exercise is about.

This row separately answers a question the family has asked before and got a
null on: is a wider reach worth anything? ``omegaclaw_reach-001`` added the most
reliable single claw ever measured here and still lost to
``omegaclaw_ctx-001``, and the family's summary of itself is "+0.107 lift for
learning which rule to trust in which context, ~0 for widening the rule set".
``text-002`` minus ``ctx-001`` re-asks that with operators that read a surface
none of the eleven can see.
"""

from __future__ import annotations

from typing import Hashable, Mapping

from ..omegaclaw import TEXT_CLAWS, Claim, Claw, OmegaClaw
from ..registry import register

__all__ = ["OmegaClawText"]


@register("omegaclaw_text-002",
          doc="OmegaClaw reaching into the prompt as well as the graph.")
class OmegaClawText(OmegaClaw):
    """Fourteen claws, per-context reliability, no language in the key."""

    def claws(self) -> Mapping[str, Claw]:
        return TEXT_CLAWS

    def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
        return claim.strength * self.reliability(name, ctx)
