"""Credit shared between the claws that were right, not handed to each of them.

``omegaclaw_ctx`` weighs a claw by how often it was right when it fired, counted
by hand-raising: every claw that named the correct symbol gets a whole hit. On
this curriculum that is systematically generous, because the claws are not
independent. ``peer`` and ``mirror`` are two routes to the same coreferent node
and agree constantly; ``slotmate`` and ``echo`` both collapse to "the usual
label around here" in a flat subtree. When four claws point at the same correct
answer, hard counting records four independent solutions to one problem.

The consequence is not a calibration error, it is a *ranking* error, and it
lands exactly where the model makes its decision. A claw that is right only ever
in company earns the same reputation as one that is often right alone, so
``weigh`` cannot prefer the second, and the whole family's thesis is that
learning which claw to trust is where the score comes from.

**The fix is to treat "which claw was responsible" as unobserved, because it
is.** Nothing in the data says which route the generator took, and often several
routes are equally good explanations. So this model estimates reliabilities by
EM over that latent variable::

    E   for each example, split one unit of credit among the claws that named
        the right symbol, in proportion to how much the current reliabilities
        say each deserves
    M   reliability := credited / fired, per context and globally

Hard counting is the special case where the E-step gives every correct claw a
full unit instead of a share, so the two differ in exactly one line and the
comparison against ``omegaclaw_ctx-001`` isolates the estimator. ``weigh`` is
identical to that model's, deliberately.

**What this predicts, before the number arrives.** The claws that should lose
most are the vague aggregates — ``echo``, ``slotmate``, ``prev`` — which are
often right by coincidence in the company of a sharp claw, and the sharp ones
(``peer``, ``mirror``) should keep almost all their credit because when they are
right they are frequently right alone. If instead every claw's rate falls by
roughly the same factor, the redundancy is uniform, EM has only rescaled the
weights, and it will change nothing after normalisation — a null worth
recording, and the reason the fitted rates are printed by ``render``.

**Two properties of this EM, measured rather than assumed, because a mixture's
fixed point need not be unique and a rich-get-richer dynamic would make the
ranking an artefact of the initialisation.**

* Two claws that fire together and are *always* both right split their credit
  exactly evenly and stay there, for any number of rounds. The symmetric fixed
  point is stable, so perfect redundancy is reported as "these two are worth
  half each", not as an arbitrary winner. Pinned in the tests.
* Partial redundancy converges slowly, and in the direction that matters:
  a claw right only in another's company reads 0.500 after one round, 0.147
  after twelve and 0.0885 at the fixed point. Stopping early *understates* the
  redundancy, so the round budget is set from that measurement rather than
  guessed.

Initialisation is stated for the same reason: hard counts, so this model starts
exactly where ``omegaclaw_ctx`` stops and every departure is a departure from it.
"""

from __future__ import annotations

import collections
from typing import Hashable, Sequence

from ..omegaclaw import Claim, OmegaClaw
from ..registry import register

__all__ = ["OmegaClawEM"]


@register("omegaclaw_em-001",
          doc="OmegaClaw whose claw reliabilities are fitted by EM, not by counting.")
class OmegaClawEM(OmegaClaw):
    """``omegaclaw_ctx`` with the credit assignment made soft."""

    def __init__(self, cfg) -> None:
        super().__init__(cfg)
        #: Measured, not guessed. The first version stopped at twelve and was
        #: nowhere near the fixed point: on a two-claw case where one is only
        #: ever right in the other's company, the discounted claw reads 0.500
        #: after one round, 0.147 after twelve and 0.0885 at convergence, which
        #: it reaches around fifty. Twelve rounds would have reported a
        #: half-finished EM as a result, and the direction of the error is the
        #: dangerous one — it *understates* the redundancy this model exists to
        #: find. The tolerance below is what actually stops it; this is a
        #: ceiling.
        self.em_rounds = int(cfg.get("em_rounds", 200))
        self.em_tolerance = float(cfg.get("em_tolerance", 1e-4))

    def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
        # Identical to `omegaclaw_ctx` by design: the only difference between
        # the two models is how `reliability` was estimated.
        return claim.strength * self.reliability(name, ctx)

    def _estimate(self, records: Sequence[tuple]
                  ) -> tuple[dict[tuple, list[float]], dict[str, list[float]]]:
        fired_ctx: dict[tuple, float] = collections.defaultdict(float)
        fired_all: dict[str, float] = collections.defaultdict(float)
        for ctx, claims, _ in records:
            for name, _symbol in claims:
                fired_ctx[(ctx, name)] += 1.0
                fired_all[name] += 1.0
        if not fired_all:
            return {}, {}

        # Initialise at the hard counts, so round zero *is* `omegaclaw_ctx` and
        # every subsequent round is a departure from it that can be reported.
        evidence, totals = super()._estimate(records)
        rate = {name: totals[name][1] / max(totals[name][0], 1.0)
                for name in totals}

        for _ in range(self.em_rounds):
            credit_ctx: dict[tuple, float] = collections.defaultdict(float)
            credit_all: dict[str, float] = collections.defaultdict(float)
            for ctx, claims, label_id in records:
                # E-step. Only the claws that were right can be responsible;
                # the share each takes is its current reputation, normalised
                # over the ones in contention. A single correct claw takes the
                # whole unit, which is what makes hard counting the limiting
                # case rather than a different model.
                right = [name for name, symbol in claims if symbol == label_id]
                if not right:
                    continue
                weights = [max(rate.get(name, 0.0), 1e-6) for name in right]
                total = sum(weights)
                for name, w in zip(right, weights):
                    share = w / total
                    credit_ctx[(ctx, name)] += share
                    credit_all[name] += share
            # M-step, smoothed so a claw that fired twice cannot claim
            # certainty and a claw credited nothing does not fall to a hard
            # zero it can never climb back from.
            moved = 0.0
            for name, fired in fired_all.items():
                updated = (credit_all.get(name, 0.0) + 0.5) / (fired + 1.0)
                moved = max(moved, abs(updated - rate.get(name, 0.0)))
                rate[name] = updated
            if moved < self.em_tolerance:
                break

        evidence = {key: [fired_ctx[key], credit_ctx.get(key, 0.0)]
                    for key in fired_ctx}
        totals = {name: [fired_all[name], credit_all.get(name, 0.0)]
                  for name in fired_all}
        return evidence, totals

    def render(self) -> str:
        """The base report; its ``rate`` column is now a share, not a hit rate.

        Worth reading against ``omegaclaw_ctx``'s side by side — the difference
        between the two columns is how much of each claw's reputation was
        earned in company.
        """
        return super().render()
