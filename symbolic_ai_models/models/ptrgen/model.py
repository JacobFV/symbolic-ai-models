"""Copy or generate, as one distribution rather than two heads.

Every pointer in this repo is scored twice and modelled once. ``corefer`` picks
a node, and that pick is reported as ``copy_acc``; the *label* it implies is
then poured into the same ``(1 - c) * backoff + c * votes`` mixture every other
model uses, with ``c`` fitted as an argmax accuracy. The pointer and the symbol
head are the same decision wearing two costumes, and neither costume fits.

This model states the decision once::

    p(label = v) = g * sum_{j : label(j) = v} p(j)  +  (1 - g) * p_generate(v)

``g`` is the probability that the answer is a copy of something visible in this
episode at all, ``p(j)`` is a proper distribution over the candidate nodes, and
``p_generate`` is the shared back-off. That is the pointer-generator of See,
Liu & Manning 2017 and the mention-ranking coreference model of Lee et al. 2017,
which is what this task has been all along: 71.9% of scored answers already sit
on a visible node, so "which node do I corefer with" is the question and "which
of 8,192 symbols" is a re-encoding of it that loses the 17.5% of answers the
vocabulary cannot name.

Two things follow, and they are the reason to build it rather than tune
``corefer``.

**The gate is the mixture weight.** ``g`` is not a confidence bolted on after
the fact; it is the thing the harness's mixture was always asking for, and
:class:`~symbolic_ai_models.calibration.MassCalibrator` fits it by maximising
held-out likelihood instead of inferring it from how often the top vote won.
The copy branch is a real distribution over labels, so spreading belief across
three plausible antecedents costs nothing, where the old contract made it
indistinguishable from being unsure.

**The pointer is trained on every correct antecedent at once.** A label usually
appears on several visible nodes -- the median question here has more than one
correct source -- and there is no fact of the matter about which one the
generator "meant". ``corefer`` handles that by asking a separate yes/no question
of each pair, which is what naive Bayes needs and is not what the task is. Here
the candidates are normalised against each other and the objective is the
*marginal* likelihood of landing anywhere correct::

    L = sum_i log sum_{j in gold(i)} softmax_j score(i, j)

The gradient of that is the difference between two expectations, so each correct
candidate is credited in proportion to how much the model currently believes it
-- soft responsibilities, not a designated winner. This is the same move as
``omegaclaw_em``'s and is here for the same reason: several answers can be true,
and a training signal that insists on one of them is fitting a question nobody
asked.

**Why this is not the perceptron that already failed.** `ROADMAP.md` records an
averaged perceptron over these features scoring 0.356 cold and 0.368 warm
against naive Bayes' 0.404, and concludes discriminative training did not rescue
correlated features. That result stands and this is a different object: a
perceptron makes a hard update towards one designated answer and has no
normalisation, so with several valid antecedents it is trained to prefer an
arbitrary one of them and to push the others down. The objective here is convex,
normalised over the candidate set, and indifferent to which correct node wins.
If it also fails, the honest conclusion is that the features are exhausted
rather than that the combiner was.

**The features are ``corefer``'s, deliberately.** Imported rather than
re-derived, so that the contrast between the two models is the training
objective and the gate, and cannot be a difference in what they were allowed to
look at. ``corefer-001`` is frozen by the versioning rule, so the import is
stable.

Registered variants, one axis each::

    ptrgen-001      marginal-likelihood pointer, mass-calibrated gate
    ptrgen-argmax   the same pointer, gate fitted as an argmax accuracy
"""

from __future__ import annotations

import collections
import math
from typing import Sequence

import numpy as np

from ...calibration import MassCalibrator, ScoreCalibrator
from ...data.curriculum import Episode
from ...data.graph import TYPE_TO_ID
from ...data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..corefer.model import _pair_features, _type_keys
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["PointerGeneratorModel", "PointerGeneratorArgmax"]


