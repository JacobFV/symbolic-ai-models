"""Variable-order back-off counting: the floor for the rule-based family.

The symbolic counterpart to ``gru``. It has no parser, no logic and no search —
it counts contexts and backs off to shorter ones when a long context is unseen,
which is what language modelling looked like before it looked like anything
else. Everything else in the rule-based family has to beat this, and a symbolic
method that cannot is doing its reasoning for nothing.

On the graph side the same idea applies to structure rather than to order: the
context of a node is where it sits — its parent's type, the slot it occupies,
what its siblings are called — and the prediction is whatever most often sat
there in the training graphs. That is a genuinely strong baseline on term trees,
and it is the same lookup-table logic the masked-node *floor* is built from, one
step richer.
"""

from __future__ import annotations

import collections
from typing import Sequence

from ...data.curriculum import Episode
from ...data.graph import TYPE_TO_ID
from ...data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["NGramModel"]


@register("ngram", doc="Variable-order back-off counts over tokens and over node contexts.")
class NGramModel(RuleBasedModel):
    """Counts, backed off from the longest context that was ever seen.

    ``extra.order`` sets the longest token context kept (default 4).
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.order = int(cfg.get("order", 4))
        #: ``context -> Counter(next symbol)``, one table per order
        self.text: list[dict[tuple, collections.Counter]] = []
        self.label: dict[tuple, collections.Counter] = {}
        self.type: dict[tuple, collections.Counter] = {}

    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        self.text = [collections.defaultdict(collections.Counter)
                     for _ in range(self.order + 1)]
        self.label = collections.defaultdict(collections.Counter)
        self.type = collections.defaultdict(collections.Counter)

        for ep in episodes:
            ids = tok.encode(ep.text, bos=True, eos=True)
            for t in range(len(ids) - 1):
                nxt = ids[t + 1]
                for k in range(self.order + 1):
                    if t + 1 >= k:
                        self.text[k][tuple(ids[t + 1 - k:t + 1])][nxt] += 1

        # Graph contexts are counted on *masked* views, so the keys recorded
        # here are keys that will still resolve at evaluation time.
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_len):
            for node, (label_id, type_id) in targets.items():
                for key in self._view_contexts(view, node):
                    if type_id >= 0:
                        self.type[key][type_id] += 1
                    if label_id >= 0:
                        self.label[key][label_id] += 1

    # ---- prediction ---------------------------------------------------
    def text_votes(self, ids: Sequence[int]) -> list[Votes]:
        out: list[Votes] = []
        for t in range(len(ids)):
            # Only ids[:t+1] is ever read, so this is causal by construction.
            out.append(self._backoff_vote(
                [self.text[k].get(tuple(ids[t + 1 - k:t + 1]))
                 for k in range(min(self.order, t + 1), -1, -1)]))
        return out

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            keys = self._view_contexts(view, i)
            out[i] = (self._backoff_vote([self.label.get(k) for k in keys]),
                      self._backoff_vote([self.type.get(k) for k in keys]))
        return out

    @staticmethod
    def _view_contexts(view: GraphView, i: int) -> list[tuple]:
        """Context keys for node ``i``, most specific first.

        Structure first — parent type, slot, depth, arity — with the parent's
        *label* as the one lexical key, because on a term tree "the second
        argument of ``parent``" predicts far better than "the second argument of
        something". When the parent is itself hidden the lexical key simply
        misses and the model falls through to the structural ones.
        """
        p = view.parent[i]
        ptype = (view.types[p] or "mask") if p >= 0 else "ROOT"
        plabel = (view.word(p) or "") if p >= 0 else ""
        arity = len(view.children(i))
        return [
            ("pl", plabel, view.slot[i]),
            ("pt", ptype, view.slot[i], min(view.depth[i], 6)),
            ("pt", ptype, view.slot[i]),
            ("d", min(view.depth[i], 6), arity > 0),
        ]

    @staticmethod
    def _backoff_vote(tables: Sequence[collections.Counter | None],
                      strength: float = 4.0) -> Votes:
        """The first context that was ever observed wins; confidence grows with
        how often it was.

        ``m / (m + strength)`` is the standard shape: one observation is weak
        evidence, twenty is strong, and nothing is ever certain. A context never
        seen in training contributes nothing and the model falls through to the
        next one, and then to the back-off.
        """
        for table in tables:
            if table:
                mass = sum(table.values())
                return dict(table), mass / (mass + strength)
        return ABSTAIN

    def n_symbolic_parameters(self) -> int:
        return (sum(len(v) for tbl in self.text for v in tbl.values())
                + sum(len(v) for v in self.label.values())
                + sum(len(v) for v in self.type.values()))
