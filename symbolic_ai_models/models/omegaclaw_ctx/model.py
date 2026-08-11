"""Trust a claw as much as it has earned *in this kind of place*.

One line different from ``omegaclaw_flat``: the weight is the claw's declared
strength multiplied by how often it was right when it fired in this structural
context, shrunk towards its own global rate. Everything else — the claw set, the
context key, the mixture, the calibration, the type head — is inherited
unchanged, so the difference between the two models' scores is the value of
per-context credit assignment and cannot be anything else.

Why multiply rather than replace the strength: the strengths encode which
operators are *specific* (a peer match names one node; ``echo`` names a
majority), and specificity is not something the hit rate recovers, because a
vague claw that is often right by coincidence earns a high rate honestly. The
product asks for both. Measured, replacing rather than multiplying was worth
less — recorded in the family's test suite rather than left as an assertion.

This is deliberately close to what ``workspace`` does with its codelet policy
and to what ``routes`` does with its context prior. That is the point of running
it: if a policy re-expressed in forty lines on top of the ABC lands where the
hand-written one lands, the substrate is carrying its weight; if it lands well
below, the abstraction has cost something and the comparison should say so.
"""

from __future__ import annotations

from typing import Hashable

from ..omegaclaw import Claim, OmegaClaw
from ..registry import register

__all__ = ["OmegaClawContext"]


@register("omegaclaw_ctx",
          doc="OmegaClaw with per-context claw reliability; weighted mixture.")
class OmegaClawContext(OmegaClaw):
    """Weighted vote, where the weights were measured in this context."""

    def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
        return claim.strength * self.reliability(name, ctx)
