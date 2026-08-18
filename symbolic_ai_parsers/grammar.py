"""A PCFG induced from the treebank, and the trie that is its LR(0) automaton.

One grammar, three parsers. ``cky-001``, ``lr-001`` and ``shiftreduce-001``
differ in *how they search*, not in what they know, which is the only way the
comparison between a chart, a deterministic table and a learned oracle means
anything.

The grammar
-----------

Terminals are tokens. There are exactly two preterminals::

    ARG     this token is an argument -- a symbol to be copied into the graph
    <word>  this token is itself, part of the template

and a production is a flat sequence of them::

    PRED[outranks] -> ARG "outranks" ARG        slots (0, 1)
    PRED[event]    -> "event" ":" ARG "," ARG   slots (0, 1)

The slot tuple is carried separately from the surface order and this is the one
piece of linguistics in the file. Turkish renders ``dave erin outranks`` — the
arguments keep their slots and the predicate moves to the end. A grammar that
folded surface position into slot would learn that as a *different predicate*
rather than as a different word order, and would need one rule per language per
predicate. Kept apart, it is one extra production over the same head.

The lexicon
-----------

``P(ARG | token)`` from training counts, so ``outranks`` is almost never an
argument and ``dave`` almost always is. The number that matters is the one for a
token never seen in training, which in this curriculum is a nonce symbol and is
therefore nearly always an argument. It is **not** written down as a constant:
it is estimated as the argument rate among training hapaxes, which is the
standard Good-Turing move and costs nothing.

The trie
--------

Productions are flat, so the LR(0) item-set automaton of this grammar *is* the
trie of right-hand sides: a state is a set of items sharing a prefix, and the
goto function is "read one more category". Building it as a trie is not an
approximation of LR — it is LR, for a grammar with no nonterminal on any
right-hand side. ``cky-001`` walks it as a chart, ``lr-001`` walks it
deterministically with the classic shift-preferring conflict resolution, and
``shiftreduce-001`` walks it under a learned oracle. Same automaton.
"""

from __future__ import annotations

import collections
import math
import re
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from symbolic_ai_core.data.term_graph import TermGraph

from .treebank import ClauseSample, Segment, Treebank

__all__ = ["Rule", "Grammar", "Derivation", "assemble", "slug"]

_DIGITS = re.compile(r"^\d+$")
#: A clause longer than this is not searched. Every rule ever induced is far
#: shorter, and the cap stops one pathological line costing an evaluation.
MAX_CLAUSE = 24


def slug(text: str, words) -> str:
    parts = words(text)
    return "_".join(parts[:6]).lower()


@dataclass(frozen=True)
class Rule:
    """One production, with the graph slots its ``ARG`` positions fill."""

    head: str
    node_type: str
    rhs: tuple[str, ...]
    arg_slots: tuple[int, ...]
    count: int = 0
    logp: float = 0.0

    def __len__(self) -> int:
        return len(self.rhs)


@dataclass
class Derivation:
    """A clause the parser committed to: which rule, over which tokens."""

    start: int
    end: int
    rule: Rule
    score: float = 0.0


class _Trie:
    __slots__ = ("kids", "rules")

    def __init__(self) -> None:
        self.kids: dict[str, "_Trie"] = {}
        self.rules: list[Rule] = []


