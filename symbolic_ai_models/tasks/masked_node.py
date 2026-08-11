"""Masked-node prediction over the episode's term graph.

The structural counterpart to next-token prediction, and the reason this repo
exists. ``langcurriculum`` builds every episode as a typed term and only then
renders it as prose, so for each episode there is a graph that is not a parse of
the text but the thing the text was generated *from*. Hiding a node in that
graph and asking a model to name it is a question about structure that has an
exact answer, no annotator, and no way to be right for surface reasons.

Two heads, reported separately and never averaged into one number:

* **type** — what kind of node sits here: a predicate, a list, a named field, an
  identifier. The structural question. A model can do well here while
  understanding nothing about reference, because term trees have strong shape
  regularities.
* **label** — *which* predicate, *which* variable, *which* field name. The
  symbolic question, and the harder of the two.

  It is harder for a *different reason* than this docstring claimed for a long
  time. The claim was that the curriculum invents its vocabulary per episode, so
  the answer is usually a name the model has never seen. Measured across all 179
  lessons, **100.0%** of scored labels are symbols that appear in training: the
  generator varies which name fills a slot, not the pool it draws from. What
  makes the label hard is choosing among familiar symbols, not naming unfamiliar
  ones — and a model that refuses to memorise is handicapping itself for a
  benefit this task does not pay.

Structural nodes carry no label and are scored on type alone, so that predicting
the empty label of a list — which is free — cannot inflate the score.
"""

from __future__ import annotations

import collections
from typing import Sequence

import numpy as np
import torch

from ..data.batch import IGNORE, collate_graph
from ..data.curriculum import Episode
from ..data.graph import STRUCTURAL, TYPE_TO_ID
from ..data.tokenizer import SymbolTokenizer
from ..models.base import ModelOutput
from .base import Task, TaskOutput, Totals, empirical_floor, ratio, score_block

__all__ = ["MaskedNode"]


def _pointer_counts(out: ModelOutput, batch) -> dict[str, float]:
    """Score a pointer by *what it picked*, never by index.

    Several nodes usually carry the same label, so an index-equality check would
    mark a correct copy wrong whenever the model chose a different valid source.
    Correctness is therefore ``label_group[picked] == label_group[asked]``.

    Scored over every masked node that has a label, including the ones the
    vocabulary cannot name. That is the point: those are 88.5% invented `ident`
    names, they are 80.7% copyable, and the label head drops them.
    """
    logits = getattr(out, "source_logits", None)
    if logits is None or batch.label_group is None:
        return {}
    asked = batch.label_group != IGNORE
    masked = batch.target_types != IGNORE
    scored = asked & masked
    if not bool(scored.any()):
        return {}
    # A pointer may not choose a padded position, and must not choose itself --
    # a node cannot be its own evidence when its label is what is hidden.
    valid = batch.pad_mask.clone()
    eye = torch.eye(valid.shape[1], dtype=torch.bool, device=valid.device)
    allowed = valid[:, None, :] & ~eye[None]
    picked = logits.masked_fill(~allowed, float("-inf")).argmax(-1)
    picked_group = torch.gather(batch.label_group, 1, picked)
    correct = (picked_group == batch.label_group) & scored
    return {"copy_n": float(scored.sum()), "copy_correct": float(correct.sum())}


def _copy_counts(batch) -> dict[str, float]:
    """How much of the answer is already sitting in the graph, in plain sight.

    The label head is scored as a choice among 8,192 symbols, but the task is
    mostly *binding*: the generator picks names arbitrarily and reuses them, so
    the question is usually "which node do I corefer with", not "which symbol is
    this". On the full curriculum 71.9% of scored answers already appear on a
    visible node of the same episode, while the best model in the table sits
    near 0.36 accuracy -- roughly half the reachable signal is untouched, and
    none of the models has a pointer.

    ``copy_censored`` counts the positions that are copyable but excluded from
    the label score because the vocabulary cannot name them. Those are 88.5%
    invented ``ident`` names on the full curriculum, and they are exactly where
    copying is the *only* available route, so a metric that drops them rewards
    naming and hides binding.
    """
    src = getattr(batch, "target_source", None)
    if src is None or batch.target_tokens is None:
        return {}
    has_source = src != IGNORE
    scored = batch.target_tokens != IGNORE
    return {"copy_reachable": float((has_source & scored).sum()),
            "copy_censored": float((has_source & ~scored).sum())}


