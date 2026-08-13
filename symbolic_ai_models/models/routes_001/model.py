"""Predict by structural route — and the per-episode refit that did not pay.

Every other reasoner here learns one thing from the training set and applies it
unchanged forever. That is the wrong shape for this curriculum, and it is why
label accuracy has sat near the floor throughout: the vocabulary is reinvented
every episode, so a rule of the form "in this context the answer is `o2`" is
worthless, and even a rule of the form "copy the peer" is only right in the
episodes that happen to be built that way.

So this model predicts with a **route** — "my slot-0 sibling", "the same slot of
another subtree with my parent's head" — chosen by a prior conditioned on
structural context and carrying no symbol at all. It is exactly equivariant
under renaming, which the test suite checks.

It was built to test a second idea, and that idea failed. The plan was to split
the *family* from the *member*: induce which routes exist across the training
set, then choose which route is in force **inside each episode**, from that
episode's own visible nodes. An episode is not just a question — in a scene
stating six objects, five are visible while the sixth is masked, and whichever
route explains those five ought to explain the sixth.

Measured, it contributes **nothing**. With ``extra.use_episode_fit`` on and off:

    use_episode_fit=True    acc 0.173   ECE 0.106
    use_episode_fit=False   acc 0.173   ECE 0.043

Identical accuracy and worse calibration, so it is off by default and the knob
remains only so the number can be reproduced. The likely reason is that the
context prior already conditions on ``(parent type, slot, arity)``, and within a
lesson the episodes are structurally homogeneous — so what an episode
demonstrates about its own routes, the prior already knew.

A first version of the per-episode score counted route *successes* without
counting failures, which made it uninformative for a different and stupider
reason; fixing that to a rate moved the contribution from +0.007 to +0.000. The
mechanism is genuinely neutral here, not merely mis-implemented.
"""

from __future__ import annotations

import collections
from typing import Sequence

from symbolic_ai_core.calibration import ScoreCalibrator
from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.graph import TYPE_TO_ID
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..routes import ROUTES, explaining_routes, follow
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["RouteModel"]


