"""One rule set over word classes, weighted per language. The multilingual PCFG.

:mod:`symbolic_ai_parsers.grammar` induces a grammar whose right-hand sides are
literal words; this one induces the same shape of grammar over the symbols
:class:`~symbolic_ai_parsers.classes.ClassMap` assigns, and adds the two things
a *mixture* of languages needs and a monolingual grammar does not.

1. Rule weights conditioned on the situation
--------------------------------------------

One rule set, selectively applied. ``logp(rule | cond)`` is a Dirichlet backoff
onto the global distribution::

    P(r | c) = (count_c(r) + K * P(r)) / (total_c + K)

with ``K =`` :data:`BACKOFF`. Two properties are the reason it is written this
way rather than as an interpolation with a tuned weight:

* a condition never seen in training gives ``count_c = 0`` and ``total_c = 0``,
  so ``P(r | c)`` is **exactly** the global ``P(r)``. Leave-one-language-out
  therefore needs no special case — conditioning degrades to not conditioning;
* a condition with plenty of evidence dominates the prior, so the amount of
  conditioning is set by the data rather than by a knob.

``cond`` is deliberately just a string. The language-conditioned parser passes
the language; the nonsense control passes ``crc32(instance_id) % K`` with the
same cardinality; a future parser could pass the partial parse state. The
grammar does not know or care which, which is what makes the control a control
rather than a different model.

2. An out-of-vocabulary rate estimated for the case that matters
-----------------------------------------------------------------

``Grammar._fit_lexicon`` estimates ``P(ARG | unseen token)`` from training
hapaxes and gets ~0.9, because in a monolingual curriculum a token seen once is
a nonce symbol and nonce symbols are arguments. **In a language the parser was
not fitted on that number is badly wrong**: there, most unseen tokens are the
frame words of the new language, and calling them arguments destroys the parse.

Both cases are real and the parser can tell them apart, because it knows whether
it has seen the condition before. So two rates are estimated, from training data
only, by simulating each case:

``oov_known``
    tokens of a *held-out training seed* that the fitted lexicon has not seen,
    for a language that **is** in the mixture. These are fresh nonce arguments,
    and the rate comes out high.
``oov_novel``
    the same, but with the token's own language excluded from the lexicon —
    which is exactly leave-one-language-out, computed without refitting
    anything, since "unseen once ``L`` is removed" is a property of the token's
    language set.

The probe is the highest training seed of each ``(lesson, language)`` pair, held
out of the counts. That is a *training* split; eval seeds (>= 1,000,000) are
never touched, here or anywhere.

3. Wildcards, and the search bound on them
-------------------------------------------

An unknown token may stand for any class symbol, priced at
``log P(unseen is frame) + log P(class)``. Unbounded that would branch as wide
as the trie at every position, so at most :data:`WILDCARD_BEAM` children are
tried, ordered by the best rule reachable underneath them. It is a search bound
of the same kind as ``MAX_CLAUSE`` and it is stated here rather than discovered
in a profile; ties break on the symbol name, so nothing depends on hash order.
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .classes import ClassMap
from .grammar import MAX_CLAUSE, Rule
from .treebank import ClauseSample, Treebank

__all__ = ["PolyGrammar", "BACKOFF", "WILDCARD_BEAM"]

#: Pseudo-count mass the global distribution lends each condition. Ten, so that
#: a condition needs on the order of ten observations of a rule before it moves
#: away from the pooled estimate. Not swept.
BACKOFF = 10.0

#: How many class symbols an unknown token may be tried as, at one trie state.
WILDCARD_BEAM = 6


class _Node:
    __slots__ = ("kids", "rules", "best", "wild")

    def __init__(self) -> None:
        self.kids: dict[str, "_Node"] = {}
        #: ``(rule index, rule)``. The index is carried because a conditioned
        #: weight is looked up by it and ``Rule`` is shared with
        #: :mod:`symbolic_ai_parsers.grammar` and not extended here.
        self.rules: list[tuple[int, Rule]] = []
        #: best global rule log-probability reachable from here, for the beam
        self.best: float = -math.inf
        #: class-symbol children, best-first. Precomputed: the beam must not
        #: depend on dict iteration order.
        self.wild: list[tuple[str, "_Node"]] = []


@dataclass
class PolyGrammar:
    """Class-based productions, conditioned weights, and an OOV rate per case."""

    rules: list[Rule] = field(default_factory=list)
    classes: ClassMap = field(default_factory=ClassMap)
    #: global log P(rule)
    logp: list[float] = field(default_factory=list)
    #: condition -> {rule index: log P(rule | condition)}
    cond_logp: dict[str, dict[int, float]] = field(default_factory=dict)
    #: condition -> log of the backoff mass, for rules that condition never saw
    cond_backoff: dict[str, float] = field(default_factory=dict)
    arg_logp: dict[str, float] = field(default_factory=dict)
    frame_logp: dict[str, float] = field(default_factory=dict)
    bg_logp: dict[str, float] = field(default_factory=dict)
    unseen_bg_logp: float = math.log(1e-6)
    #: P(ARG | unseen token) when the condition was seen in training
    oov_known: float = 0.9
    #: ... and when it was not. The held-out-language case.
    oov_novel: float = 0.5
    coverage: float = 0.0
    n_samples: int = 0
    n_languages: int = 0
    _root: _Node = field(default_factory=_Node, repr=False)

    # ---- induction -----------------------------------------------------
    #: how many class symbols an unknown token may be tried as, at one state
    beam: int = WILDCARD_BEAM

    @classmethod
    def induce(cls, treebank: Treebank, conds: Sequence[str], *,
               probe: Sequence[bool] | None = None,
               class_mode: str = "classes", condition: bool = True,
               beam: int = WILDCARD_BEAM) -> "PolyGrammar":
        """Fit from a treebank whose samples carry a condition each.

        ``probe`` marks samples used for the out-of-vocabulary estimates. They
        are held out of *that estimate's* vocabulary and nothing else: the rules
        and the lexicon are fitted on everything, because the two rates are
        estimates of a quantity rather than parameters that have to agree with
        the counts. Holding a quarter of the treebank out of the grammar to
        measure one number would be paying for it twice.

        ``condition=False`` fits the global distribution alone, which is the
        unconditioned arm.
        """
        samples = treebank.samples
        langs = list(treebank.languages) or [""] * len(samples)
        keep = [not p for p in probe] if probe is not None else [True] * len(samples)
        fit_s, fit_l, fit_c = list(samples), langs, list(conds)

        cmap = ClassMap.induce(fit_s, fit_l, mode=class_mode)

        counts: collections.Counter = collections.Counter()
        by_cond: dict[str, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for s, c in zip(fit_s, fit_c):
            key = _key(s, cmap)
            if key is None:
                continue
            counts[key] += 1
            if condition:
                by_cond[c][key] += 1

        keys = sorted(counts)
        total = sum(counts.values()) or 1
        rules = [Rule(head=h, node_type=t, rhs=r, arg_slots=sl,
                      count=counts[(h, t, r, sl)],
                      logp=math.log(counts[(h, t, r, sl)] / total))
                 for (h, t, r, sl) in keys]
        index = {k: i for i, k in enumerate(keys)}

        g = cls(rules=rules, classes=cmap, logp=[r.logp for r in rules],
                coverage=treebank.coverage, n_samples=len(fit_s),
                n_languages=len(set(fit_l)))
        g.beam = beam
        for cond, cnt in sorted(by_cond.items()):
            tot = sum(cnt.values())
            denom = tot + BACKOFF
            g.cond_logp[cond] = {
                index[k]: math.log((n + BACKOFF * math.exp(g.logp[index[k]]))
                                   / denom)
                for k, n in sorted(cnt.items())}
            g.cond_backoff[cond] = math.log(BACKOFF / denom)
        g._fit_lexicon(fit_s, fit_l, cmap)
        g._fit_oov(samples, langs, keep, cmap)
        g._build_trie()
        return g

    # ---- the lexicon ---------------------------------------------------
    def _fit_lexicon(self, samples: Sequence[ClauseSample],
                     languages: Sequence[str], cmap: ClassMap) -> None:
        arg: collections.Counter = collections.Counter()
        seen: collections.Counter = collections.Counter()
        for s in samples:
            positions = {i for i, _ in s.arg_slots}
            for i, tok in enumerate(s.tokens):
                seen[tok] += 1
                if i in positions:
                    arg[tok] += 1
        for w in sorted(seen):
            p = min(max((arg[w] + 0.5) / (seen[w] + 1.0), 1e-3), 1 - 1e-3)
            self.arg_logp[w] = math.log(p)
            self.frame_logp[w] = math.log(1 - p)
        total = sum(seen.values())
        denom = total + len(seen) + 1.0
        for w, n in sorted(seen.items()):
            self.bg_logp[w] = math.log((n + 1.0) / denom)
        self.unseen_bg_logp = math.log(1.0 / denom)

    def _fit_oov(self, samples: Sequence[ClauseSample],
                 languages: Sequence[str], keep: Sequence[bool],
                 cmap: ClassMap) -> None:
        """The two out-of-vocabulary argument rates. See the module docstring."""
        tok_langs: dict[str, set[str]] = collections.defaultdict(set)
        for s, lang, k in zip(samples, languages, keep):
            if k:
                for tok in s.tokens:
                    tok_langs[tok].add(lang)

        known_a = known_n = novel_a = novel_n = 0
        for s, lang, k in zip(samples, languages, keep):
            if k:
                continue
            args = {i for i, _ in s.arg_slots}
            for i, tok in enumerate(s.tokens):
                where = tok_langs.get(tok)
                if not where:                       # unseen with every language
                    known_n += 1
                    known_a += i in args
                if not where or where == {lang}:    # unseen once L is removed
                    novel_n += 1
                    novel_a += i in args

        def rate(a: int, n: int, fallback: float) -> float:
            if n < 20:
                return fallback
            return min(max((a + 0.5) / (n + 1.0), 1e-3), 1 - 1e-3)

        self.oov_known = rate(known_a, known_n, 0.9)
        self.oov_novel = rate(novel_a, novel_n, self.oov_known)

    # ---- the automaton --------------------------------------------------
    def _build_trie(self) -> None:
        self._root = _Node()
        for i, r in enumerate(self.rules):
            node = self._root
            for sym in r.rhs:
                node = node.kids.setdefault(sym, _Node())
            node.rules.append((i, r))
        for node in self._walk(self._root):
            node.rules.sort(key=lambda ir: (-ir[1].logp, ir[1].head))
        self._score_trie(self._root)

    def _score_trie(self, node: _Node) -> float:
        best = max((r.logp for _, r in node.rules), default=-math.inf)
        for sym in sorted(node.kids):
            best = max(best, self._score_trie(node.kids[sym]))
        node.best = best
        node.wild = sorted(((s, k) for s, k in node.kids.items()
                            if s.startswith("C:")),
                           key=lambda sk: (-sk[1].best, sk[0]))[:self.beam]
        return best

    def _walk(self, node: _Node) -> Iterable[_Node]:
        stack = [node]
        while stack:
            n = stack.pop()
            yield n
            stack.extend(n.kids[s] for s in sorted(n.kids))

    def background(self, token: str) -> float:
        return self.bg_logp.get(token, self.unseen_bg_logp)

    def rule_logp(self, idx: int, cond: str | None) -> float:
        if cond is None:
            return self.logp[idx]
        table = self.cond_logp.get(cond)
        if table is None:                     # a condition never seen: global
            return self.logp[idx]
        got = table.get(idx)
        if got is not None:
            return got
        return self.cond_backoff[cond] + self.logp[idx]

    def steps(self, node: _Node, token: str, novel: bool
              ) -> list[tuple[_Node, float]]:
        """Every ``(next state, lexical score)`` one token allows from ``node``."""
        out: list[tuple[_Node, float]] = []
        a = self.arg_logp.get(token)
        if a is None:
            rate = self.oov_novel if novel else self.oov_known
            a, f = math.log(rate), math.log(1 - rate)
            nxt = node.kids.get("ARG")
            if nxt is not None:
                out.append((nxt, a))
            for sym, kid in node.wild:
                out.append((kid, f + self.classes.class_logp.get(sym, -20.0)))
            return out
        nxt = node.kids.get("ARG")
        if nxt is not None:
            out.append((nxt, a))
        sym = self.classes.category(token)
        if sym is not None:
            kid = node.kids.get(sym)
            if kid is not None:
                out.append((kid, self.frame_logp[token]))
        return out

    def matches(self, tokens: Sequence[str], start: int, cond: str | None,
                novel: bool) -> list[tuple[int, Rule, float]]:
        """``(end, rule, rule + lexical score)`` for every RHS covering
        ``tokens[start:]``. The rule weight is folded in here because it is the
        one term that depends on the condition."""
        out: list[tuple[int, Rule, float]] = []
        stack: list[tuple[_Node, int, float]] = [(self._root, start, 0.0)]
        limit = min(len(tokens), start + MAX_CLAUSE)
        while stack:
            node, i, score = stack.pop()
            for idx, r in node.rules:
                out.append((i, r, score + self.rule_logp(idx, cond)))
            if i >= limit:
                continue
            for kid, sc in self.steps(node, tokens[i], novel):
                stack.append((kid, i + 1, score + sc))
        return out

    @property
    def root(self) -> _Node:
        return self._root

    def n_parameters(self) -> int:
        return (len(self.rules) + len(self.arg_logp) + len(self.classes.of)
                + sum(len(v) for v in self.cond_logp.values()))


def _key(s: ClauseSample, cmap: ClassMap):
    """The production ``s`` instantiates, over class symbols. ``None`` if a
    frame token has no category, which cannot happen on the fitting pass."""
    args = dict(s.arg_slots)
    rhs = []
    for i, tok in enumerate(s.tokens):
        if i in args:
            rhs.append("ARG")
            continue
        sym = cmap.category(tok)
        if sym is None:
            return None
        rhs.append(sym)
    if len(rhs) > MAX_CLAUSE:
        return None
    slots = tuple(args[i] for i in sorted(args))
    return (s.head, s.node_type, tuple(rhs), slots)
