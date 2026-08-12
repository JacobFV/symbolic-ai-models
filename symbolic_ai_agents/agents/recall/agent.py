"""Learn from what actually paid, rather than from what was labelled correct.

Every other agent in this package is fitted on the *gold answers* of the
training episodes: :mod:`symbolic_ai_agents.agents.context` counts what filled
each kind of slot, :mod:`symbolic_ai_agents.agents.shortcut` measures which
cheats were right. That is supervision, and it is available here only because
the curriculum happens to know the answer. It is not available in an environment
in general, and it is not what makes an environment different from a dataset.

This agent is fitted on **its own rollouts**. It acts in the training
environments, records the return that followed each ``(context, action)`` pair,
and afterwards prefers the pairs that paid. Nothing it learns comes from a label;
everything comes from a reward it was handed after committing to something.

Two decisions are worth naming, because both were wrong in the first version.

**The value is the return from the step onward, not the immediate reward.** A
myopic learner is a perfectly good policy for :mod:`symbolic_ai_agents.envs.choice`
and :mod:`symbolic_ai_agents.envs.repair`, where the reward for an action
arrives on the same step. It is a *degenerate* policy for
:mod:`symbolic_ai_agents.envs.probe`, where a probe costs ``-cost`` immediately
and pays only through the answer it makes possible: a myopic learner sees every
probe lose money and learns never to ask. Crediting each action with the return
that followed it — a plain Monte Carlo return, no discounting, because the
horizons here are single digits — is what lets this agent discover that asking
can be worth it. Whether it *does* discover that is an empirical question and is
what the ``probe`` column is for.

**Exploration is seeded, not random.** During fitting the agent takes a
non-preferred action with probability ``epsilon``, chosen from a generator keyed
on the episode and the round. Two fits on the same training episodes therefore
produce the same table. A fitted agent whose table moved between runs would make
every number measured from it unreproducible, and the movement would be
invisible.
"""

from __future__ import annotations

import collections
import random

from ...envs.base import Environment, Move, Observation
from ...envs.rollout import rollout
from ..base import ABSTAIN, Decision, Preference, PolicyAgent, shuffled
from ..registry import register

__all__ = ["RecallAgent"]


@register("recall", doc="Fitted on its own rollouts: prefer what actually paid.")
class RecallAgent(PolicyAgent):
    """Try things in training; remember the return; do more of what worked."""

    LEARNED = ("value", "rounds", "epsilon")

    def __init__(self, extra=None) -> None:
        super().__init__(extra)
        #: ``(environment, context, action) -> [times taken, total return]``
        self.value: dict[tuple, list[float]] = {}
        self.rounds = int(self.get("rounds", 2))
        self.epsilon = float(self.get("epsilon", 0.35))
        self.smoothing = float(self.get("smoothing", 2.0))
        self._exploring = False
        self._round = 0

    # ---- fitting --------------------------------------------------------
    def fit(self, ctx) -> None:
        self.tok = ctx.tok
        self._fit_prior(ctx.episodes)
        envs = list(ctx.envs.values()) or self._default_envs()
        self.value = {}
        self._fitted = True                 # it must be able to act to explore
        self._exploring = True
        try:
            for self._round in range(max(self.rounds, 1)):
                for env in envs:
                    for ep in shuffled(ctx.episodes, seed=self._round):
                        self._credit(env, rollout(env, self, ep, tok=ctx.tok))
                    if ctx.on_step:
                        ctx.on_step(self._round, self.rounds,
                                    f"{env.name}: {len(self.value)} cells")
        finally:
            self._exploring = False

    def _default_envs(self) -> list[Environment]:
        from ...envs import REGISTRY, build
        return [build(n) for n in sorted(REGISTRY)]

    def _credit(self, env: Environment, traj) -> None:
        """Give every action the return that followed it.

        Computed as a suffix sum over the trajectory's rewards — the plain Monte
        Carlo return, undiscounted. See the module docstring for why the
        immediate reward is not enough.
        """
        suffix = 0.0
        for move in reversed(traj.moves):
            suffix += move.step.reward
            key = (env.name, env.context_key(move.obs), move.action)
            cell = self.value.setdefault(key, [0.0, 0.0])
            cell[0] += 1.0
            cell[1] += suffix

    # ---- acting ---------------------------------------------------------
    def act(self, obs: Observation) -> Decision:
        if not self._exploring:
            return super().act(obs)
        legal = [a for a in obs.choices if a not in self._refused] or list(obs.choices)
        if not legal:                                     # pragma: no cover
            return Decision(action="", confidence=0.0, why="no legal action")
        rng = random.Random(f"{obs.key}:{obs.step}:{self._round}")
        if rng.random() < self.epsilon:
            return Decision(action=rng.choice(legal), confidence=0.0,
                            why=f"exploring (round {self._round})")
        return super().act(obs)

    def prefer(self, obs: Observation) -> Preference:
        env = self.env
        if env is None or not self.value:
            return ABSTAIN
        ctx = env.context_key(obs)
        legal = [a for a in obs.choices if a not in self._refused] or list(obs.choices)

        rows = [(a, self.value.get((env.name, ctx, a))) for a in legal]
        seen = [(a, cell) for a, cell in rows if cell and cell[0] > 0]
        if not seen:
            return ABSTAIN

        # Shrunk towards the environment's own mean return, so an action taken
        # once and paid once is not evidence of certainty. Shrinking to the
        # *observed* mean rather than to zero matters on `probe`, where every
        # return is dragged below zero by the cost and shrinking to zero would
        # make a rarely-tried probe look better than a well-tried answer.
        prior = self._mean_return(env.name)
        scored = {a: (cell[1] + self.smoothing * prior) / (cell[0] + self.smoothing)
                  for a, cell in seen}
        low = min(scored.values())
        weights = {a: v - low + 1e-6 for a, v in scored.items()}
        spread = max(scored.values()) - low
        # Raw score is how far the best action stands above the rest, scaled by
        # the spread the table has actually seen. Flat evidence means an honest
        # abstention rather than a confident coin flip.
        raw = 0.0 if spread <= 0 else min(spread, 1.0)
        return weights, self.confidence(raw)

    def _mean_return(self, env: str) -> float:
        cells = [c for (e, _, _), c in self.value.items() if e == env]
        taken = sum(c[0] for c in cells)
        return sum(c[1] for c in cells) / taken if taken else 0.0

    def observe(self, move: Move) -> None:
        super().observe(move)

    def n_parameters(self) -> int:
        return len(self.value)

    def render(self) -> str:
        by_env: dict[str, list[tuple]] = collections.defaultdict(list)
        for (env, ctx, action), (n, total) in self.value.items():
            by_env[env].append((total / n if n else 0.0, action, n))
        lines = [f"=== {self.name}: {len(self.value)} (context, action) cells, "
                 f"{self.rounds} rounds at epsilon {self.epsilon} ==="]
        for env, rows in sorted(by_env.items()):
            rows.sort(reverse=True)
            top = ", ".join(f"{a!r}={v:+.2f}(n={int(n)})" for v, a, n in rows[:3])
            lines.append(f"  {env:<10}{len(rows):>6} cells   best: {top}")
        return "\n".join(lines)
