"""``wrap``, calibrated where it acts. The third difference nobody had named.

``notes/findings/2026-08-14-the-action-readout-clears-the-repair-floor-on-179-lessons.md``
puts ``wrap`` and ``graphread`` side by side and says of the pair: *"same model,
same 179 lessons, same 716 episodes, same 2,632 fills, same floor, same shared
prior and calibrator. One thing differs: what the model's output is read as."*

The calibrator is not the same, and it is not a detail. Read the two ``_calibrate``
methods together:

* :meth:`~symbolic_ai_agents.agents.wrapped.agent.WrappedModel._calibrate` builds
  a **fresh** ``choice`` environment and fits its confidence map there — on a run
  configured with ``envs = ["repair"]``, that is an environment the run does not
  contain.
* :meth:`~symbolic_ai_agents.agents.graphread.agent.GraphReadAgent._calibrate`
  fits its map through **the environments the run was fitted with**, and says why
  in its own docstring: ``mask_rate`` and ``max_actions`` change how separable a
  decision is, so "a map fitted at one and applied at another is a map for a
  different question".

``graphread`` was therefore right about the hazard and ``wrap`` was left carrying
it. On ``repair`` the two action spaces are not comparable at all —
``choice`` offers the curriculum's multiple-choice answers, ``repair`` offers
node labels — and ``notes/findings/2026-08-13-abstention-on-repair-is-below-chance.md``
already measured what happens when a quantity fitted on the first is applied to
the second: the shared prior loses 0.06 to *uniform* that way. A confidence map
is the weight on the mixture between an agent's votes and that prior, so an
``choice``-fitted map on ``repair`` is a mis-set dial on the one term the row is
made of, and this repo's standing lesson is that a harness decision of that shape
moves 0.15 to 2.0 while models move 0.1.

So the ``wrap`` and ``graphread`` rows differ in **three** things — the readout,
the candidate cap, and where the calibrator was fitted — and the finding
attributes the gap to the first. This agent removes the third, exactly as
``graphread-capped`` removes the second. Registered beside ``wrap`` and not in
place of it: every published ``wrap`` number keeps meaning what it meant.

Run with ``extra.max_actions = 24`` it is ``graphread``'s equal in everything a
row can be equal in — same 24 candidates, same calibration environment, same
prior, same model, same episodes — and the only surviving difference is what the
output is read as. That is the comparison the finding claims to be reporting.
"""

from __future__ import annotations

from typing import Sequence

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.tokenizer import SymbolTokenizer

from ..base import held_out, training_views
from ..registry import register
from .agent import WrappedModel

__all__ = ["EnvCalibratedWrap"]


@register("wrap-envcal",
          doc="wrap, with its confidence map fitted in the run's own environments.")
class EnvCalibratedWrap(WrappedModel):
    """``wrap`` with ``graphread``'s calibration, and nothing else changed."""

    def fit(self, ctx) -> None:
        # Kept before `super().fit`, which is what calls `learn` and therefore
        # `_calibrate`. The same order `GraphReadAgent.fit` uses.
        self._learn_envs = list(ctx.envs.values())
        super().fit(ctx)

    def _calibrate(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """The same held-out fit, through the environments this run has.

        Deliberately *not* filtered to the graph-carrying ones the way
        ``graphread`` filters: ``wrap`` reads text and has an opinion everywhere,
        so restricting it would be inventing a handicap rather than removing an
        asymmetry. On a ``repair``-only run the two reduce to the same set, which
        is the run this agent was written for.

        Falls back to a fresh ``choice`` when the run supplied no environments at
        all, so an agent built outside a run still calibrates rather than acting
        on the unfitted guess in
        :meth:`~symbolic_ai_agents.agents.base.PolicyAgent.confidence`.
        """
        from ...envs import build as build_env
        _, held = held_out(episodes)
        envs = list(getattr(self, "_learn_envs", ()) or ()) or [build_env("choice")]
        scores: list[float] = []
        correct: list[bool] = []
        for env in envs:
            for obs, gold in training_views(env, held, tok):
                if gold is None or not obs.actions:
                    continue
                votes, raw = self._raw(obs)
                if not votes:
                    continue
                best = max(votes, key=lambda a: (votes[a], a))
                scores.append(raw)
                correct.append(best == gold)
        self.calibrate_on(scores, correct)

    def render(self) -> str:
        where = ", ".join(sorted(e.name for e in getattr(self, "_learn_envs", ())))
        base = super().render().split("\n")
        return "\n".join(base[:2] + [f"  calibrated in: {where or 'choice (fallback)'}"]
                         + base[2:])
