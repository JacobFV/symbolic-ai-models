"""Ask before answering, but only when unsure — and only if that pays.

The lookup table of :mod:`symbolic_ai_agents.agents.context` with one thing
added: when it is not confident and the environment is offering information, it
buys some. That is the entire difference, deliberately, so the ``probe`` column
of a comparison table between the two says exactly what knowing-that-you-do-not-
know is worth here and nothing else is free to vary — the same discipline
:mod:`symbolic_ai_models.models.omegaclaw` imposes on its three subclasses.

The threshold is **fitted, not chosen**. A hand-picked "probe below 0.5" is an
assertion about a number this repo has repeatedly found to be worth measuring
instead; the model harness's whole calibration story is that confidence derived
from how much structure was found is not confidence in being right. So the
threshold is swept over a coarse grid on held-out *training* episodes and the
value with the best measured return is kept. One parameter, so a grid is honest
and a search would be false precision.

What this cannot do, and why it is still the interesting row: it has no model of
*which* probe is informative. It reveals the lowest-numbered hidden segment
first, because choosing between segments would need a model of what each one
says, and that model would be the contribution rather than this. An agent that
picked its probes well would beat this, and building it is the obvious next
step; the honest reading of a good score here is that asking at all was worth
more than asking cleverly.
"""

from __future__ import annotations

from typing import Sequence

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.tokenizer import SymbolTokenizer

from ...envs.base import Observation
from ...envs.rollout import rollouts
from ..base import Decision, held_out
from ..context.agent import ContextAgent
from ..registry import register

__all__ = ["CarefulAgent"]

#: Thresholds tried during fitting. Coarse on purpose: the quantity being chosen
#: is measured on a few dozen held-out episodes and finer steps would be fitting
#: the noise in that measurement.
GRID = (0.0, 0.2, 0.35, 0.5, 0.65, 0.8, 1.0)


@register("careful", doc="The lookup table, plus buying information when unsure.")
class CarefulAgent(ContextAgent):
    """Probe while unconfident and the budget allows; then commit."""

    LEARNED = ContextAgent.LEARNED + ("threshold", "max_probes")

    def __init__(self, extra=None) -> None:
        super().__init__(extra)
        #: Probe while the committing decision's confidence is below this.
        #: ``0.0`` never probes and reduces this agent to ``context`` exactly.
        self.threshold = float(self.get("threshold", 0.5))
        self.max_probes = int(self.get("max_probes", 4))
        self._probes = 0
        self._tuned = False

    # ---- fitting --------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        super().learn(episodes, tok)
        if self.get("threshold", None) is not None:
            self._tuned = True              # the caller pinned it; do not tune
            return
        self._tune(episodes, tok)

    def _tune(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Sweep the grid on training episodes; keep the best return.

        Only environments that actually offer probes are swept. On a lesson set
        whose prompts are single sentences there is nothing to buy, every
        threshold scores identically, and the tie is broken towards ``0.0`` —
        never probing — because paying for information that does not exist is
        the failure mode worth defaulting away from.

        **The known bias.** The sweep runs on the last fifth of the training
        episodes, which are held out from *evaluation* but not from the lookup
        table: :meth:`ContextAgent.learn` counted on all of them. The
        confidences seen while tuning are therefore in-sample and a little too
        high, which pushes the chosen threshold *down* and makes this agent
        probe less than it should. That is the safe direction and it is cheap to
        state; fixing it properly means fitting the table twice more, which
        would cost more than the bias does.
        """
        probing = [env for env in self._envs() if self._offers_probes(env, episodes, tok)]
        if not probing:
            self.threshold, self._tuned = 0.0, True
            return
        _, held = held_out(episodes)
        best, best_return = 0.0, float("-inf")
        for value in GRID:
            self.threshold = value
            total = 0.0
            for env in probing:
                metrics = env.summarize(rollouts(env, self, held, tok=tok).totals)
                total += float(metrics.get("return", 0.0))
            if total > best_return + 1e-9:
                best, best_return = value, total
        self.threshold, self._tuned = best, True

    @staticmethod
    def _offers_probes(env, episodes: Sequence[Episode],
                       tok: SymbolTokenizer) -> bool:
        for ep in list(episodes)[:8]:
            if env.reset(ep, tok=tok).probes:
                return True
        return False

    # ---- acting ---------------------------------------------------------
    def begin(self, env, obs: Observation) -> None:
        super().begin(env, obs)
        self._probes = 0

    def act(self, obs: Observation) -> Decision:
        committing = super().act(obs)
        if (not obs.probes or self._probes >= self.max_probes
                or committing.confidence >= self.threshold
                or obs.remaining <= 1):
            return committing
        self._probes += 1
        # The lowest-numbered hidden segment, always. See the module docstring:
        # choosing *which* to reveal would be a different contribution.
        return Decision(action=obs.probes[0],
                        confidence=committing.confidence,
                        why=f"unsure ({committing.confidence:.2f} < "
                            f"{self.threshold:.2f}) — asking")

    def render(self) -> str:
        return (f"{super().render()}\n  probe threshold: {self.threshold:.2f} "
                f"({'fitted' if self._tuned else 'pinned'}), "
                f"at most {self.max_probes} per episode")
