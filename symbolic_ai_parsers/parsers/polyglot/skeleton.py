"""One multilingual parser, and the six controls that make it readable.

Every arm in the ``polycky`` family is this class with four declarative knobs
set differently, so that the sweep prints them against the same floors and each
difference is attributable to exactly one change. The knobs, and what each
control is for:

============  ==========================  ==========================
knob          values                      the question it isolates
============  ==========================  ==========================
``segment``   ``v2`` / ``v1``             is the cross-language number a fact
                                          about parsing or about
                                          ``split_words``?
``abstract``  ``classes`` / ``one`` /     does abstracting the frame help, and
              ``literal``                 do the class *identities* matter?
``condition`` ``language`` / ``crc`` /    does conditioning on language beat a
              ``none``                    same-cardinality nonsense split?
``oov``       ``lolo`` / ``hapax``        how much of it is the unseen-token
                                          argument rate, a harness constant?
============  ==========================  ==========================

The decode is ``cky-001``'s: the productions are flat, so the chart collapses to
a linear Viterbi over start positions, with a fitted background unigram rather
than a chosen skip penalty. That is deliberate — the search is held fixed at the
one this package already measured, so nothing in the table is a search
difference wearing a grammar's name.

The conditioning value at parse time
------------------------------------

``Parser.parse`` takes a string and nothing else, and it stays that way:
``parse(text)`` uses the global rule weights, which is what any caller outside
this experiment gets. :meth:`parse_in` takes the situation as a second argument,
and the polyglot protocol supplies it from episode *metadata* — the language and
the instance id — never from the graph.

The language label is therefore an **oracle**, and this repo's standing caveat
applies: a supplied signal must be measured as its own head with its own floor
or a subproblem has been assumed away rather than factored out.
:func:`symbolic_ai_parsers.polyglot.language_id_head` does that, on
``shape_features``, against a 1/K floor, and the number is printed in the same
report.
"""

from __future__ import annotations

import zlib
from typing import Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.term_graph import TermGraph

from ...base import Parser
from ...features import words_of
from ...grammar import Derivation, assemble
from ...polygrammar import WILDCARD_BEAM, PolyGrammar
from ...segment import words as words_v2
from ...treebank import Treebank, blocks, segments

__all__ = ["PolyParser"]


def _field_label(header: str) -> str:
    return "_".join(words_of(header)[:6]).lower()


