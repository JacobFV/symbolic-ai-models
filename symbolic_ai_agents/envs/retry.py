"""The same question, but wrong answers come back — so the whole ranking is scored.

:mod:`symbolic_ai_agents.envs.choice` scores an agent's ``argmax`` and throws
away everything else it believed. That is a real loss of information: two agents
with the same top-1 accuracy can be very different, one holding the answer
second whenever it is wrong and the other holding it last. Under teacher forcing
there is nowhere to put that difference, which is why the model harness never
measures it.

Here the environment says "no" and asks again, up to ``tries`` times, and the
payout is ``1 / tries_used``. The return is then the reciprocal rank of the true
answer, truncated at the horizon — a standard, well-understood quantity, and one
that cannot be improved by anything except ordering the options better.

**What this does and does not measure.** The base agent forgets nothing: a
refused action is excluded from the next choice by
:class:`~symbolic_ai_agents.agents.base.Agent`, for every agent, so this is not
a test of whether someone remembered to write that down. It is the shared
machinery that localises the difference, in exactly the way one shared output
head localises the difference between two architectures in the model harness.
The consequence worth stating plainly is that ``retry`` is **not** a test of
learning from feedback — the feedback carries no information the agent did not
already have, since it only rules out a choice the agent itself just made.
:mod:`symbolic_ai_agents.envs.probe` is the environment where feedback is
genuinely informative.
"""

from __future__ import annotations

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.tokenizer import SymbolTokenizer

from .base import Environment, Observation, Step
from .registry import register

__all__ = ["Retry"]


@register("retry", doc="Answer until right or out of tries; paid 1/tries_used.")
class Retry(Environment):
    """Reciprocal rank of the true answer, measured by asking."""

    interactive = True

    def __init__(self, tries: int = 3) -> None:
        self.tries = max(int(tries), 1)
        self.horizon = self.tries
        self._ep: Episode | None = None
        self._used = 0
        self._done = True

    def reset(self, ep: Episode, *, tok: SymbolTokenizer) -> Observation:
        self._ep = ep
        self._used = 0
        self._done = False
        return self._observe()

    def _observe(self) -> Observation:
        ep = self._ep
        assert ep is not None
        left = self.tries - self._used
        return Observation(
            text=ep.prompt, actions=tuple(ep.choices), step=self._used,
            remaining=left,
            # The key does not change between tries: it is the same question,
            # so the agent is expected to remember what it has already been
            # refused. It changes on the next episode.
            key=f"{ep.instance_id}:answer",
            info={"lesson_id": ep.lesson_id, "instance_id": ep.instance_id,
                  "n_choices": len(ep.choices), "tries_left": left})

    def oracle(self) -> str | None:
        return None if self._ep is None or self._done else self._ep.answer

    def step(self, action: str) -> Step:
        if self._ep is None or self._done:                # pragma: no cover
            raise RuntimeError("retry: step() before reset(), or after done")
        self._used += 1
        correct = action.strip() == self._ep.answer.strip()
        if correct:
            self._done = True
            return Step(reward=1.0 / self._used, done=True, correct=True,
                        feedback=f"right, on try {self._used}")
        if self._used >= self.tries:
            self._done = True
            return Step(reward=0.0, done=True, correct=False,
                        feedback=f"no — it was {self._ep.answer}")
        return Step(reward=0.0, done=False, correct=False,
                    feedback=f"no, not {action!r} — try again",
                    next_obs=self._observe())

    def _salt(self) -> str:
        return str(self.tries)