class PointerGeneratorModel(RuleBasedModel):
    """A gated mixture of a node pointer and the shared back-off."""

    LEARNED = ("weights", "gate_map", "type_rules", "n_questions")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.max_questions = int(cfg.get("max_questions", 6000))
        self.epochs = int(cfg.get("epochs", 6))
        self.lr = float(cfg.get("lr", 0.5))
        self.l2 = float(cfg.get("l2", 1e-6))
        #: Candidates scored per question. Every visible node is a legal
        #: antecedent, but the gradient needs the whole normalised set each
        #: pass, and the tail of a hundred-node graph contributes almost no
        #: probability. Truncation is by structural distance, which is
        #: content-blind and so cannot smuggle the answer in.
        self.max_candidates = int(cfg.get("max_candidates", 48))
        self.weights: dict[tuple, float] = {}
        self.gate_map = MassCalibrator()
        self.type_rules: dict[tuple, collections.Counter] = {}
        self.min_support = int(cfg.get("min_support", 5))
        self.n_questions = 0

    # ---- fitting ------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        cut = max(int(len(episodes) * 0.8), 1)
        questions = self._questions(episodes[:cut], tok)
        self._fit_pointer(questions)
        # The gate is fitted on episodes the pointer was not fitted from. A
        # pointer scored on its own training questions looks sharper than it is,
        # and the gate would then hand that sharpness the mass to act on.
        self._fit_gate(episodes[cut:] or episodes, tok)
        self._fit_types(episodes, tok)
        self.n_questions = len(questions)

    def _candidates(self, view: GraphView, node: int) -> list[int]:
        """Visible labelled nodes, nearest first, capped.

        Ordered by distance in the linearisation, which is a fact about shape.
        Ordering by score would make the candidate set depend on the parameters
        being fitted, so a question would change shape between epochs.
        """
        pool = [j for j in range(len(view))
                if j != node and view.labels[j] is not None]
        if len(pool) <= self.max_candidates:
            return pool
        pool.sort(key=lambda j: (abs(j - node), j))
        return sorted(pool[:self.max_candidates])

    def _questions(self, episodes: Sequence[Episode], tok: SymbolTokenizer
                   ) -> list[tuple[list[list[tuple]], np.ndarray]]:
        """``(features per candidate, which candidates are correct)``.

        A question with no correct candidate is dropped: its marginal
        likelihood is zero however the weights are set, so it contributes an
        infinite loss and no gradient direction. Those positions are exactly
        what the gate is for, and they are counted there instead.
        """
        out: list[tuple[list[list[tuple]], np.ndarray]] = []
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (label_id, _) in targets.items():
                if label_id < 0 or label_id == tok.unk_id:
                    continue
                cands = self._candidates(view, node)
                if not cands:
                    continue
                gold = np.array([view.labels[j] == label_id for j in cands])
                if not gold.any():
                    continue
                out.append(([_pair_features(view, node, j) for j in cands], gold))
                if len(out) >= self.max_questions:
                    return out
        return out

    def _fit_pointer(self, questions: Sequence[tuple]) -> None:
        """Maximise the marginal likelihood of landing on *any* correct node.

        AdaGrad, because the features are categorical and wildly unequal in
        frequency: ``rel=sibling`` fires on most questions and a particular
        ``(query, dist)`` conjunction on a handful, and one global step size
        either crawls for the first or diverges on the second. A per-feature
        rate is the standard answer and needs no schedule.
        """
        if not questions:
            return
        weights: dict[tuple, float] = collections.defaultdict(float)
        accum: dict[tuple, float] = collections.defaultdict(float)
        order = np.arange(len(questions))
        rng = np.random.default_rng(0)
        for epoch in range(self.epochs):
            rng.shuffle(order)
            for index in order:
                feats, gold = questions[index]
                scores = np.array([sum(weights[f] for f in fs) for fs in feats])
                scores -= scores.max()
                probs = np.exp(scores)
                probs /= probs.sum()
                # Responsibilities: the posterior over *which* correct
                # candidate, given that one of them is. This is the whole
                # difference from a perceptron -- credit is shared between the
                # correct nodes in proportion to current belief instead of
                # being assigned to a designated one.
                mass = float(probs[gold].sum())
                if mass <= 0.0:
                    continue
                responsibility = np.where(gold, probs / mass, 0.0)
                residual = responsibility - probs
                for fs, r in zip(feats, residual):
                    if r == 0.0:
                        continue
                    for f in fs:
                        grad = r - self.l2 * weights[f]
                        accum[f] += grad * grad
                        weights[f] += self.lr * grad / math.sqrt(accum[f] + 1e-8)
        self.weights = dict(weights)

    def _fit_gate(self, episodes: Sequence[Episode],
                  tok: SymbolTokenizer) -> None:
        """Fit ``g`` as the mixture weight it is, on held-out episodes.

        Every scorable node contributes, including the ones where no visible
        node carries the answer -- those are precisely the evidence that the
        copy branch is sometimes wrong to trust, and dropping them would fit a
        gate for a task in which copying always works.
        """
        scores: list[float] = []
        votes: list[float] = []
        backoff: list[float] = []
        for view, targets in self.training_views(episodes, tok, repeats=1,
                                                 seed=7,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                labels, raw = self._label_distribution(view, node)
                if not labels:
                    continue
                scores.append(raw)
                votes.append(float(labels.get(int(label_id), 0.0)))
                backoff.append(self.backoff_prob(view, node, int(label_id)))
        self.gate_map = self._fit_gate_map(scores, votes, backoff)

    def _fit_gate_map(self, scores: list[float], votes: list[float],
                      backoff: list[float]):
        """The one line ``ptrgen-argmax`` overrides. See that class."""
        return MassCalibrator().fit(scores, votes, backoff)

    def _fit_types(self, episodes: Sequence[Episode],
                   tok: SymbolTokenizer) -> None:
        """A backed-off structural lookup, with the pointed-at type as one key.

        Deliberately the same ladder ``corefer`` uses -- the keys are imported
        -- so that the label result is attributable to the label machinery and
        not to one model having a better type head than the other. Type is
        nearly a function of tree shape here, and a pointer is a poor way to ask
        about kind: 86% of the time a mistaken pick had the right type anyway.
        """
        counts: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (_, type_id) in targets.items():
                if type_id < 0:
                    continue
                pointed = self._pointed_type(view, node)
                for key in _type_keys(view, node, pointed):
                    counts[key][int(type_id)] += 1
        self.type_rules = dict(counts)

    # ---- prediction ---------------------------------------------------
    def _pointer(self, view: GraphView, node: int) -> dict[int, float]:
        """``{candidate node: probability}``, normalised over the candidates."""
        if not self.weights:
            return {}
        cands = self._candidates(view, node)
        if not cands:
            return {}
        scores = np.array([sum(self.weights.get(f, 0.0)
                               for f in _pair_features(view, node, j))
                           for j in cands])
        scores -= scores.max()
        probs = np.exp(scores)
        total = probs.sum()
        if not np.isfinite(total) or total <= 0.0:
            return {}
        return {j: float(p / total) for j, p in zip(cands, probs)}

    def _label_distribution(self, view: GraphView, node: int
                            ) -> tuple[dict[int, float], float]:
        """The copy branch: node probabilities summed onto the labels they carry.

        Summing is the point. Three nodes carrying one symbol are three routes
        to the same answer, and a pointer that splits its belief across them is
        not less sure about the *label* -- which is what the label head is
        asked. ``corefer`` reports the same quantity by accident of its softmax;
        here it is the definition.

        The raw score returned is the winning label's share, not the winning
        node's, for the same reason.
        """
        pointer = self._pointer(view, node)
        if not pointer:
            return {}, 0.0
        labels: dict[int, float] = collections.defaultdict(float)
        for j, p in pointer.items():
            label = view.labels[j]
            if label is not None:
                labels[int(label)] += p
        if not labels:
            return {}, 0.0
        return dict(labels), max(labels.values())

    def _pointed_type(self, view: GraphView, node: int) -> str | None:
        pointer = self._pointer(view, node)
        if not pointer:
            return None
        best = max(pointer, key=lambda j: (pointer[j], -j))
        return view.types[best]

    def _type_vote(self, view: GraphView, node: int) -> Votes:
        for key in _type_keys(view, node, self._pointed_type(view, node)):
            counts = self.type_rules.get(key)
            if counts and sum(counts.values()) >= self.min_support:
                total = sum(counts.values())
                top, n = counts.most_common(1)[0]
                return {int(top): 1.0}, min(0.15 + 0.8 * n / total, 0.95)
        return ABSTAIN

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            labels, raw = self._label_distribution(view, i)
            type_vote = self._type_vote(view, i)
            if not labels or not self.gate_map.fitted:
                out[i] = (ABSTAIN, type_vote)
                continue
            gate = float(self.gate_map(raw))
            out[i] = ((labels, gate) if gate > 0.0 else ABSTAIN, type_vote)
        return out

    def source_votes(self, view: GraphView) -> dict[int, Votes]:
        """The same pointer, reported as a binding.

        Confidence here is the pointer's own top share rather than the gate:
        the copy head is scored on where it pointed given that it pointed, and
        the gate is a claim about whether to point at all.
        """
        out: dict[int, Votes] = {}
        for i in view.hidden:
            pointer = self._pointer(view, i)
            if not pointer:
                continue
            out[i] = (pointer, min(0.15 + 0.8 * max(pointer.values()), 0.95))
        return out

    def n_symbolic_parameters(self) -> int:
        return len(self.weights) + len(self.type_rules)

    def render(self) -> str:
        rows = sorted(self.weights.items(), key=lambda kv: -abs(kv[1]))[:20]
        lines = [f"=== {self.name}: {len(self.weights)} pointer features, "
                 f"{self.n_questions} questions ===",
                 f"gate: {'fitted' if self.gate_map.fitted else 'unfitted'}"]
        if self.gate_map.fitted:
            lines.append("  score -> mass: " + ", ".join(
                f"{e:.2f}->{v:.2f}"
                for e, v in zip(self.gate_map.edges, self.gate_map.values)))
        lines.append("top pointer features:")
        lines += [f"  {str(k):<44} {v:+.3f}" for k, v in rows]
        return "\n".join(lines)


@register("ptrgen-001",
          doc="Gated copy/generate: marginal-likelihood pointer, mass-fitted gate.")
class PointerGenerator001(PointerGeneratorModel):
    """The model described in this module's docstring."""


@register("ptrgen-argmax",
          doc="ptrgen with the gate fitted as an argmax accuracy, as a control.")
class PointerGeneratorArgmax(PointerGeneratorModel):
    """One line different: the gate is fitted the way every other model's is.

    This exists so that the mass calibrator can be charged for its own effect.
    ``ptrgen-001`` changes two things at once against ``corefer`` -- how the
    pointer is trained and how its mass is set -- and without this row there is
    no way to say which of them moved the number.

    The score handed to the calibrator and the decision procedure are otherwise
    identical, so the difference between these two rows is exactly the
    difference between fitting a mixture weight and fitting an accuracy.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.gate_map = ScoreCalibrator()

    def _fit_gate_map(self, scores: list[float], votes: list[float],
                      backoff: list[float]):
        # "Was the top label the right one" is recoverable from the same
        # arrays: the winning label holds `max(labels.values())`, which is the
        # score, so gold got that mass exactly when gold won.
        correct = [v >= s - 1e-12 and v > 0.0 for s, v in zip(scores, votes)]
        return ScoreCalibrator().fit(scores, correct)
