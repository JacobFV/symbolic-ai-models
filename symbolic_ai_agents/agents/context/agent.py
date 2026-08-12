"""What usually goes here — the model harness's floor, moved into a trajectory.

:meth:`symbolic_ai_models.tasks.masked_node.MaskedNode.floor` is a lookup table:
the commonest answer for each structural context, backing off to the global
majority. It is the floor the entire model harness measures lift against, on the
argument that node type is very nearly determined by the shape of the tree and a
model scoring 0.95 against a majority-class floor of 0.33 has learned *less than
the table*.

This is that table, as an agent. It keys on
:meth:`symbolic_ai_agents.envs.base.Environment.context_key`, which
:mod:`symbolic_ai_agents.envs.repair` overrides with exactly the tuple the
masked-node floor uses — ``(parent type, slot, depth, has children)`` — so the
two are the same table asked the same question, one under teacher forcing and
one not. The difference between them is the size of the teacher-forcing
subsidy, measured rather than argued about.

It is registered as a competitor as well as being one of the
:data:`~symbolic_ai_agents.envs.base.FLOOR_POLICIES`, which has a consequence
worth stating: wherever this agent is the strongest of the three floors, its own
lift is zero by construction. That is not a defect in the table. It is the table
saying "this row *is* the baseline", the same way ``ngram`` is both a registered
model and the counting baseline every other rule-based model has to beat.

There is nothing in this agent that could be mistaken for understanding. It has
the shape of the situation and no idea what any symbol in it means.
"""

from __future__ import annotations

import collections
from typing import Sequence

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.tokenizer import SymbolTokenizer

from ...envs.base import Environment, Observation
from ..base import ABSTAIN, Preference, PolicyAgent, held_out, training_views
from ..registry import register

__all__ = ["ContextAgent"]


@register("context", doc="Commonest answer per structural context; a lookup table.")
class ContextAgent(PolicyAgent):
    """Count what filled this kind of slot in training; offer it again."""

    LEARNED = ("table", "overall", "confidence_map")

    def __init__(self, extra=None) -> None:
        super().__init__(extra)
        #: ``(environment, context) -> Counter(action)``
        self.table: dict[tuple, collections.Counter] = {}
        #: ``environment -> Counter(action)``, the back-off within this agent
        self.overall: dict[str, collections.Counter] = {}
        self.min_count = int(self.get("min_count", 2))

    # ---- fitting --------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Count on four fifths, price the counts on the other fifth, ship both.

        Fitted twice on purpose, and the reason is the one
        :meth:`symbolic_ai_models.models.omegaclaw.base.OmegaClaw.learn` gives:
        a confidence measured against the episodes the counts came from
        certifies the agent's overconfidence instead of removing it. The table
        that ships is fitted on everything and the map that prices it was
        measured on data the map's table had not seen, which biases confidence
        *down* — the safe direction.
        """
        fitting, held = held_out(episodes)
        table, overall = self._count(fitting, tok)
        self._fit_confidence(held, tok, table, overall)
        self.table, self.overall = self._count(episodes, tok)

    def _count(self, episodes: Sequence[Episode], tok: SymbolTokenizer
               ) -> tuple[dict[tuple, collections.Counter],
                          dict[str, collections.Counter]]:
        table: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        overall: dict[str, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for env in self._envs():
            for obs, gold in training_views(env, episodes, tok):
                if gold is None:
                    continue
                table[(env.name, env.context_key(obs))][gold] += 1
                overall[env.name][gold] += 1
        return dict(table), dict(overall)

    def _fit_confidence(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
                        table: dict, overall: dict) -> None:
        """What this agent's agreement score was actually worth, out of sample."""
        held_table, held_overall = self.table, self.overall
        self.table, self.overall = table, overall
        scores: list[float] = []
        correct: list[bool] = []
        try:
            for env in self._envs():
                for obs, gold in training_views(env, episodes, tok):
                    if gold is None:
                        continue
                    self.env = env
                    votes, raw = self._raw(obs)
                    if not votes:
                        continue
                    best = max(votes, key=lambda a: (votes[a], a))
                    scores.append(raw)
                    correct.append(best == gold)
        finally:
            self.table, self.overall = held_table, held_overall
            self.env = None
        self.calibrate_on(scores, correct)

    def _envs(self) -> list[Environment]:
        """Every environment this agent was given, or a default set.

        An agent fitted with no environments named would have an empty table and
        abstain everywhere, which reads in a comparison table exactly like a
        broken agent. Falling back on the registry means "fitted on nothing" is
        impossible rather than silent.
        """
        from ...envs import REGISTRY, build
        envs = list(getattr(self, "_learn_envs", ()) or ())
        return envs or [build(n) for n in sorted(REGISTRY)]

    def fit(self, ctx) -> None:
        self._learn_envs = list(ctx.envs.values())
        super().fit(ctx)

    # ---- acting ---------------------------------------------------------
    def _raw(self, obs: Observation) -> tuple[dict[str, float], float]:
        env = self.env
        if env is None:
            return {}, 0.0
        legal = set(obs.actions)
        counts = self.table.get((env.name, env.context_key(obs)))
        if not counts or sum(counts.values()) < self.min_count:
            counts = self.overall.get(env.name)
        if not counts:
            return {}, 0.0
        votes = {a: float(c) for a, c in counts.items() if a in legal}
        if not votes:
            return {}, 0.0
        total = sum(votes.values())
        return votes, max(votes.values()) / total

    def prefer(self, obs: Observation) -> Preference:
        votes, raw = self._raw(obs)
        if not votes:
            return ABSTAIN
        return votes, self.confidence(raw)

    def n_parameters(self) -> int:
        return len(self.table) + sum(len(c) for c in self.overall.values())

    def render(self) -> str:
        lines = [f"=== {self.name}: {len(self.table)} context cells ==="]
        for env, counts in sorted(self.overall.items()):
            top = ", ".join(f"{a!r}x{n}" for a, n in counts.most_common(4))
            lines.append(f"  {env:<10}{len(counts):>6} answers seen   {top}")
        lines.append(f"  confidence map: "
                     f"{'fitted' if self.confidence_map.fitted else 'unfitted'}")
        return "\n".join(lines)
