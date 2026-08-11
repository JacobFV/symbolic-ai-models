"""Context Tree Weighting: a Bayesian mixture over *every* context tree at once.

Willems, Shtarkov and Tjalkens (1995). ``ngram`` picks one context — the longest
that was ever observed — and backs off when it misses; the choice is a heuristic
and the confidence attached to it is a made-up formula. CTW does not choose. It
maintains, implicitly, a mixture over all context trees up to depth ``D``,
weighted by a prior on tree shapes, and its prediction is the posterior mixture.
The result is the classical one: the code length is within a constant of the
best tree in hindsight, without ever being told which tree that is.

That is worth having in this repo precisely because ``ngram`` is already here.
The two see identical counts from identical contexts and differ only in how they
combine them, so whatever separates their scores is the value of mixing over
model orders rather than selecting one.

The implementation is the standard incremental form, over the symbol alphabet
rather than over bits:

* every node on the current context path keeps Krichevsky-Trofimov counts and an
  accumulated log KT probability of the symbols that reached it;
* a node's *weighted* probability is ``½·KT(node) + ½·∏ weighted(children)``,
  which is the CTW recursion — half the prior mass on "the context stops here",
  half on "it goes deeper";
* the predictive probability of a symbol is the ratio of the root's weighted
  probability after hypothetically observing it to its value now.

Only symbols that were actually seen somewhere on the path are scored, which is
what keeps the ratio computation cheap: the rest are indistinguishable to the
model and are left to the shared back-off.
"""

from __future__ import annotations

import collections
import math
from typing import Sequence

from ...data.curriculum import Episode
from ...data.tokenizer import SymbolTokenizer
from ..base import ModelConfig, N_TYPES
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["CTWModel"]

LOG_HALF = math.log(0.5)


class _Node:
    """One context. ``kt`` accumulates the log KT probability of what reached it."""

    __slots__ = ("counts", "total", "log_kt", "log_w", "children", "child_logsum")

    def __init__(self) -> None:
        self.counts: dict[int, int] = {}
        self.total = 0
        self.log_kt = 0.0
        self.log_w = 0.0
        self.children: dict[int, "_Node"] = {}
        self.child_logsum = 0.0

    def kt_logp(self, symbol: int, alphabet: float) -> float:
        """Krichevsky-Trofimov: add-½ smoothing, the minimax-optimal prior for
        an unknown discrete source."""
        return math.log((self.counts.get(symbol, 0) + 0.5)
                        / (self.total + 0.5 * alphabet))


class _Tree:
    """A context tree over one symbol stream."""

    def __init__(self, depth: int, alphabet: int) -> None:
        self.depth = depth
        self.alphabet = float(alphabet)
        self.root = _Node()

    def path(self, context: Sequence[int], *, create: bool) -> list[_Node]:
        """Root first, deepest last. ``context`` is most-recent-first."""
        nodes = [self.root]
        node = self.root
        for symbol in context[:self.depth]:
            child = node.children.get(symbol)
            if child is None:
                if not create:
                    break
                child = node.children[symbol] = _Node()
            nodes.append(child)
            node = child
        return nodes

    def update(self, context: Sequence[int], symbol: int) -> None:
        """Observe ``symbol`` in ``context``; refresh the path leaf-upward."""
        nodes = self.path(context, create=True)
        for depth in range(len(nodes) - 1, -1, -1):
            node = nodes[depth]
            node.log_kt += node.kt_logp(symbol, self.alphabet)
            node.counts[symbol] = node.counts.get(symbol, 0) + 1
            node.total += 1
            before = node.log_w
            node.log_w = (node.log_kt if depth == len(nodes) - 1 or not node.children
                          else _logaddexp(LOG_HALF + node.log_kt,
                                          LOG_HALF + node.child_logsum))
            if depth:                       # tell the parent its child moved
                nodes[depth - 1].child_logsum += node.log_w - before

    def prune(self, min_count: int, min_depth: int = 2) -> None:
        """Drop thinly-evidenced branches, then rebuild the weights above them.

        A context tree grows with distinct contexts — about 1.4 nodes per token
        on this data, so a large corpus wants tens of millions and several
        gigabytes. The deep nodes are where nearly all of them are and where
        almost none of the evidence is: a context seen once contributes a KT
        estimate that is barely distinguishable from its parent's.

        The weights *must* be rebuilt afterwards. ``log_w`` and
        ``child_logsum`` are maintained incrementally, so deleting a child
        leaves its parent claiming mass from a subtree that no longer exists,
        and the weighted probabilities would quietly stop being probabilities.
        """
        self._prune_node(self.root, 0, min_count, min_depth)
        self._rebuild(self.root, 0)

    def _prune_node(self, node: _Node, depth: int, min_count: int,
                    min_depth: int) -> None:
        if depth >= min_depth:
            for symbol in [s for s, c in node.children.items()
                           if c.total < min_count]:
                del node.children[symbol]
        for child in node.children.values():
            self._prune_node(child, depth + 1, min_count, min_depth)

    def _rebuild(self, node: _Node, depth: int) -> float:
        """Recompute ``log_w`` bottom-up; returns this node's weighted value."""
        if not node.children or depth >= self.depth:
            node.child_logsum = 0.0
            node.log_w = node.log_kt
            return node.log_w
        node.child_logsum = sum(self._rebuild(c, depth + 1)
                                for c in node.children.values())
        node.log_w = _logaddexp(LOG_HALF + node.log_kt,
                                LOG_HALF + node.child_logsum)
        return node.log_w

    def size(self) -> int:
        return _size(self.root)

    def predict(self, context: Sequence[int]) -> dict[int, float]:
        """``{symbol: P(symbol | context)}`` for the symbols the path has seen.

        Each candidate is scored by asking what the root's weighted probability
        *would* become if that symbol arrived — the definition of a sequential
        predictive probability, evaluated without mutating the tree.
        """
        nodes = self.path(context, create=False)
        candidates: set[int] = set()
        for node in nodes:
            candidates.update(node.counts)
        if not candidates:
            return {}

        out: dict[int, float] = {}
        for symbol in candidates:
            log_w = 0.0                     # the deepest node's weighted value
            for depth in range(len(nodes) - 1, -1, -1):
                node = nodes[depth]
                log_kt = node.log_kt + node.kt_logp(symbol, self.alphabet)
                if depth == len(nodes) - 1 or not node.children:
                    log_w = log_kt
                else:
                    # only the child on this path changed; the siblings' sum
                    # is carried unchanged
                    sibling_sum = node.child_logsum - nodes[depth + 1].log_w
                    log_w = _logaddexp(LOG_HALF + log_kt,
                                       LOG_HALF + sibling_sum + log_w)
            out[symbol] = math.exp(min(log_w - self.root.log_w, 0.0))
        return out


