"""One rule set, selectively applied — and told which language it is in.

Registered beside ``omegaclaw_ctx-001``, differing in one method. ``perceive``
appends the episode's language to the structural context key, so ``weigh``
learns a claw's reliability **per language** instead of pooling it. Everything
else — the claw set, the mixture, the held-out calibration, the type head — is
inherited bit for bit, so the difference between the two rows is the value of
the language partition and cannot be anything else.

The design argument, from ``APPROACH.md``: languages share composition,
consolidation, abstraction and association rules through common descent, so one
parser per language throws the sharing away, while one rule set conditioned on
which language this is keeps it. ``OmegaClaw.weigh(name, ctx, claim)`` is
already exactly that shape.

Why this model is expected to lose, and why it is registered anyway
-------------------------------------------------------------------
``Lesson.structured`` takes no language. The term graph is byte-identical across
all seven packs — 179 lessons x 3 seeds, every one of 537 episodes per pack —
and the eleven claws this model inherits read only the graph. So the seven
per-language evidence tables are seven estimates of **one** distribution, and
splitting the counts seven ways is data-thinning with nothing bought.

That is arithmetic about the corpus, not a hypothesis about the model, and it
means this row's job is to *quantify* a null that was predictable in advance:
how much does an uninformative refinement of the context cost, on a table this
size? The model that can actually use the language is
``omegaclaw_textlang-002``, whose claws read the prose.

The control that makes the reading safe is ``omegaclaw_const-002``: the same
extra context dimension, carrying a constant. If ``const`` and ``ctx`` score
identically and ``lang`` does not, the difference is the partition and not the
plumbing.
"""

from __future__ import annotations

from typing import Hashable

from ..omegaclaw import Claim, OmegaClaw
from ..registry import register
from ..symbolic import GraphView

__all__ = ["OmegaClawLanguage"]


@register("omegaclaw_lang-002",
          doc="OmegaClaw with per-language, per-context claw reliability.")
class OmegaClawLanguage(OmegaClaw):
    """``omegaclaw_ctx``, with the language folded into the context key."""

    def perceive(self, view: GraphView, node: int) -> Hashable:
        return (view.language, *OmegaClaw.perceive(self, view, node))

    def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
        return claim.strength * self.reliability(name, ctx)
