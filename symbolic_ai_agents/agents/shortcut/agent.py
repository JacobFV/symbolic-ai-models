"""The best cheat, ranked — a floor that has looked at the page but not read it.

:mod:`symbolic_ai_models.shortcuts` makes the case that a uniform floor is the
right question asked weakly: the stronger question is what a rule gets that
knows nothing about the problem while still looking at it. Pick the longest
option. Pick the one sharing most words with the question. Pick the one written
unlike the others. On a generated curriculum these work far more often than they
should, and an agent scoring above chance but below them has understood nothing.

This agent is that argument as a policy. It ranks the legal actions by **how
many of the nine shortcuts pick each one**, weighted by how often each shortcut
was right on held-out training episodes. Ranking rather than picking is what
makes it a usable floor for :mod:`symbolic_ai_agents.envs.retry`, where the
whole ordering is scored and a single pick would leave everything after the
first try to the prior.

The shortcuts are parameter-free by construction, so there is nothing here that
can overfit; the only fitting is measuring which of them work, and that is done
on training episodes with the measurement taken on a held-out fifth of them.

It is also a **generator audit**. A lesson where this agent scores highly has
leaked — the distractors are built by a different recipe than the answer, or the
answer sits in the prompt — and that is a fact about the lesson, not about any
agent that beats it. ``symbolic-ai-agents shortcuts`` prints the breakdown.
"""

from __future__ import annotations

from symbolic_ai_models.data.tokenizer import SymbolTokenizer
from symbolic_ai_models.shortcuts import SHORTCUTS

from ...envs.base import Observation
from ..base import ABSTAIN, Preference, PolicyAgent, held_out
from ..registry import register

__all__ = ["ShortcutAgent"]


@register("shortcut", doc="Rank the options by the parameter-free cheats that work.")
class ShortcutAgent(PolicyAgent):
    """Every shortcut votes, weighted by what it was worth out of sample."""

    LEARNED = ("weights",)

    def __init__(self, extra=None) -> None:
        super().__init__(extra)
        #: shortcut name -> its accuracy on held-out training episodes
        self.weights: dict[str, float] = {}

    def learn(self, episodes, tok: SymbolTokenizer) -> None:
        usable = [e for e in episodes if e.choices]
        if not usable:
            self.weights = {}
            return
        _, held = held_out(usable)
        self.weights = {}
        for shortcut in SHORTCUTS:
            hits = sum(shortcut.pick(e.prompt, list(e.choices)).strip()
                       == e.answer.strip() for e in held)
            # Weighted by accuracy above chance, floored at zero: a cheat that
            # does worse than guessing is not evidence for its pick, and letting
            # it vote negatively would make this agent an anti-cheat detector
            # rather than a floor.
            chance = sum(1.0 / max(len(e.choices), 1) for e in held) / len(held)
            self.weights[shortcut.name] = max(hits / len(held) - chance, 0.0)

    def prefer(self, obs: Observation) -> Preference:
        if not obs.actions or not self.weights:
            return ABSTAIN
        options = list(obs.actions)
        votes: dict[str, float] = {}
        for shortcut in SHORTCUTS:
            weight = self.weights.get(shortcut.name, 0.0)
            if weight <= 0.0:
                continue
            try:
                picked = shortcut.pick(obs.text, options)
            except (ValueError, IndexError):              # pragma: no cover
                continue
            votes[picked] = votes.get(picked, 0.0) + weight
        if not votes:
            return ABSTAIN
        # The raw score is the winner's share of the vote — a statement about
        # *agreement between cheats*, which is measurable, rather than about
        # correctness, which is what the calibrator is for.
        total = sum(votes.values())
        return votes, self.confidence(max(votes.values()) / total)

    def n_parameters(self) -> int:
        return sum(1 for w in self.weights.values() if w > 0.0)

    def render(self) -> str:
        rows = sorted(self.weights.items(), key=lambda kv: -kv[1])
        lines = [f"=== {self.name}: {self.n_parameters()} cheats above chance ==="]
        lines += [f"  {name:<14}{weight:+.3f} above chance" for name, weight in rows]
        return "\n".join(lines)
