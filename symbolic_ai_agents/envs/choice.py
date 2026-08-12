"""One question, one commitment — the curriculum's own question, as an environment.

This is the bridge between the two packages. It is exactly what
:func:`symbolic_ai_models.agent.evaluate_choices` scores a trained model on:
the prompt, the stated answer set, one pick. There is nothing to learn within an
episode and nothing to recover from, so ``interactive`` is ``False`` and an
agent's return here is its top-1 accuracy and nothing more.

It earns its place for two reasons. It is the **control** for the other three
environments: any claim that ``retry`` or ``probe`` measures something new has
to survive the comparison against this, where interaction is unavailable by
construction. And it is the one environment where an agent and a *model* are
answering literally the same question, so
:mod:`symbolic_ai_agents.agents.wrapped` scoring differently here from the model
it wraps means the wrapper is broken rather than the agent being interesting.
"""

from __future__ import annotations

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.tokenizer import SymbolTokenizer

from .base import Environment, Observation, Step
from .registry import register

__all__ = ["Choice"]


@register("choice", doc="Answer the curriculum's multiple-choice question in one move.")
class Choice(Environment):
    """The episode's own question, asked once."""

    horizon = 1
    interactive = False

    def __init__(self) -> None:
        self._ep: Episode | None = None
        self._done = True

    def reset(self, ep: Episode, *, tok: SymbolTokenizer) -> Observation:
        self._ep = ep
        self._done = False
        return Observation(
            text=ep.prompt, actions=tuple(ep.choices), step=0, remaining=1,
            key=f"{ep.instance_id}:answer",
            info={"lesson_id": ep.lesson_id, "instance_id": ep.instance_id,
                  "n_choices": len(ep.choices)})

    def oracle(self) -> str | None:
        return None if self._ep is None or self._done else self._ep.answer

    def step(self, action: str) -> Step:
        if self._ep is None or self._done:                # pragma: no cover
            raise RuntimeError("choice: step() before reset(), or after done")
        self._done = True
        correct = action.strip() == self._ep.answer.strip()
        return Step(reward=1.0 if correct else 0.0, done=True, correct=correct,
                    feedback="right" if correct else f"no — it was {self._ep.answer}")
