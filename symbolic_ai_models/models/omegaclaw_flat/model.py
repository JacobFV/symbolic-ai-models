"""The control: reach with every claw and never learn which one to trust.

The first member of the family exists to make the other two interpretable. It
implements ``weigh`` as ``claim.strength`` — the operator's own declared
conviction, written down by hand in
:data:`~symbolic_ai_models.models.omegaclaw.base.CLAWS` and identical for every
model in the family — so its evidence table is gathered, stored and then never
consulted.

That makes it the honest zero of the comparison. Whatever ``omegaclaw_ctx``
scores above this is what *learning which claw to trust* was worth; anything
this model already gets is what the claw set was worth on its own, before any
control policy at all.

It is not quite a no-learning model, and saying otherwise would be false: it
still inherits the held-out confidence calibration, so it learns how much its
own agreement is worth even though it does not learn which claw is right. That
is deliberate — the alternative is a control that differs from its siblings in
two places at once, which would make the contrast unreadable.
"""

from __future__ import annotations

from typing import Hashable

from ..omegaclaw import Claim, OmegaClaw
from ..registry import register

__all__ = ["OmegaClawFlat"]


@register("omegaclaw_flat-001",
          doc="OmegaClaw control: fixed per-claw strengths, no learned trust.")
class OmegaClawFlat(OmegaClaw):
    """Every claw counts what it always counts, wherever it fires."""

    def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
        return claim.strength
