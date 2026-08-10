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
  symbolic question, and the hard one, because the curriculum invents its
  vocabulary per episode: the answer is very often a name the model has never
  seen and can only get from how the node sits among its neighbours.

Structural nodes carry no label and are scored on type alone, so that predicting
the empty label of a list — which is free — cannot inflate the score.
"""

from __future__ import annotations

import collections
from typing import Sequence

import numpy as np

from ..data.batch import collate_graph
from ..data.curriculum import Episode
from ..data.graph import STRUCTURAL, TYPE_TO_ID
from ..data.tokenizer import SymbolTokenizer
from ..models.base import ModelOutput
from .base import Task, TaskOutput, Totals, empirical_floor, ratio, score_block

__all__ = ["MaskedNode"]


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
                          counts={**label_counts, **type_counts})

    def summarize(self, totals: Totals) -> dict[str, float]:
        return {**ratio(totals, "label"), **ratio(totals, "type")}

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

        Fitted on train and scored on eval, and computed over every scorable
        node rather than over a masked sample — estimating it from 15% of nodes
        would put variance into the one number that is meant to be the fixed
        point the model is compared against.
        """
        type_rule, label_rule = _ContextRule(), _ContextRule()
        for ep in train:
            for ctx, label, type_ in self._nodes(ep, tok):
                type_rule.observe(ctx, type_)
                if label is not None:
                    label_rule.observe(ctx, label)

        type_hits = type_n = label_hits = label_n = 0
        eval_types: collections.Counter[str] = collections.Counter()
        eval_labels: collections.Counter[int] = collections.Counter()
        for ep in episodes:
            for ctx, label, type_ in self._nodes(ep, tok):
                type_hits += type_rule.predict(ctx) == type_
                type_n += 1
                eval_types[type_] += 1
                if label is not None:
                    label_hits += label_rule.predict(ctx) == label
                    label_n += 1
                    eval_labels[label] += 1

        _, type_bits = empirical_floor(dict(eval_types))
        _, label_bits = empirical_floor(dict(eval_labels))
        return {
            "type_acc": type_hits / type_n if type_n else float("nan"),
            "type_bits": type_bits, "type_n": float(type_n),
            "label_acc": label_hits / label_n if label_n else float("nan"),
            "label_bits": label_bits, "label_n": float(label_n),
        }

    def _nodes(self, ep: Episode, tok: SymbolTokenizer):
        """``(structural context, label id or None, type)`` per scorable node.

        The context is exactly what a model can read off the relations without
        seeing a single symbol: what kind of node the parent is, which slot this
        one sits in, how deep it is, and whether it has children of its own.
        """
        g = ep.graph
        n = min(len(g), self.max_nodes)
        has_children = [False] * n
        for i in range(n):
            p = g.parent[i]
            if 0 <= p < n:
                has_children[p] = True
        for i in range(n):
            p = g.parent[i]
            ctx = (g.types[p] if 0 <= p < n else "ROOT",
                   min(g.slot[i], 8), min(g.depth[i], 8), has_children[i])
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