class PolyParser(Parser):
    """Chart parse over one class-based rule set, weighted by the situation."""

    #: ``v2`` script-aware, ``v1`` the repo's shared splitter
    segment: str = "v2"
    #: ``classes`` / ``one`` / ``literal`` -- see :mod:`symbolic_ai_parsers.classes`
    abstract: str = "classes"
    #: ``language`` / ``crc`` / ``none``
    condition: str = "none"
    #: ``lolo`` held-out-language estimate, or ``hapax`` as ``cky-001`` has it
    oov: str = "lolo"
    #: how many class symbols an unknown token may be tried as. A *search*
    #: bound, and it is a knob because the one-class control has exactly one
    #: class and therefore no beam at all — so a beam too tight would starve
    #: the full induction and look like a finding about class identities.
    beam: int = WILDCARD_BEAM

    def __init__(self) -> None:
        self.grammar = PolyGrammar()
        self.treebank = Treebank()
        self.known_conds: frozenset[str] = frozenset()
        self.n_train_languages = 0

    # ---- the situation --------------------------------------------------
    def cond_of(self, language: str, instance_id: str) -> str | None:
        """The conditioning value, from episode metadata only.

        ``crc`` is the control: ``crc32(instance_id)`` modulo the number of
        training languages partitions the *same* episodes into the *same* number
        of buckets of the same expected size, and carries no information. If
        conditioning on language does not beat it, the gain was cardinality.
        """
        if self.condition == "language":
            return language
        if self.condition == "crc":
            k = max(self.n_train_languages, 1)
            return f"crc{zlib.crc32(instance_id.encode('utf-8')) % k}"
        return None

    # ---- fitting --------------------------------------------------------
    def fit(self, episodes: Sequence[Episode]) -> None:
        words = words_v2 if self.segment == "v2" else words_of
        eps = list(episodes)
        probe_ids = _probe_ids(eps)
        self.n_train_languages = len({ep.language for ep in eps})

        tb = Treebank()
        conds: list[str] = []
        probe: list[bool] = []
        for ep in eps:
            one = Treebank.build([ep], words)
            tb.extend(one)
            c = self.cond_of(ep.language, ep.instance_id) or ""
            conds.extend([c] * len(one.samples))
            probe.extend([ep.instance_id in probe_ids] * len(one.samples))

        self.treebank = tb
        self.grammar = PolyGrammar.induce(
            tb, conds, probe=probe if self.oov == "lolo" else None,
            class_mode=self.abstract, condition=self.condition != "none",
            beam=self.beam)
        if self.oov == "hapax":
            self.grammar.oov_known = self.grammar.oov_novel = _hapax_rate(tb)
        self.known_conds = frozenset(self.grammar.cond_logp)

    # ---- parsing --------------------------------------------------------
    def parse(self, text: str) -> TermGraph:
        return self.parse_in(text, None)

    def parse_in(self, text: str, cond: str | None) -> TermGraph:
        g = self.grammar
        if not g.rules:
            return TermGraph()
        novel = self.condition != "none" and (cond is None
                                              or cond not in self.known_conds)
        words = words_v2 if self.segment == "v2" else words_of
        blks = blocks(text)
        by_block: dict[int, list[tuple[Sequence[str], list[Derivation]]]] = {}
        for seg in segments(text, words):
            ds = self.decode(seg.tokens, cond, novel)
            if ds:
                by_block.setdefault(seg.block, []).append((seg.tokens, ds))
        return assemble([(h, ()) for h, _ in blks], by_block, _field_label)

    def parse_episode(self, ep: Episode) -> TermGraph:
        return self.parse_in(ep.prompt, self.cond_of(ep.language, ep.instance_id))

    def decode(self, tokens: Sequence[str], cond: str | None, novel: bool
               ) -> list[Derivation]:
        """``cky-001``'s Viterbi, with the conditioned rule weight folded in."""
        n = len(tokens)
        if not n:
            return []
        g = self.grammar
        best = [0.0] * (n + 1)
        back: list[tuple[int, object] | None] = [None] * (n + 1)
        for i in range(n - 1, -1, -1):
            score = g.background(tokens[i]) + best[i + 1]
            choice: tuple[int, object] | None = None
            for end, rule, sc in g.matches(tokens, i, cond, novel):
                if end <= i:
                    continue
                cand = sc + best[end]
                if cand > score:
                    score, choice = cand, (end, rule)
            best[i], back[i] = score, choice

        out: list[Derivation] = []
        i = 0
        while i < n:
            step = back[i]
            if step is None:
                i += 1
                continue
            end, rule = step
            out.append(Derivation(start=i, end=int(end), rule=rule))  # type: ignore[arg-type]
            i = int(end)
        return out

    def n_parameters(self) -> int:
        return self.grammar.n_parameters()

    def describe(self) -> str:
        g = self.grammar
        return (f"{self.name}: seg={self.segment} abstract={self.abstract} "
                f"cond={self.condition} oov={self.oov} beam={self.beam}; "
                f"{len(g.rules):,} rules, "
                f"{g.classes.n_classes()} classes over {g.n_languages} languages, "
                f"{self.treebank.coverage:.0%} clause coverage, "
                f"oov_arg known={g.oov_known:.2f} novel={g.oov_novel:.2f}")


def _probe_ids(episodes: Sequence[Episode]) -> frozenset[str]:
    """The highest training seed of each ``(lesson, language)``, held out.

    A *training* split, used only to estimate the two out-of-vocabulary rates.
    Its point is that a probe episode's nonce symbols were not in the counts, so
    "unseen token" means at fit time what it will mean at eval time.
    """
    top: dict[tuple[str, str], tuple[int, str]] = {}
    for ep in episodes:
        key = (ep.lesson_id, ep.language)
        if key not in top or ep.seed > top[key][0]:
            top[key] = (ep.seed, ep.instance_id)
    return frozenset(v[1] for v in top.values()) if len(top) < len(episodes) \
        else frozenset()


def _hapax_rate(tb: Treebank) -> float:
    """``Grammar._fit_lexicon``'s estimate, kept so one arm can carry it."""
    import collections

    arg: collections.Counter = collections.Counter()
    seen: collections.Counter = collections.Counter()
    for s in tb.samples:
        positions = {i for i, _ in s.arg_slots}
        for i, tok in enumerate(s.tokens):
            seen[tok] += 1
            if i in positions:
                arg[tok] += 1
    hapax = sorted(w for w, c in seen.items() if c == 1)
    if not hapax:
        return 0.9
    rate = (sum(arg[w] for w in hapax) + 0.5) / (len(hapax) + 1.0)
    return min(max(rate, 1e-3), 1 - 1e-3)
