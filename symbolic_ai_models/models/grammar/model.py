"""A parser that was **learned**, not written down.

Every other parser in this repo is hand-built. ``syllogism`` knows four
categorical forms because somebody typed them out; ``symbolalg`` splits clauses
on a regex; ``evidence`` has a stopword list and eight query-type patterns. That
is a defensible way to build a symbolic system and it is how those systems were
originally built — but it means their grammar is an assumption, not a finding,
and on a corpus rendered in Swahili they are simply blind.

This model writes down nothing. It induces its grammar from the training text
by the oldest idea in distributional linguistics: **things that appear in the
same contexts are the same kind of thing** (Harris, 1954; and its modern
descendants — ADIOS, alignment-based learning, Bayesian model merging).

Two stages, both learned:

* **Equivalence classes.** For every context ``(left, right)`` seen with several
  different fillers, those fillers are evidence of a class. Pairs are counted
  across the corpus and merged by union-find once they share enough contexts.
  What comes out on this data are the classes the curriculum's generator
  actually used — colours in one, shapes in another, object names in a third —
  recovered without being told that colours exist.
* **Patterns.** Once tokens are classes, the frequent class digrams are promoted
  to nonterminals, repeatedly, in the manner of SEQUITUR: a grammar rule is a
  sequence that earns its own name by recurring.

Prediction then happens at the level of the class rather than the token, which
is the whole point of having induced one. A context never observed with a
particular word can still be resolved if the *class* was observed there — so
where ``ngram`` and ``ctw`` must back off to a shorter context, this backs off
to a more abstract one.

``render()`` prints the induced grammar. On the curriculum it is short enough to
read, which is the check that matters: if the classes are nonsense, you can see
that they are nonsense.
"""

from __future__ import annotations

import collections
import itertools
from typing import Sequence

from ...data.curriculum import Episode
from ...data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import (ABSTAIN, GraphView, RuleBasedModel, Votes,
                        prune_tables)

__all__ = ["GrammarModel"]


class _Classes:
    """Union-find over symbols, merged by shared contexts."""

    def __init__(self) -> None:
        self.parent: dict[int, int] = {}
        self.members: dict[int, list[int]] = {}

    def find(self, x: int) -> int:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def finalise(self) -> None:
        self.members = collections.defaultdict(list)
        for symbol in list(self.parent):
            self.members[self.find(symbol)].append(symbol)
        self.members = dict(self.members)

    def of(self, symbol: int) -> int:
        """The class of a symbol; itself if it was never merged."""
        return self.find(symbol) if symbol in self.parent else symbol

    def size(self) -> int:
        return sum(1 for m in self.members.values() if len(m) > 1)


