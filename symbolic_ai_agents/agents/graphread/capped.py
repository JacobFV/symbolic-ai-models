"""``graphread``, handicapped with ``wrap``'s shortlist. The control, not a better agent.

This agent exists to remove one confound and nothing else, and it is registered
beside :class:`~symbolic_ai_agents.agents.graphread.agent.GraphReadAgent` rather
than replacing it because the comparison *is* the measurement.

The confound, stated in the finding that needed it
(``notes/findings/2026-08-14-the-action-readout-clears-the-repair-floor-on-179-lessons.md``):

    ``wrap`` **scores at most 8 of** ``repair``'s **24 candidates**
    (``max_actions=8``), shortlisted by the shared prior. Where the answer falls
    outside that shortlist, ``wrap`` cannot pick it at any quality of reading.
    Some unknown part of the 0.423 is therefore truncation rather than readout.

``graphread`` has no such cap — one graph emission per decision costs the same
whatever the size of the action set — so the two rows differ in *two* things at
once and the gap between them is not attributable. This agent restores the cap
without restoring the text readout, which makes the three rows a proper ladder::

    wrap             text readout,  8 of 24 candidates
    graphread-capped graph readout, 8 of 24 candidates   <- this agent
    graphread        graph readout, 24 of 24 candidates

``graphread-capped`` minus ``wrap`` is the readout at a fixed candidate set;
``graphread`` minus ``graphread-capped`` is the cap at a fixed readout. Neither
number was available before, and the headline 0.423 is their sum.

How the handicap is applied, and why that way
---------------------------------------------
The shortlist comes from
:meth:`~symbolic_ai_agents.agents.base.PolicyAgent.shortlist` — literally the
method ``wrap`` calls, moved to the base class for this reason — so both agents
face the same eight strings in the same order, chosen by the shared prior and by
nothing either agent knows.

Votes landing outside it are **dropped**, and what survives is renormalised.
That is the same restriction ``wrap`` is under: its softmax puts all of its vote
mass on the shortlisted eight, and the other sixteen reach the mixture in
:meth:`~symbolic_ai_agents.agents.base.PolicyAgent.act` only through the prior.

One asymmetry is left in deliberately and has to be read with the number. If the
readout's *entire* mass falls outside the shortlist this agent abstains, and an
abstention on ``repair`` is measured to land below chance
(``notes/findings/2026-08-13-abstention-on-repair-is-below-chance.md``), whereas
``wrap`` in the same situation still ranks the eight it scored. So the handicap
here is a little **harsher** than ``wrap``'s, not a little softer — which is the
direction a control should err in, since it can only make the readout look
worse. :meth:`render` prints the rate so the size of it is visible rather than
assumed.

The alternative — falling back to the prior *within* the shortlist instead of
abstaining — was rejected for the reason ``graphread``'s own docstring gives
about text fallback: an agent that switches mechanism when its mechanism has
nothing to say is a measurement of neither mechanism.
"""

from __future__ import annotations

import torch

from ...envs.base import Observation
from ..registry import register
from .agent import GraphReadAgent

__all__ = ["CappedGraphReadAgent"]


@register("graphread-capped",
          doc="graphread, restricted to the same top-k shortlist wrap scores.")
class CappedGraphReadAgent(GraphReadAgent):
    """``graphread`` under ``wrap``'s ``max_actions`` cap. A control."""

    LEARNED = ("model", "model_name", "channel", "max_actions")

    def __init__(self, extra=None) -> None:
        super().__init__(extra)
        #: same default as ``wrap``'s, so an unconfigured run of the two is the
        #: paired comparison rather than something that needs a flag to become
        #: one. ``<= 0`` disables the cap and reproduces plain ``graphread``.
        self.max_actions = int(self.get("max_actions", 8))
        #: decisions where the cap removed every vote the readout had, which is
        #: the asymmetry against ``wrap`` named in the module docstring.
        self.truncated_out = 0

    @torch.no_grad()
    def _raw(self, obs: Observation) -> tuple[dict[str, float], float]:
        votes, raw = super()._raw(obs)
        if not votes:
            return votes, raw
        keep = set(self.shortlist(obs, obs.actions, self.max_actions))
        kept = {a: w for a, w in votes.items() if a in keep}
        if not kept:
            self.truncated_out += 1
            return {}, 0.0
        total = sum(kept.values()) or 1.0
        kept = {a: w / total for a, w in kept.items()}
        # The raw score is a statement about *separation among the candidates
        # that survived*, so it is rescaled by the mass that survived rather
        # than carried over. Reporting the uncapped separation of a capped
        # decision would hand the calibrator a confidence for a choice that was
        # never made. The calibrator is refitted through this method, so the map
        # this agent uses is measured under the cap it acts under.
        return kept, float(min(max(max(kept.values()) * raw / max(
            max(votes.values()), 1e-12), 0.0), 1.0))

    def explain(self, obs: Observation, action: str, votes, conf: float) -> str:
        if not votes:
            return (f"abstained (no {self.channel} votes inside the top-"
                    f"{self.max_actions}) -> prior")
        return f"{self.channel}: {len(votes)} of top-{self.max_actions} at {conf:.2f}"

    def render(self) -> str:
        base = super().render().split("\n")
        cap = (f"  capped at {self.max_actions} candidates, ranked by the shared "
               f"prior — the shortlist `wrap` scores")
        lost = (f"  {self.truncated_out:,} decisions lost every vote to the cap "
                f"and abstained")
        return "\n".join(base[:1] + [cap, lost] + base[1:])