@register("routes-001", doc="Predict by structural route from a context-conditioned prior.")
class RouteModel(RuleBasedModel):
    """Follow the route the structural context expects. Symbol-free by design."""

    LEARNED = ("prior", "context_prior", "confidence_map", "min_evidence",
               "use_episode_fit")

    #: The one model that keeps the structural guarantee. Every other
    #: rule-based model now falls back on a memorised label when it abstains,
    #: which buys accuracy and costs renaming equivariance — a real trade, made
    #: knowingly, on a curriculum where every scored label recurs in training.
    #: This model opts out so the property is still demonstrated by something
    #: and the invariance test still has a subject.
    structural_fallback = False

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.min_evidence = int(cfg.get("min_evidence", 2))
        #: The ablation switch. With it off the model is the global route prior
        #: and nothing else, which is the comparison that says whether fitting
        #: per episode buys anything. Kept as a knob rather than a patch in a
        #: scratch script so the number can be reproduced.
        self.use_episode_fit = bool(cfg.get("use_episode_fit", False))
        #: how often each route explains a node anywhere — the family prior
        self.prior: collections.Counter = collections.Counter()
        #: the same, conditioned on structural context
        self.context_prior: dict[tuple, collections.Counter] = {}
        self.confidence_map = ScoreCalibrator()

    # ---- the family ----------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        self.prior, self.context_prior = self._fit_family(episodes, tok)
        self._calibrate(episodes, tok)

    def _fit_family(self, episodes: Sequence[Episode], tok: SymbolTokenizer):
        """Which routes ever explain anything, globally and per context."""
        prior: collections.Counter = collections.Counter()
        context: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                for route in explaining_routes(view.labels, view.parent,
                                               view.slot, node, label_id):
                    prior[route] += 1
                    context[_context(view, node)][route] += 1
        return prior, {k: v for k, v in context.items()}

    def _calibrate(self, episodes: Sequence[Episode],
                   tok: SymbolTokenizer) -> None:
        """Fit the confidence on episodes the family was not induced from."""
        cut = max(int(len(episodes) * 0.8), 1)
        if cut >= len(episodes):
            return
        prior, context = self._fit_family(episodes[:cut], tok)
        scores: list[float] = []
        correct: list[bool] = []
        for view, targets in self.training_views(episodes[cut:], tok,
                                                 max_nodes=self.cfg.max_nodes,
                                                 repeats=1, seed=23):
            endorsed = self._episode_fit(view)
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                votes, score = self._vote(view, node, endorsed, prior, context)
                if not votes:
                    continue
                scores.append(score)
                correct.append(max(votes, key=lambda k: votes[k]) == label_id)
        self.confidence_map = ScoreCalibrator().fit(scores, correct)

    # ---- the member ----------------------------------------------------
    def _episode_fit(self, view: GraphView) -> dict[tuple, float]:
        """Score every route against this episode's *visible* labelled nodes.

        This is the per-episode parameter. A node whose label is on the page is
        a worked example: whichever routes reach its own label from it are the
        routes this episode is built out of. Hidden nodes are never consulted,
        so nothing here can see the answer.

        The score is a **rate**, not a count, and the difference is the whole
        mechanism. Counting successes alone made a route that fires fifty times
        and lands five score exactly like one that fires five times and lands
        five — so the endorsement carried no information about reliability, and
        an ablation showed the per-episode half contributing +0.007 over the
        global prior. Failures have to count.
        """
        if not self.use_episode_fit:
            return {}
        hits: collections.Counter = collections.Counter()
        tries: collections.Counter = collections.Counter()
        for i, label in enumerate(view.labels):
            if label is None:
                continue
            for route in ROUTES:
                target = follow(view.labels, view.parent, view.slot, i, route)
                if target is None or target == i or view.labels[target] is None:
                    continue
                tries[route] += 1
                hits[route] += view.labels[target] == label
        # Smoothed towards zero, so a route demonstrated once is believed a
        # little and a route demonstrated twenty times is believed a lot.
        return {r: hits[r] / (tries[r] + 2.0) for r in tries}

    def _vote(self, view: GraphView, node: int, endorsed: dict[tuple, float],
              prior: collections.Counter,
              context: dict[tuple, collections.Counter]) -> tuple[dict, float]:
        """Follow the routes this episode endorses, backed by the global prior."""
        local = context.get(_context(view, node)) or prior
        if not local:
            return {}, 0.0
        total = sum(local.values()) or 1

        votes: collections.Counter = collections.Counter()
        best = 0.0
        for route in ROUTES:
            target = follow(view.labels, view.parent, view.slot, node, route)
            if target is None or view.labels[target] is None:
                continue
            # Two sources of belief, multiplied: how often this route works in
            # general, and how well it explains *this* episode. A route the
            # episode has never demonstrated is not ruled out, only quiet.
            globally = local.get(route, 0) / total
            here = endorsed.get(route, 0.0)
            # Two sources multiplied, with the episode's own evidence dominant:
            # the prior says which routes exist, the episode says which one is
            # in force. `+ 0.1` keeps a route the episode never demonstrated
            # quiet rather than silenced.
            weight = globally * (here + 0.1)
            if weight <= 0.0:
                continue
            votes[view.labels[target]] += weight
            best = max(best, here)
        return dict(votes), best

    def _vote_nodes(self, view: GraphView, node: int,
                    endorsed: dict[tuple, float]) -> tuple[dict, float]:
        """The same walk, accumulated on the *node* each route lands on.

        `_vote` computes `target` and then immediately reads `labels[target]`,
        so the binding was there and the label was a projection of it. Two
        routes that land on different nodes carrying the same symbol are one
        vote in `_vote` and two here, which is the honest shape: they are two
        pieces of evidence for the same answer, not one.
        """
        local = self.context_prior.get(_context(view, node)) or self.prior
        if not local:
            return {}, 0.0
        total = sum(local.values()) or 1
        votes: collections.Counter = collections.Counter()
        best = 0.0
        for route in ROUTES:
            target = follow(view.labels, view.parent, view.slot, node, route)
            if target is None or view.labels[target] is None:
                continue
            here = endorsed.get(route, 0.0)
            weight = (local.get(route, 0) / total) * (here + 0.1)
            if weight <= 0.0:
                continue
            votes[int(target)] += weight
            best = max(best, here)
        return dict(votes), best

    def source_votes(self, view: GraphView) -> dict[int, Votes]:
        endorsed = self._episode_fit(view)
        out: dict[int, Votes] = {}
        for i in view.hidden:
            votes, score = self._vote_nodes(view, i, endorsed)
            if not votes:
                continue
            confidence = (self.confidence_map(score)
                          if self.confidence_map.fitted
                          else min(0.15 + 0.7 * score, 0.9))
            out[i] = (votes, confidence)
        return out

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        endorsed = self._episode_fit(view)
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            votes, score = self._vote(view, i, endorsed, self.prior,
                                      self.context_prior)
            if not votes:
                out[i] = (ABSTAIN, self._type_vote(view, i))
                continue
            confidence = (self.confidence_map(score)
                          if self.confidence_map.fitted
                          else min(0.15 + 0.7 * score, 0.9))
            out[i] = ((votes, confidence), self._type_vote(view, i))
        return out

    @staticmethod
    def _type_vote(view: GraphView, i: int) -> Votes:
        peers = [view.types[j] for j in view.siblings(i) if view.types[j]]
        if not peers:
            return ABSTAIN
        counts = collections.Counter(TYPE_TO_ID[t] for t in peers)
        return dict(counts), min(len(peers) / (len(peers) + 2.0), 0.8)

    def n_symbolic_parameters(self) -> int:
        return len(self.prior) + sum(len(v) for v in self.context_prior.values())

    def render(self) -> str:
        lines = [f"=== route family ({len(self.prior)} routes) ==="]
        total = sum(self.prior.values()) or 1
        for route, count in self.prior.most_common(12):
            lines.append(f"  {str(route):<24}{count / total:>7.3f}")
        lines.append(f"=== {len(self.context_prior)} structural contexts ===")
        return "\n".join(lines)


def _context(view: GraphView, node: int) -> tuple:
    """The structural situation a route is conditioned on.

    Types and positions only — no labels — so the prior transfers to an episode
    whose vocabulary is entirely new, which is the whole point of separating the
    family from the member.
    """
    p = view.parent[node]
    return ((view.types[p] or "mask") if p >= 0 else "ROOT",
            min(view.slot[node], 6),
            min(len(view.children(node)), 4))