def _logaddexp(a: float, b: float) -> float:
    if a < b:
        a, b = b, a
    return a if b == -math.inf else a + math.log1p(math.exp(b - a))


@register("ctw-001", doc="Context Tree Weighting: Bayesian mixture over all context trees.")
class CTWModel(RuleBasedModel):
    """The principled counterpart to ``ngram``: mix orders, never choose one.

    ``extra.depth`` sets the deepest context kept (default 5).
    """

    LEARNED = ("text_tree", "node_tree", "type_tree", "depth")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.depth = int(cfg.get("depth", 5))
        #: Drop context-tree nodes below this many observations. Off by
        #: default, unlike the cutoff in `ngram`, and the difference is the
        #: point: pruning `ngram` *improves* it (4.029 -> 3.857 bits/token,
        #: because a singleton context makes a confident claim on no evidence),
        #: while pruning here costs 0.4 bits for 31% of the memory. CTW's deep
        #: nodes are not a long tail of noise — mixing over them is the
        #: algorithm. Raise this only when memory is the binding constraint,
        #: and know what it buys.
        self.min_count = int(cfg.get("min_count", 1))
        self.text_tree: _Tree | None = None
        self.node_tree: _Tree | None = None
        self.type_tree: _Tree | None = None

    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        self.text_tree = _Tree(self.depth, len(tok))
        for ep in episodes:
            ids = tok.encode(ep.text, bos=True, eos=True)
            for t in range(len(ids) - 1):
                self.text_tree.update(_reversed_context(ids, t, self.depth),
                                      ids[t + 1])

        # The graph side gets its own tree, over a context that walks *up* the
        # term rather than backwards along a string: the labels of the parent,
        # the grandparent and so on. That is the tree's analogue of "what came
        # just before", and it is what makes one implementation serve both.
        self.node_tree = _Tree(self.depth, len(tok))
        # Types are a third stream through the same machinery. Leaving them to
        # the back-off would have scored the abstention rather than the method.
        self.type_tree = _Tree(self.depth, N_TYPES)
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (label_id, type_id) in targets.items():
                context = _ancestor_context(view, node, self.depth)
                if label_id >= 0:
                    self.node_tree.update(context, label_id)
                if type_id >= 0:
                    self.type_tree.update(context, type_id)
        if self.min_count > 1:
            for tree in (self.text_tree, self.node_tree, self.type_tree):
                tree.prune(self.min_count)

    def text_votes(self, ids: Sequence[int]) -> list[Votes]:
        if self.text_tree is None:
            return [ABSTAIN] * len(ids)
        out: list[Votes] = []
        for t in range(len(ids)):
            out.append(_as_votes(self.text_tree.predict(
                _reversed_context(ids, t, self.depth))))
        return out

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        if self.node_tree is None or self.type_tree is None:
            return {}
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            context = _ancestor_context(view, i, self.depth)
            out[i] = (_as_votes(self.node_tree.predict(context)),
                      _as_votes(self.type_tree.predict(context)))
        return out

    def n_symbolic_parameters(self) -> int:
        return sum(_size(t.root) for t in
                   (self.text_tree, self.node_tree, self.type_tree) if t)


def _as_votes(scores: dict[int, float]) -> Votes:
    """Confidence is the posterior mass CTW put on the symbols it named.

    Nothing invented: the leftover mass genuinely belongs to symbols the model
    has never seen in this context, and handing exactly that share to the shared
    back-off is what the mixture in :mod:`symbolic_ai_models.models.symbolic`
    already does.
    """
    if not scores:
        return ABSTAIN
    mass = sum(scores.values())
    return scores, min(max(mass, 0.0), 0.95)


def _reversed_context(ids: Sequence[int], t: int, depth: int) -> list[int]:
    """The ``depth`` symbols before position ``t + 1``, most recent first."""
    return [ids[i] for i in range(t, max(t - depth, -1), -1)]


def _ancestor_context(view: GraphView, i: int, depth: int) -> list[int]:
    """Slot, then the labels of the ancestors above ``i``, nearest first.

    The slot leads because on a term tree "which argument am I" separates
    contexts that the ancestry alone would merge — ``f(a, b)`` and ``f(b, a)``
    have the same ancestors everywhere.
    """
    out = [-1 - min(view.slot[i], 8)]
    p = view.parent[i]
    while p >= 0 and len(out) < depth:
        label = view.labels[p]
        out.append(label if label is not None else -1)
        p = view.parent[p]
    return out


def _size(node: _Node) -> int:
    return len(node.counts) + sum(_size(c) for c in node.children.values())
