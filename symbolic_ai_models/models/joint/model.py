"""Fill the surest node first, then read the graph again.

Every model here predicts each masked node from the same frozen view, and the
collator masks 15% of the nodes at once. So a claw reaching for a coreferent
node lands on ``None`` a substantial share of the time — not because the
evidence is absent but because the harness happened to hide the evidence and the
question in the same pass. ``claw_peer`` returns nothing whenever its target is
one of the other masked nodes; ``ilp``'s clauses drop out on exactly the same
condition, with an explicit ``if label is None: continue``.

That is a decoding order, not a property of the models, and it is the only place
in this repo where the two halves are inconsistent with each other: the agent
side's ``repair`` environment already fills a term graph one node at a time and
lets the model see what it wrote. The prediction side never has.

So: run the reasoner, commit the answers it is surest of, put them into the view
as ordinary visible labels, and ask again. Each node's *reported* distribution
is the one it had when it was first decided, so nothing is scored against a
value the model wrote itself — a committed node is evidence for its neighbours
and never for itself.

**This is legitimate and it is worth saying exactly why.** The committed labels
are the model's own predictions, not the answers; the harness's hidden values
are never read; and a wrong commitment propagates, which is a cost the model
pays rather than a leak it exploits. That last part is the interesting half. The
teacher-forced score every other model gets says what happens when errors do not
compound, and the repo has recorded that as a scope boundary for as long as it
has existed. This closes it on the prediction side.

**Committed in rounds rather than one at a time.** One node per round is
``O(k^2)`` reasoner calls for ``k`` masked nodes and would put ``corefer`` an
hour behind its own baseline for what is a decoding question. Four rounds, each
committing a fixed share of what is left, is ``O(4k)`` and keeps the
highest-confidence nodes first, which is where nearly all of the benefit is: the
sure answers are the ones worth conditioning on.

**What would refute it.** If iterative decoding buys nothing, the reachable
signal was never blocked by the masking — the claws that came back empty would
have been wrong anyway — and "15% of the evidence is hidden" is a story about
the harness rather than a constraint on the score. That is a real possibility
and the null is worth as much as the win, because it decides whether the
teacher-forcing boundary is costing anything measurable.

Registered over two different reasoners on purpose. ``omegaclaw_ctx`` reaches
for named structural relations and should gain most if the mechanism works at
all; ``ptrgen`` scores every visible node and merely gains candidates. If only
one of them moves, the effect is about *reach* rather than about decoding.
"""

from __future__ import annotations

from typing import Sequence

from ..omegaclaw_ctx_001 import OmegaClawContext
from ..ptrgen_001.model import PointerGeneratorModel
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, Votes

__all__ = ["JointDecoding", "OmegaClawJoint", "PointerGeneratorJoint"]


def _certainty(vote: Votes | None) -> float:
    """How sure a vote is: its confidence times its winner's share.

    Both halves are needed. Confidence alone ranks a model that is sure it is
    one of six above one that is moderately sure of a single symbol, and the
    share alone ignores that the first model may have no business speaking. The
    product is what "surest" has to mean for a commitment.
    """
    if not vote:
        return 0.0
    table, confidence = vote
    total = float(sum(table.values()))
    if total <= 0.0 or confidence <= 0.0:
        return 0.0
    return float(confidence) * (max(table.values()) / total)


class JointDecoding:
    """Mixin: decode the masked nodes in confidence order, not all at once.

    Mixed into a reasoner ahead of :class:`RuleBasedModel` so that
    ``super().node_votes`` is the underlying model's, called once per round on a
    progressively more visible graph. The reasoner is not modified and does not
    know this is happening, which is what keeps the contrast one variable.
    """

    #: Passes over the masked set. Each commits ``1 / (rounds - r)`` of what
    #: remains, so the schedule finishes exactly at the last round.
    joint_rounds = 4

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        hidden = list(view.hidden)
        if len(hidden) < 2:
            return super().node_votes(view)

        # The view belongs to the caller; every mutation below is undone.
        saved_labels = list(view.labels)
        saved_types = list(view.types)
        decided: dict[int, tuple[Votes, Votes]] = {}
        remaining = set(hidden)
        try:
            for round_index in range(self.joint_rounds):
                view.hidden = sorted(remaining)
                votes = super().node_votes(view)
                left = self.joint_rounds - round_index
                if left <= 1:
                    for node in remaining:
                        decided[node] = votes.get(node, (ABSTAIN, ABSTAIN))
                    break
                # A node is recorded in the round it is *committed*, not the
                # first round it is seen in. Recording every node on the first
                # pass was the initial version and it made the whole mixin a
                # no-op with the machinery visibly running: every distribution
                # was already fixed before a single commitment existed, and the
                # scores came out bit-identical to the base model. The nodes
                # that gain are the ones decided late, so they are exactly the
                # ones whose answer must not be frozen early.
                take = max(1, len(remaining) // left)
                ranked = sorted(
                    remaining,
                    key=lambda n: (-_certainty(votes[n][0] if n in votes else None), n))
                for node in ranked[:take]:
                    pair = votes.get(node, (ABSTAIN, ABSTAIN))
                    decided[node] = pair
                    remaining.discard(node)
                    self._commit(view, node, pair)
                if not remaining:
                    break
        finally:
            view.labels = saved_labels
            view.types = saved_types
            view.hidden = hidden
        return decided

    @staticmethod
    def _commit(view: GraphView, node: int,
                pair: tuple[Votes, Votes] | None) -> None:
        """Write this node's own answer into the graph, for its neighbours.

        A node with nothing to say stays masked rather than being filled with a
        guess from the back-off: the point is to supply evidence, and an
        invented label is worse than a missing one for every claw that keys on
        matching symbols.
        """
        if pair is None:
            return
        label_votes, type_votes = pair
        table, confidence = label_votes if label_votes else ({}, 0.0)
        if table and confidence > 0.0:
            view.labels[node] = int(max(table, key=lambda s: (table[s], -s)))
        types, type_confidence = type_votes if type_votes else ({}, 0.0)
        if types and type_confidence > 0.0:
            from symbolic_ai_core.data.graph import NODE_TYPES
            best = int(max(types, key=lambda t: (types[t], -t)))
            if 0 <= best < len(NODE_TYPES):
                view.types[node] = NODE_TYPES[best]


@register("omegaclaw_joint-001",
          doc="omegaclaw_ctx, decoded in confidence order instead of all at once.")
class OmegaClawJoint(JointDecoding, OmegaClawContext):
    """``omegaclaw_ctx-001`` and a decoding order. Nothing else differs."""


@register("ptrgen_joint-001",
          doc="ptrgen, decoded in confidence order instead of all at once.")
class PointerGeneratorJoint(JointDecoding, PointerGeneratorModel):
    """``ptrgen-001`` and a decoding order. Nothing else differs."""
