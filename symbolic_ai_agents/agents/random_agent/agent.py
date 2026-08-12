"""Chance, and nothing else — the one row in the table that is genuinely a floor.

Every other agent here falls back on a prior that has *looked at the training
episodes*: which answers are common, which parameter-free cheat works on this
lesson set. That is the right fallback for an agent, because declining to answer
should not cost you the baseline you are being compared against. It is the wrong
thing for a floor, because a "random" row that quietly consulted the best
shortcut would report chance as whatever the shortcut scores and every lift in
the table would be understated by that amount.

So this agent sets ``use_prior = False`` and is uniform over the legal actions,
including the probes. Its return is what an agent that can read the *shape* of
the problem — how many options there are, how many tries remain — and nothing
about its content gets.

It is deliberately seeded from the observation rather than from a generator
carried across episodes. Two evaluations of this agent on the same episodes
produce the same trajectories, which matters because it is a floor: a floor that
moves by a point between runs makes every lift beside it unreproducible.
"""

from __future__ import annotations

import random

from ...envs.base import Observation
from ..base import Decision, PolicyAgent
from ..registry import register

__all__ = ["RandomAgent"]


@register("random", doc="Uniform over the legal actions. Chance, reproducibly.")
class RandomAgent(PolicyAgent):
    """Uniform, with the prior switched off so that chance means chance."""

    use_prior = False

    def act(self, obs: Observation) -> Decision:
        legal = [a for a in obs.choices if a not in self._refused] or list(obs.choices)
        if not legal:                                     # pragma: no cover
            return Decision(action="", confidence=0.0, why="no legal action")
        rng = random.Random(f"{obs.key}:{obs.step}:{self.get('seed', 0)}")
        return Decision(action=rng.choice(legal), confidence=1.0 / len(legal),
                        why=f"uniform over {len(legal)}")

    def n_parameters(self) -> int:
        return 0