@register("grammar", doc="Distributional grammar induction: classes and patterns, learned not written.")
class GrammarModel(RuleBasedModel):
    """Induce the equivalence classes, then predict at the level of the class."""

    LEARNED = ("classes", "class_next", "token_next", "class_members",
               "patterns", "node_classes", "node_next", "node_types",
               "min_shared")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.min_shared = int(cfg.get("min_shared", 3))
        self.max_fillers = int(cfg.get("max_fillers", 10))
        self.order = int(cfg.get("order", 2))
        self.n_patterns = int(cfg.get("n_patterns", 24))
        self.max_entries = int(cfg.get("max_entries", 400_000))
        self.classes = _Classes()
        self.node_classes = _Classes()
        self.class_members: dict[int, collections.Counter] = {}
        self.class_next: dict[tuple, collections.Counter] = {}
        self.token_next: dict[tuple, collections.Counter] = {}
        self.node_next: dict[tuple, collections.Counter] = {}
        self.node_types: dict[tuple, collections.Counter] = {}
        self.patterns: list[tuple] = []

    # ---- induction -----------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        streams = [tok.encode(ep.text, bos=True, eos=True) for ep in episodes]
        self.classes = self._induce_classes(
            self._context_fillers(streams))
        self._count_transitions(streams)
        self.patterns = self._induce_patterns(streams)
        self._learn_graph(episodes, tok)
        for name in ("token_next", "class_next", "node_next", "node_types"):
            setattr(self, name, prune_tables(getattr(self, name),
                                             max_entries=self.max_entries))

    @staticmethod
    def _context_fillers(streams: Sequence[Sequence[int]]
                         ) -> dict[tuple, set[int]]:
        """``(left, right) -> the symbols seen between them``.

        This is the entire empirical basis for the classes: nothing about what a
        symbol *means*, only where it is allowed to stand.
        """
        fillers: dict[tuple, set[int]] = collections.defaultdict(set)
        for ids in streams:
            for i in range(1, len(ids) - 1):
                fillers[(ids[i - 1], ids[i + 1])].add(ids[i])
        return fillers

    def _induce_classes(self, fillers: dict[tuple, set[int]]) -> _Classes:
        """Merge symbols that share ``min_shared`` contexts.

        Contexts with very many fillers are skipped. A slot that accepts forty
        different words is not evidence of a class, it is evidence of a common
        frame, and letting it merge would collapse the whole vocabulary into one
        class through a single promiscuous context.
        """
        shared: collections.Counter = collections.Counter()
        for symbols in fillers.values():
            if 2 <= len(symbols) <= self.max_fillers:
                for a, b in itertools.combinations(sorted(symbols), 2):
                    shared[(a, b)] += 1

        classes = _Classes()
        for (a, b), count in shared.items():
            if count >= self.min_shared:
                classes.union(a, b)
        classes.finalise()
        return classes

    def _count_transitions(self, streams: Sequence[Sequence[int]]) -> None:
        """Two n-gram tables: one over tokens, one over their classes."""
        self.token_next = collections.defaultdict(collections.Counter)
        self.class_next = collections.defaultdict(collections.Counter)
        self.class_members = collections.defaultdict(collections.Counter)
        for ids in streams:
            classes = [self.classes.of(i) for i in ids]
            for t in range(len(ids) - 1):
                self.class_members[classes[t]][ids[t]] += 1
                for k in range(1, self.order + 1):
                    if t + 1 >= k:
                        self.token_next[tuple(ids[t + 1 - k:t + 1])][ids[t + 1]] += 1
                        self.class_next[tuple(classes[t + 1 - k:t + 1])][
                            classes[t + 1]] += 1
            if ids:
                self.class_members[classes[-1]][ids[-1]] += 1
        self.token_next = dict(self.token_next)
        self.class_next = dict(self.class_next)
        self.class_members = dict(self.class_members)

    def _induce_patterns(self, streams: Sequence[Sequence[int]]) -> list[tuple]:
        """Promote frequent class digrams to nonterminals, SEQUITUR-fashion.

        Reported rather than used for prediction: the classes carry the
        generalisation, and the patterns are what make the induced grammar
        legible when you print it.
        """
        sequences = [[self.classes.of(i) for i in ids] for ids in streams]
        patterns: list[tuple] = []
        for _ in range(self.n_patterns):
            digrams: collections.Counter = collections.Counter()
            for seq in sequences:
                for a, b in zip(seq, seq[1:]):
                    digrams[(a, b)] += 1
            if not digrams:
                break
            (a, b), count = digrams.most_common(1)[0]
            if count < 4:
                break
            name = -(len(patterns) + 2)          # negative ids are nonterminals
            patterns.append((name, a, b))
            sequences = [_replace(seq, a, b, name) for seq in sequences]
        return patterns

    def _learn_graph(self, episodes: Sequence[Episode],
                     tok: SymbolTokenizer) -> None:
        """The same induction on the tree: a node's context is where it sits."""
        fillers: dict[tuple, set[int]] = collections.defaultdict(set)
        self.node_next = collections.defaultdict(collections.Counter)
        self.node_types = collections.defaultdict(collections.Counter)
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            for i in range(len(view)):
                label = view.labels[i]
                if label is not None:
                    fillers[_node_context(view, i)].add(label)
            for node, (label_id, type_id) in targets.items():
                context = _node_context(view, node)
                if label_id >= 0:
                    self.node_next[context][label_id] += 1
                if type_id >= 0:
                    self.node_types[context][type_id] += 1
        self.node_classes = self._induce_classes(fillers)
        self.node_next = dict(self.node_next)
        self.node_types = dict(self.node_types)

    # ---- prediction ----------------------------------------------------
    def text_votes(self, ids: Sequence[int]) -> list[Votes]:
        out: list[Votes] = []
        for t in range(len(ids)):
            votes = self._predict(ids, t)
            out.append(votes)
        return out

    def _predict(self, ids: Sequence[int], t: int) -> Votes:
        """Concrete context first; then the same context read as classes.

        The class table is the point of the whole model: it is consulted exactly
        when the literal context was never observed, and it answers by saying
        what *kind* of thing goes here and then which members that kind has.
        """
        for k in range(min(self.order, t + 1), 0, -1):
            table = self.token_next.get(tuple(ids[t + 1 - k:t + 1]))
            if table:
                mass = sum(table.values())
                return dict(table), min(mass / (mass + 4.0), 0.9)

        for k in range(min(self.order, t + 1), 0, -1):
            key = tuple(self.classes.of(i) for i in ids[t + 1 - k:t + 1])
            table = self.class_next.get(key)
            if not table:
                continue
            votes: collections.Counter = collections.Counter()
            for class_id, count in table.items():
                members = self.class_members.get(class_id)
                if not members:
                    continue
                total = sum(members.values())
                for symbol, seen in members.items():
                    votes[symbol] += count * seen / total
            if votes:
                mass = sum(table.values())
                # Weaker than a literal hit, because a class prediction commits
                # to the kind and guesses the member.
                return dict(votes), min(0.6 * mass / (mass + 4.0), 0.7)
        return ABSTAIN

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            context = _node_context(view, i)
            out[i] = (_table_vote(self.node_next.get(context)),
                      _table_vote(self.node_types.get(context)))
        return out

    # ---- reporting ------------------------------------------------------
    def n_symbolic_parameters(self) -> int:
        return (self.classes.size() + self.node_classes.size()
                + len(self.patterns)
                + sum(len(v) for v in self.class_next.values()))

    def render(self) -> str:
        """The induced grammar. If the classes are nonsense you can see it."""
        assert self.tok is not None
        lines = [f"=== {self.classes.size()} induced classes (text) ==="]
        groups = sorted((m for m in self.classes.members.values() if len(m) > 1),
                        key=len, reverse=True)[:20]
        for members in groups:
            words = [repr(self.tok.itos[s]) for s in members[:10]]
            more = "" if len(members) <= 10 else f" ... (+{len(members) - 10})"
            lines.append("  { " + ", ".join(words) + more + " }")
        lines.append(f"=== {len(self.patterns)} promoted patterns ===")
        for name, a, b in self.patterns[:12]:
            lines.append(f"  N{-name} -> {self._name(a)} {self._name(b)}")
        lines.append(f"=== {self.node_classes.size()} induced classes (graph) ===")
        groups = sorted((m for m in self.node_classes.members.values() if len(m) > 1),
                        key=len, reverse=True)[:10]
        for members in groups:
            lines.append("  { " + ", ".join(repr(self.tok.itos[s])
                                            for s in members[:10]) + " }")
        return "\n".join(lines)

    def _name(self, symbol: int) -> str:
        assert self.tok is not None
        if symbol < 0:
            return f"N{-symbol}"
        members = self.classes.members.get(symbol)
        if members and len(members) > 1:
            return f"C{symbol}"
        return repr(self.tok.itos[symbol]) if symbol < len(self.tok.itos) else str(symbol)


def _table_vote(table: collections.Counter | None) -> Votes:
    if not table:
        return ABSTAIN
    mass = sum(table.values())
    return dict(table), min(mass / (mass + 4.0), 0.88)


def _node_context(view: GraphView, i: int) -> tuple:
    """A node's distributional context: what stands around it in the tree."""
    p = view.parent[i]
    return ((view.labels[p] if p >= 0 else None),
            min(view.slot[i], 6),
            (view.types[p] or "mask") if p >= 0 else "ROOT")


def _replace(seq: Sequence[int], a: int, b: int, name: int) -> list[int]:
    out: list[int] = []
    i = 0
    while i < len(seq):
        if i + 1 < len(seq) and seq[i] == a and seq[i + 1] == b:
            out.append(name)
            i += 2
        else:
            out.append(seq[i])
            i += 1
    return out
