"""Same weights as ``omegaclaw_ctx``; commit to one claw instead of mixing.

The third member changes the *aggregation* and holds everything else fixed. It
weighs claims exactly as ``omegaclaw_ctx`` does — the one line is duplicated
rather than inherited, and a test pins the two implementations to agree — and
then, instead of mixing every claim into a distribution, it hands all the mass
to the single best-weighted claw and reports that weight as its raw score.

So the family gives two clean contrasts along one axis each::

    flat -> ctx     does learned per-context trust pay?
    ctx  -> rank    does mixing beat committing to the best single claw?

Winner-take-all is not obviously worse, which is why it is worth measuring. It
is what a decision list does, it is what ``brill``'s last firing rule does, and
it has a real argument behind it: when two claws point at different symbols,
usually only one of them is *reasoning* and the other is coincidence, so
averaging them contaminates a good answer with a bad one. The counter-argument
is the one ``ilp`` records — agreement between rules is the main evidence a
theory of several rules provides, and first-past-the-post throws it away.

The raw score is the winner's weight rather than its share of the total, because
a share is meaningless once all the mass is on one symbol: it would be 1.0 for
every prediction and the confidence map would have nothing to calibrate
against. Making the score the winning claw's measured reliability instead means
this model's stated confidence is, before calibration, already a claim the
evidence supports.
"""

from __future__ import annotations

from typing import Hashable, Mapping, Sequence

from ..omegaclaw import Claim, OmegaClaw, Weighted
from ..registry import register

__all__ = ["OmegaClawRank"]


@register("omegaclaw_rank-001",
          doc="OmegaClaw with per-context claw reliability; the best claw takes all.")
class OmegaClawRank(OmegaClaw):
    """Rank the claws that fired, and believe the top one."""

    def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
        # Identical to `omegaclaw_ctx` by design; see the module docstring.
        return claim.strength * self.reliability(name, ctx)

    def commit(self, weighted: Sequence[Weighted]
               ) -> tuple[Mapping[int, float], float] | None:
        best: Weighted | None = None
        for entry in weighted:
            # Strictly greater, so a tie goes to the earlier claw and the
            # iteration order of `CLAWS` is the tie-break. That order is fixed
            # in one place and does not depend on a set or on hash seeding.
            if entry[2] > 0.0 and (best is None or entry[2] > best[2]):
                best = entry
        if best is None:
            return None
        # Claims agreeing with the winner still count towards the score, since
        # two claws pointing at the same symbol is evidence and the calibrator
        # can only use it if it reaches the calibrator.
        agree = sum(1 for entry in weighted
                    if entry[1].symbol == best[1].symbol and entry[2] > 0.0)
        raw = min(best[2] * (1.0 + 0.1 * (agree - 1)), 1.0)
        return {best[1].symbol: 1.0}, raw

    def render(self) -> str:
        """The base report, plus the ranking this model actually acts on."""
        lines = [super().render(), "  --- global ranking (ties break upwards) ---"]
        order = sorted(self.claw_totals, key=lambda n: -self.reliability(n))
        for name in order:
            lines.append(f"  {name:<14} {self.reliability(name):.3f}")
        return "\n".join(lines)
