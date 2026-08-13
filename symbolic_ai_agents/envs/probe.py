"""The facts are hidden and asking for them costs something.

The one environment here where the feedback carries information the agent did
not already have, and therefore the only one that can separate *knowing the
answer* from *knowing that you do not know it yet*.

The prompt is split into segments and everything except the question itself is
redacted to ``[1]``, ``[2]``, .... The agent may spend a move on ``look 2``,
which reveals that segment and hands the turn back, or it may commit to an
answer at any point. Every probe costs ``cost``; the return is
``correct - probes * cost``, so an agent that reveals everything before
answering can still lose to one that answers straight away, and an agent that
answers blind can still lose to one that paid for the fact it needed.

There is no way to be teacher-forced through this. The optimal policy is a
function of the agent's own uncertainty, which no dataset of correct answers
contains, and that is the point: it is the smallest environment in this package
that a prediction harness cannot express at all.

Two honest limits, stated because they bound what a good score here means:

* **The redaction is syntactic.** Segments are lines, or sentences when the
  prompt is one line. A lesson whose prompt is a single short question has
  nothing to hide, no probes are offered, and the episode reduces to
  :mod:`symbolic_ai_agents.envs.choice`. ``blind`` reports what share of
  episodes came out that way, and a comparison drawn from a lesson set where it
  is high is a comparison of choice accuracy wearing a different name.
* **The cost is a free parameter.** At ``cost=0`` the dominant policy is to
  reveal everything, at ``cost>1/n_probes`` it is to never probe, and both ends
  make the environment uninteresting. The default of 0.1 was chosen so that
  revealing about three segments is worth roughly a third of a correct answer;
  it was not tuned against any agent's score, and it is recorded in the run's
  config so a table cannot silently mix two settings.
"""

from __future__ import annotations

import re

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.tokenizer import SymbolTokenizer

from .base import Environment, Observation, Step
from .registry import register

__all__ = ["Probe"]

#: Sentence-ish split, used when the prompt is a single line. Deliberately crude:
#: it only has to produce segments a reader would recognise as separate facts.
_SENTENCE = re.compile(r"(?<=[.;?!])\s+")


@register("probe", doc="Facts are redacted; pay to reveal them, then answer.")
class Probe(Environment):
    """Buy information, then commit. Return is correctness minus what you spent."""

    interactive = True

    def __init__(self, cost: float = 0.1, max_probes: int = 6,
                 horizon: int = 8) -> None:
        self.cost = float(cost)
        self.max_probes = int(max_probes)
        self.horizon = int(horizon)
        self._ep: Episode | None = None
        self._segments: list[str] = []
        self._question = ""
        self._revealed: set[int] = set()
        self._spent = 0
        self._done = True

    def _salt(self) -> str:
        return f"{self.cost}:{self.max_probes}:{self.horizon}"

    # ---- setting up -----------------------------------------------------
    def reset(self, ep: Episode, *, tok: SymbolTokenizer) -> Observation:
        self._ep = ep
        self._revealed = set()
        self._spent = 0
        self._done = False
        segments = [s.strip() for s in ep.prompt.splitlines() if s.strip()]
        if len(segments) < 3:
            segments = [s.strip() for s in _SENTENCE.split(ep.prompt) if s.strip()]
        # The question and everything after it stay visible. An agent that
        # cannot see what is being asked is not choosing whether to probe, it is
        # guessing, and the environment would be measuring the redaction rather
        # than the policy.
        #
        # Finding the question by position was the first attempt and it was
        # wrong: `langcurriculum` prompts end with the answer set and "Reply
        # with the answer only", so "the last segment" is boilerplate and the
        # actual question was among the things being hidden. It is found by
        # content instead — the last segment that asks something or states the
        # options — which survives the episode being rendered in another
        # language, since `?` and `|` are not translated.
        #
        # The *first* such segment, not the last. The options line also matches,
        # it comes after the question, and anchoring on it hid the question
        # again — the exact bug this rule was written to fix, reintroduced one
        # line further down.
        cut = len(segments)
        for i, s in enumerate(segments):
            if "?" in s or " | " in s:
                cut = i
                break
        self._question = "\n".join(segments[cut:]) if segments else ep.prompt
        self._segments = segments[:cut][-self.max_probes:]
        return self._observe()

    def _observe(self) -> Observation:
        ep = self._ep
        assert ep is not None
        lines = [f"[{i + 1}] {s}" if i in self._revealed
                 else f"[{i + 1}] (hidden)"
                 for i, s in enumerate(self._segments)]
        hidden = [i for i in range(len(self._segments)) if i not in self._revealed]
        left = self.horizon - len(self._revealed)
        return Observation(
            text="\n".join(lines + ["", self._question]),
            actions=tuple(ep.choices),
            probes=tuple(f"look {i + 1}" for i in hidden),
            step=len(self._revealed), remaining=left,
            key=f"{ep.instance_id}:answer",
            info={"lesson_id": ep.lesson_id, "instance_id": ep.instance_id,
                  "n_choices": len(ep.choices), "hidden": len(hidden),
                  "cost": self.cost})

    # ---- acting ---------------------------------------------------------
    def oracle(self) -> str | None:
        return None if self._ep is None or self._done else self._ep.answer

    def step(self, action: str) -> Step:
        if self._ep is None or self._done:                # pragma: no cover
            raise RuntimeError("probe: step() before reset(), or after done")

        index = self._probe_index(action)
        if index is not None:
            self._revealed.add(index)
            self._spent += 1
            return Step(reward=-self.cost, done=False, correct=None,
                        feedback=f"revealed: {self._segments[index]}",
                        next_obs=self._observe(),
                        info={"probes_paid": 1.0})

        self._done = True
        correct = action.strip() == self._ep.answer.strip()
        return Step(
            reward=1.0 if correct else 0.0, done=True, correct=correct,
            feedback="right" if correct else f"no — it was {self._ep.answer}",
            info={"blind": float(not self._segments),
                  "revealed": float(len(self._revealed)),
                  "hideable": float(len(self._segments)),
                  "episodes_scored": 1.0})

    def _probe_index(self, action: str) -> int | None:
        if not action.startswith("look "):
            return None
        try:
            i = int(action.split()[1]) - 1
        except (IndexError, ValueError):                  # pragma: no cover
            return None
        return i if 0 <= i < len(self._segments) and i not in self._revealed else None

    # ---- reporting -------------------------------------------------------
    def summarize(self, totals) -> dict[str, float]:
        """Adds what was spent and how often there was nothing to buy."""
        from .base import summarize as base_summarize
        out = base_summarize(totals)
        # `episodes`, not `episodes_scored`: an agent that probed until the
        # horizon ran out never committed and so never wrote the second counter.
        # Dividing by the episodes that reached an answer would quietly exclude
        # exactly the failure this environment is capable of producing.
        n = totals.get("episodes", 0.0)
        out["revealed"] = totals.get("revealed", 0.0) / n if n else float("nan")
        out["blind"] = totals.get("blind", 0.0) / n if n else float("nan")
        out["answered"] = (totals.get("episodes_scored", 0.0) / n
                           if n else float("nan"))
        hideable = totals.get("hideable", 0.0)
        out["seen"] = (totals.get("revealed", 0.0) / hideable
                       if hideable else float("nan"))
        return out
