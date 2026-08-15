"""The abstention path itself, as a row. What "I have nothing to say" scores.

:mod:`symbolic_ai_agents.agents.base` states the design in its own docstring:

    Confidence zero is abstention, and it lands the agent exactly on the prior.
    Because the prior *is* the floor [...] an agent that declines to answer
    scores the floor rather than scoring chance.

That is a claim with a number in it, and until this agent existed the number was
only reachable *by accident* — through a ``graphread`` pointed at a model that
happens to emit nothing on the chosen channel, which is how
``notes/findings/2026-08-13-abstention-on-repair-is-below-chance.md`` measured it
on six lessons. Reaching a control through a model that fails is fragile in the
worst way: fix the model and the control silently becomes something else.

So this is the control stated directly. :meth:`prefer` returns
:data:`~symbolic_ai_agents.agents.base.ABSTAIN` unconditionally and nothing else
is overridden, which makes every row it produces a pure function of the shared
prior — the same prior every other agent falls back to, fitted the same way on
the same training episodes.

Why it belongs in the table rather than in a script
---------------------------------------------------
Because an agent's score on :mod:`symbolic_ai_agents.envs.repair` mixes *how
often it spoke* with *how good it was when it did*, in a ratio that is only
readable against what silence is worth. An agent speaking on 96.9% of decisions
and one speaking on 47% are not comparable until this row is on the page, and it
has to be measured under the same config as the rows it is read against — a
number carried over from a different sweep would be a floor fitted differently,
which :func:`~symbolic_ai_agents.envs.base.reference_floor` records as the way
this package has already published a policy beating itself.

It is deliberately **not** one of :data:`~symbolic_ai_agents.envs.base.FLOOR_POLICIES`.
The floor is the best of ``random``, ``shortcut`` and ``context`` — the best
thing that understands nothing — and abstention is not a candidate for that. It
is the *cost of silence*, which is a different quantity and, on ``repair``, a
much lower one.
"""

from __future__ import annotations

from ...envs.base import Observation
from ..base import ABSTAIN, Preference, PolicyAgent
from ..registry import register

__all__ = ["AbstainAgent"]


@register("abstain",
          doc="Never speaks. What an abstention is worth, as a measured row.")
class AbstainAgent(PolicyAgent):
    """Abstains on every decision, so its row is the shared prior and nothing else."""

    def prefer(self, obs: Observation) -> Preference:
        return ABSTAIN

    def render(self) -> str:
        shortcut = self.shortcut.name if self.shortcut else "none"
        return (f"=== {self.name}: the abstention path ===\n"
                f"  abstains on every decision; the row is "
                f"{len(self.action_prior):,} prior counts with "
                f"{self.shortcut_purity:.3f} of the mass on `{shortcut}`")
