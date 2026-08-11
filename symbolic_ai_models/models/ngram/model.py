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
from ..symbolic import (ABSTAIN, GraphView, RuleBasedModel, Votes,
                        prune_tables)

__all__ = ["NGramModel"]


@register("ngram", doc="Variable-order back-off counts over tokens and over node contexts.")
class NGramModel(RuleBasedModel):
    """Counts, backed off from the longest context that was ever seen.

    ``extra.order`` sets the longest token context kept (default 4).
    """

    LEARNED = ("text", "label", "type", "order", "class_next", "class_of")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.order = int(cfg.get("order", 4))
        #: Bound on stored contexts per table. Counting models grow with
        #: distinct contexts and had no limit; see `prune_tables`.
        self.max_entries = int(cfg.get("max_entries", 400_000))
        self.min_count = int(cfg.get("min_count", 1))
        #: ``context -> Counter(next symbol)``, one table per order
        self.text: list[dict[tuple, collections.Counter]] = []
        self.label: dict[tuple, collections.Counter] = {}
        self.type: dict[tuple, collections.Counter] = {}
        #: token id -> the class its parser assigned, when it assigned one
        self.class_of: dict[int, str] = {}
        #: class context -> next token. The abstract back-off level.
        self.class_next: dict[tuple, collections.Counter] = {}

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

        self._learn_classes(episodes, tok)

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
        self._prune()

    # ---- prediction ---------------------------------------------------
    def _learn_classes(self, episodes: Sequence[Episode],
                       tok: SymbolTokenizer) -> None:
        """Add one back-off level above the literal contexts, from the parser.

        Where the token tables back off to a *shorter* context, this backs off to
        a more *abstract* one: the same span read as the classes the parser
        assigned. A context never seen with these particular words can still
        resolve if it was seen with words of the same kind.

        With ``parser=none`` nothing is assigned and the table is left empty, so
        this model is then bit-identical to what it was before the parser
        existed — which is the property that makes the parser x reasoner matrix
        readable, since the ``none`` column is a true control rather than a
        differently-shaped model.
        """
        self.class_of = {}
        self.class_next = {}

        votes: dict[str, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for ep in episodes:
            result = self.parser.parse(ep.text)
            for i, word in enumerate(result.tokens):
                assigned = result.classes.get(i)
                if assigned:
                    votes[word][assigned] += 1
        if not votes:                       # the parser has no opinion
            return

        word_class = {w: c.most_common(1)[0][0] for w, c in votes.items()}
        for token_id, piece in enumerate(tok.itos):
            klass = word_class.get(piece.strip())
            if klass:
                self.class_of[token_id] = klass

        table: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for ep in episodes:
            ids = tok.encode(ep.text, bos=True, eos=True)
            abstract = [self.class_of.get(i) for i in ids]
            for t in range(len(ids) - 1):
                for k in range(1, self.order + 1):
                    if t + 1 < k:
                        continue
                    window = abstract[t + 1 - k:t + 1]
                    # Only wholly-classified spans generalise. A window with a
                    # gap in it is the literal context wearing a hat, and
                    # keeping those would just duplicate the token tables.
                    if all(window):
                        table[tuple(window)][ids[t + 1]] += 1
        self.class_next = dict(table)

    def _prune(self) -> None:
        """Bound every table, so memory stops growing with distinct contexts.

        The cutoff applies only above order 1. Short contexts are few and carry
        the back-off, so pruning them would cost far more than it saves, while
        the long contexts are where both the entries and the singletons are.
        """
        for k in range(2, len(self.text)):
            self.text[k] = prune_tables(self.text[k],
                                        max_entries=self.max_entries,
                                        min_count=self.min_count + 1)
        self.label = prune_tables(self.label, max_entries=self.max_entries,
                                  min_count=self.min_count)
        self.type = prune_tables(self.type, max_entries=self.max_entries,
                                 min_count=self.min_count)
        self.class_next = prune_tables(self.class_next,
                                       max_entries=self.max_entries,
                                       min_count=self.min_count)

    def text_votes(self, ids: Sequence[int]) -> list[Votes]:
        out: list[Votes] = []
        for t in range(len(ids)):
            # Only ids[:t+1] is ever read, so this is causal by construction.
            # Interleaved by specificity: a literal k-gram, then the same span
            # read as classes, then the literal (k-1)-gram, and so on.
            #
            # Appending the class tables *after* every literal one, which is the
            # obvious arrangement, makes them dead code: the literal 1-token
            # context is seen for nearly every token in training, so back-off
            # reaches it first and stops, and the abstraction is never
            # consulted. Measured before this was fixed - the logits were
            # bit-identical for `none`, `induced`, `chunker` and `regex` while
            # the class tables sat there fully populated.
            tables: list[collections.Counter | None] = []
            for k in range(min(self.order, t + 1), 0, -1):
                tables.append(self.text[k].get(tuple(ids[t + 1 - k:t + 1])))
                tables.append(self._class_table(ids, t, k))
            tables.append(self.text[0].get(()))
            out.append(self._backoff_vote(tables))
        return out

    def _class_table(self, ids: Sequence[int], t: int,
                     k: int) -> collections.Counter | None:
        """The last ``k`` positions read as parser classes, if all were assigned."""
        if not self.class_next:
            return None
        window = [self.class_of.get(i) for i in ids[t + 1 - k:t + 1]]
        return self.class_next.get(tuple(window)) if all(window) else None

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
                + sum(len(v) for v in self.type.values())
                + sum(len(v) for v in self.class_next.values()))