class MaskedNode(Task):
    """Hide nodes; predict their type and their label."""

    name = "node"

    def __init__(self, mask_rate: float = 0.15, type_weight: float = 0.5,
                 max_nodes: int = 256, seed: int = 0) -> None:
        self.mask_rate = mask_rate
        self.type_weight = type_weight
        self.max_nodes = max_nodes
        self.rng = np.random.default_rng(seed)

    def collate(self, episodes: Sequence[Episode], tok: SymbolTokenizer):
        return collate_graph(episodes, tok, max_nodes=self.max_nodes,
                             mask_rate=self.mask_rate, rng=self.rng)

    def compute(self, out: ModelOutput, batch) -> TaskOutput:
        label_loss, label_counts = score_block(
            out.symbol_logits, batch.target_tokens, "label")
        type_loss, type_counts = score_block(
            out.type_logits, batch.target_types, "type")
        return TaskOutput(loss=label_loss + self.type_weight * type_loss,
                          counts={**label_counts, **type_counts,
                                  **_copy_counts(batch),
                                  **_pointer_counts(out, batch)})

    def summarize(self, totals: Totals) -> dict[str, float]:
        """Both heads, plus how much of the masked set the label score covers.

        Every masked node has a type target, but only a node whose label the
        vocabulary can name has a label target — and the ones it cannot name are
        systematically the *interesting* ones, the per-episode invented symbols.
        About 16% of masked labels are dropped this way on the full curriculum,
        so ``label_acc`` is an accuracy over the nameable 84% and is optimistic
        for exactly that reason. Reporting the coverage is the least that can be
        done about it short of giving the models a copy mechanism.
        """
        out = {**ratio(totals, "label"), **ratio(totals, "type")}
        scored, masked = out.get("label_n", 0.0), out.get("type_n", 0.0)
        out["label_coverage"] = scored / masked if masked else float("nan")

        # The ceiling, reported next to the score so the gap is visible in every
        # run rather than in a scratch script somebody has to rediscover.
        if totals.get("copy_n"):
            out["copy_acc"] = totals.get("copy_correct", 0.0) / totals["copy_n"]
            out["copy_scored_n"] = totals["copy_n"]

        reachable = totals.get("copy_reachable", 0.0)
        out["copy_ceiling"] = reachable / scored if scored else float("nan")
        censored = totals.get("copy_censored", 0.0)
        out["copy_censored"] = censored
        return out

    def floor(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
              train: Sequence[Episode]) -> dict[str, float]:
        """A **structure-only** baseline, fitted on train, scored on eval.

        A constant guess is far too weak a floor here, and reporting one would
        badly overstate the result. Node type is very nearly determined by the
        shape of the tree: a ``field`` node is always the child of a record, a
        ``char`` always the child of a string. On the curriculum's graphs, a
        lookup table keyed on nothing but ``(parent type, slot, depth)`` gets
        about 0.96 — so a model scoring 0.95 against a majority-class floor of
        0.33 has not learned something worth 0.9 lift, it has learned less than
        the table.

        So the floor is that table: the most common answer for each structural
        context, backing off to the global majority for a context the training
        graphs never showed. It knows the shape of the tree and nothing about
        any symbol in it, which makes the lift above it the part of the score
        that is actually about reference.

        Fitted on train and scored on eval, and — since the correction described
        in :meth:`_nodes` — under the same masking the models face, so the floor
        is what a structure-only lookup gets *given what a model is given*
        rather than given the whole graph. Several masked draws are averaged so
        that sampling 15% of nodes does not put noise into the one number
        everything else is compared against.
        """
        # Several masked draws per training episode, so the lookup is fitted on
        # a comparable amount of evidence to the models', which also see
        # repeated maskings of the same graphs.
        type_rule, label_rule = _ContextRule(), _ContextRule()
        rng = np.random.default_rng(4)
        for _ in range(4):
            for ep in train:
                for ctx, label, type_ in self._nodes(ep, tok, rng):
                    type_rule.observe(ctx, type_)
                    if label is not None:
                        label_rule.observe(ctx, label)

        type_hits = type_n = label_hits = label_n = 0
        eval_types: collections.Counter[str] = collections.Counter()
        eval_labels: collections.Counter[int] = collections.Counter()
        # Averaged over several draws for the same reason it is fitted over
        # several: one 15% sample of an evaluation set is a few hundred nodes,
        # and the floor is the fixed point every lift in the repo is measured
        # against, so it cannot be the noisiest number in the table.
        scoring = np.random.default_rng(12345)
        for _ in range(8):
            for ep in episodes:
                for ctx, label, type_ in self._nodes(ep, tok, scoring):
                    type_hits += type_rule.predict(ctx) == type_
                    type_n += 1
                    eval_types[type_] += 1
                    if label is not None:
                        label_hits += label_rule.predict(ctx) == label
                        label_n += 1
                        eval_labels[label] += 1

        copy_acc = self._copy_floor(episodes, train, tok)

        _, type_bits = empirical_floor(dict(eval_types))
        _, label_bits = empirical_floor(dict(eval_labels))
        return {
            "type_acc": type_hits / type_n if type_n else float("nan"),
            "type_bits": type_bits, "type_n": float(type_n),
            "label_acc": label_hits / label_n if label_n else float("nan"),
            "label_bits": label_bits, "label_n": float(label_n),
            "copy_acc": copy_acc,
        }

    def _copy_floor(self, episodes: Sequence[Episode],
                    train: Sequence[Episode], tok: SymbolTokenizer) -> float:
        """What a structure-only pointer gets: copy from a fixed relative offset.

        The copy head needs a floor for the same reason the other two do. A
        random pointer scores about 0.05 and an oracle 0.73, and quoting a copy
        accuracy between those without saying which end is cheap would be
        exactly the mistake this repo keeps having to undo.

        The rule knows the shape of the tree and nothing about any symbol: for
        each structural context it learns the commonest *offset* to a node that
        turned out to carry the same label, then applies that offset blind. It
        cannot read what any node says, so whatever a real pointer scores above
        this is the part that came from reading the episode.
        """
        rule: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        rng = np.random.default_rng(4)
        for _ in range(4):
            for ep in train:
                for ctx, i, source, _ in self._pointer_examples(ep, rng):
                    if source is not None:
                        rule[ctx][i - source] += 1

        overall: collections.Counter = collections.Counter()
        for counts in rule.values():
            overall.update(counts)
        fallback = overall.most_common(1)[0][0] if overall else 1

        hits = total = 0
        scoring = np.random.default_rng(12345)
        for _ in range(8):
            for ep in episodes:
                for ctx, i, _, labels in self._pointer_examples(ep, scoring):
                    counts = rule.get(ctx)
                    offset = counts.most_common(1)[0][0] if counts else fallback
                    j = i - offset
                    total += 1
                    hits += 0 <= j < len(labels) and j != i \
                        and labels[j] == labels[i]
        return hits / total if total else float("nan")

    def _pointer_examples(self, ep: Episode, rng: np.random.Generator):
        """``(context, node, a visible same-label node or None, labels)``.

        Same masking regime as everything else here, and the same reason: a
        floor measured under conditions the models do not face is not a floor.
        """
        g = ep.graph
        n = min(len(g), self.max_nodes)
        if not n:
            return
        hidden = set(np.flatnonzero(rng.random(n) < self.mask_rate).tolist())
        if not hidden:
            hidden = {int(rng.integers(0, n))}
        labels = list(g.labels[:n])
        for i in sorted(hidden):
            if not labels[i] or g.types[i] in STRUCTURAL:
                continue
            p = g.parent[i]
            parent_type = ("ROOT" if not 0 <= p < n
                           else ("mask" if p in hidden else g.types[p]))
            ctx = (parent_type, min(g.slot[i], 8), min(g.depth[i], 8))
            source = next((j for j in range(n)
                           if j not in hidden and labels[j] == labels[i]), None)
            yield ctx, i, source, labels

    def _nodes(self, ep: Episode, tok: SymbolTokenizer,
               rng: np.random.Generator | None = None):
        """``(context, label id or None, type)`` for the nodes this episode hides.

        The context is what a model can *actually* read, which is a stronger
        requirement than it sounds and was got wrong here for a long time. The
        first version read the true parent type straight off the unmasked graph
        and scored every node in it, while a model reads ``mask`` wherever the
        parent is hidden and is scored only where the mask fell. The floor was
        therefore computed with information the models were denied, and it made
        every lift in the repo pessimistic by an unknown amount.

        So the mask is drawn here at the rate evaluation uses, a hidden parent
        contributes ``mask`` exactly as it does in a
        :class:`~symbolic_ai_models.models.symbolic.GraphView`, and only masked
        nodes are yielded. The floor is then what the best structure-only lookup
        gets *under the conditions the model faces*, which is the only version
        of it worth comparing against.

        The mask positions are not the identical ones any particular evaluation
        draws — the floor is a property of the distribution, so matching the
        regime is what matters, not the individual draw.
        """
        rng = rng or np.random.default_rng(0)
        g = ep.graph
        n = min(len(g), self.max_nodes)
        if not n:
            return
        hidden = set(np.flatnonzero(rng.random(n) < self.mask_rate).tolist())
        if not hidden:
            hidden = {int(rng.integers(0, n))}

        has_children = [False] * n
        for i in range(n):
            p = g.parent[i]
            if 0 <= p < n:
                has_children[p] = True
        for i in sorted(hidden):
            p = g.parent[i]
            parent_type = ("ROOT" if not 0 <= p < n
                           else ("mask" if p in hidden else g.types[p]))
            ctx = (parent_type, min(g.slot[i], 8), min(g.depth[i], 8),
                   has_children[i])
            label = (tok.label_id(g.labels[i])
                     if self._scorable(g.labels[i], g.types[i], tok) else None)
            yield ctx, label, g.types[i]

    @staticmethod
    def _scorable(label: str, type_: str, tok: SymbolTokenizer) -> bool:
        """Mirrors the exclusion in ``collate_graph``: a node counts towards the
        label score only if it has a label and the vocabulary can name it."""
        return bool(label) and type_ not in STRUCTURAL \
            and tok.label_id(label) != tok.unk_id


class _ContextRule:
    """Most common answer per structural context, backing off to the global one.

    A lookup table, deliberately. The floor is supposed to be the score of
    something that has the tree's shape and no idea what any symbol means, and a
    table is exactly that — there is nothing in it that could be mistaken for
    understanding.
    """

    def __init__(self) -> None:
        self.by_context: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        self.overall: collections.Counter = collections.Counter()

    def observe(self, context: tuple, answer) -> None:
        self.by_context[context][answer] += 1
        self.overall[answer] += 1

    def predict(self, context: tuple):
        counts = self.by_context.get(context)
        if counts:
            return counts.most_common(1)[0][0]
        return self.overall.most_common(1)[0][0] if self.overall else None
