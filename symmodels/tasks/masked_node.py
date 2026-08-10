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
        """Most-frequent-class, fitted on training graphs, scored on eval ones.

        Deliberately *not* measured on a masked sample: the floor is a property
        of the label distribution, and estimating it from a 15% sample would add
        variance to the one number that is supposed to be the fixed point the
        model is compared against. Every scorable node is counted instead.
        """
        train_types: collections.Counter[str] = collections.Counter()
        train_labels: collections.Counter[int] = collections.Counter()
        for ep in train:
            for label, type_ in zip(ep.graph.labels[:self.max_nodes],
                                    ep.graph.types[:self.max_nodes]):
                train_types[type_] += 1
                if self._scorable(label, type_, tok):
                    train_labels[tok.label_id(label)] += 1

        eval_types: collections.Counter[str] = collections.Counter()
        eval_labels: collections.Counter[int] = collections.Counter()
        for ep in episodes:
            for label, type_ in zip(ep.graph.labels[:self.max_nodes],
                                    ep.graph.types[:self.max_nodes]):
                eval_types[type_] += 1
                if self._scorable(label, type_, tok):
                    eval_labels[tok.label_id(label)] += 1

        _, type_bits = empirical_floor(dict(eval_types))
        _, label_bits = empirical_floor(dict(eval_labels))
        return {
            "type_acc": _const_acc(train_types, eval_types),
            "type_bits": type_bits,
            "type_n": float(sum(eval_types.values())),
            "label_acc": _const_acc(train_labels, eval_labels),
            "label_bits": label_bits,
            "label_n": float(sum(eval_labels.values())),
        }

    @staticmethod
    def _scorable(label: str, type_: str, tok: SymbolTokenizer) -> bool:
        """Mirrors the exclusion in ``collate_graph``: a node counts towards the
        label score only if it has a label and the vocabulary can name it."""
        return bool(label) and type_ not in STRUCTURAL \
            and tok.label_id(label) != tok.unk_id


def _const_acc(train: collections.Counter, evaluation: collections.Counter) -> float:
    """Accuracy of always answering whatever was commonest in training.

    Fitted on train and scored on eval, rather than scored on its own argmax,
    because a floor that gets to look at the answers is not a floor.
    """
    n = sum(evaluation.values())
    if not n or not train:
        return float("nan")
    best = max(train, key=lambda k: train[k])
    return evaluation.get(best, 0) / n