@dataclass
class Grammar:
    """The induced PCFG plus its LR(0) trie. Fitted once, shared by three parsers."""

    rules: list[Rule] = field(default_factory=list)
    arg_logp: dict[str, float] = field(default_factory=dict)
    frame_logp: dict[str, float] = field(default_factory=dict)
    #: log P(token) under a background unigram. A token no clause claims is
    #: generated from this instead, which is what lets a partial parse be scored
    #: against a full one on the same scale -- and means the parsers carry no
    #: hand-set "skip penalty". A constant there would be a free parameter
    #: sitting on the result of every classical parser at once.
    bg_logp: dict[str, float] = field(default_factory=dict)
    unseen_bg_logp: float = math.log(1e-6)
    unseen_arg_logp: float = math.log(0.9)
    unseen_frame_logp: float = math.log(0.1)
    coverage: float = 0.0
    n_samples: int = 0
    _root: _Trie = field(default_factory=_Trie, repr=False)

    # ---- induction -----------------------------------------------------
    @classmethod
    def induce(cls, treebank: Treebank, *, min_count: int = 1) -> "Grammar":
        counts: collections.Counter = collections.Counter()
        for s in treebank.samples:
            if len(s.tokens) > MAX_CLAUSE:
                continue
            args = dict(s.arg_slots)
            slots = tuple(args[i] for i in sorted(args))
            counts[(s.head, s.node_type, s.categories(), slots)] += 1

        total = sum(counts.values()) or 1
        rules = [Rule(head=h, node_type=t, rhs=r, arg_slots=sl, count=c,
                      logp=math.log(c / total))
                 for (h, t, r, sl), c in counts.items() if c >= min_count]

        g = cls(rules=rules, coverage=treebank.coverage,
                n_samples=len(treebank.samples))
        g._fit_lexicon(treebank.samples)
        g._build_trie()
        return g

    def _fit_lexicon(self, samples: Sequence[ClauseSample]) -> None:
        arg: collections.Counter = collections.Counter()
        seen: collections.Counter = collections.Counter()
        for s in samples:
            positions = dict(s.arg_slots)
            for i, tok in enumerate(s.tokens):
                seen[tok] += 1
                if i in positions:
                    arg[tok] += 1

        # The unseen-token rate, estimated on hapaxes rather than written down:
        # a token seen once in training is the best available stand-in for one
        # seen zero times, and in this curriculum both are usually nonce
        # symbols. Good-Turing's idea, at its cheapest.
        hapax = [w for w, c in seen.items() if c == 1]
        rate = ((sum(arg[w] for w in hapax) + 0.5) / (len(hapax) + 1.0)
                if hapax else 0.9)
        rate = min(max(rate, 1e-3), 1 - 1e-3)
        self.unseen_arg_logp = math.log(rate)
        self.unseen_frame_logp = math.log(1 - rate)

        for w, n in seen.items():
            p = (arg[w] + 0.5) / (n + 1.0)
            p = min(max(p, 1e-3), 1 - 1e-3)
            self.arg_logp[w] = math.log(p)
            self.frame_logp[w] = math.log(1 - p)

        total = sum(seen.values())
        denom = total + len(seen) + 1.0
        for w, n in seen.items():
            self.bg_logp[w] = math.log((n + 1.0) / denom)
        self.unseen_bg_logp = math.log(1.0 / denom)

    def background(self, token: str) -> float:
        return self.bg_logp.get(token, self.unseen_bg_logp)

    def _build_trie(self) -> None:
        self._root = _Trie()
        for r in self.rules:
            node = self._root
            for cat in r.rhs:
                node = node.kids.setdefault(cat, _Trie())
            node.rules.append(r)
        for node in self._walk(self._root):
            node.rules.sort(key=lambda r: (-r.logp, r.head))

    def _walk(self, node: _Trie) -> Iterable[_Trie]:
        stack = [node]
        while stack:
            n = stack.pop()
            yield n
            stack.extend(n.kids.values())

    # ---- the lexicon, as scores ---------------------------------------
    def cat_scores(self, token: str) -> list[tuple[str, float]]:
        """``[(category, log probability)]`` for one token. At most two."""
        a = self.arg_logp.get(token, self.unseen_arg_logp)
        f = self.frame_logp.get(token, self.unseen_frame_logp)
        return [("ARG", a), (token, f)]

    # ---- the automaton, walked as a chart ------------------------------
    def matches(self, tokens: Sequence[str], start: int
                ) -> list[tuple[int, Rule, float]]:
        """Every ``(end, rule, lexical score)`` whose RHS covers ``tokens[start:end]``.

        A depth-first walk of the trie, taking both categories at every token.
        Bounded by :data:`MAX_CLAUSE` and by the trie's own depth, so the
        branching cannot run away on a long line.
        """
        out: list[tuple[int, Rule, float]] = []
        stack: list[tuple[_Trie, int, float]] = [(self._root, start, 0.0)]
        limit = min(len(tokens), start + MAX_CLAUSE)
        while stack:
            node, i, score = stack.pop()
            for r in node.rules:
                out.append((i, r, score))
            if i >= limit:
                continue
            for cat, sc in self.cat_scores(tokens[i]):
                nxt = node.kids.get(cat)
                if nxt is not None:
                    stack.append((nxt, i + 1, score + sc))
        return out

    def step(self, node: _Trie | None, token: str) -> list[tuple[_Trie, str, float]]:
        """One shift from a trie state. Used by the deterministic parsers."""
        node = self._root if node is None else node
        out = []
        for cat, sc in self.cat_scores(token):
            nxt = node.kids.get(cat)
            if nxt is not None:
                out.append((nxt, cat, sc))
        return out

    @property
    def root(self) -> _Trie:
        return self._root

    def n_parameters(self) -> int:
        return len(self.rules) + len(self.arg_logp)


def clause_graph(g: TermGraph, parent: int, slot: int, rule: Rule,
                 tokens: Sequence[str], start: int) -> None:
    """Write one derived clause into ``g`` as a predicate and its arguments."""
    node = g.add(rule.head, rule.node_type, parent, slot)
    args = [(rule.arg_slots[k], tokens[start + i])
            for k, i in enumerate(j for j, c in enumerate(rule.rhs) if c == "ARG")
            if k < len(rule.arg_slots)]
    for graph_slot, tok in sorted(args):
        g.add(tok.lower(), "num" if _DIGITS.match(tok) else "ident",
              node, graph_slot)


def assemble(blocks_of: Sequence[tuple[str, Sequence[Segment]]],
             parsed: dict[int, list[tuple[Sequence[str], list[Derivation]]]],
             field_label) -> TermGraph:
    """Build the record scaffolding and hang the parsed clauses under it.

    The scaffolding is **not** parsed and is not claimed to be: the treebank
    only ever recovered clause-level spans, so record, field and list come from
    block layout exactly as ``bracket-001`` builds them. Everything below the
    list is the grammar's work. Where the ceiling on these parsers comes from is
    therefore visible in the code rather than inferred from the scores.
    """
    g = TermGraph()
    root = g.add("", "record", -1, 0)
    for b, (header, _segs) in enumerate(blocks_of):
        derivs = parsed.get(b) or []
        if not derivs:
            continue
        f = g.add(field_label(header), "field", root, b)
        lst = g.add("", "list", f, 0)
        k = 0
        for tokens, ds in derivs:
            for d in ds:
                clause_graph(g, lst, k, d.rule, tokens, d.start)
                k += 1
    return g
