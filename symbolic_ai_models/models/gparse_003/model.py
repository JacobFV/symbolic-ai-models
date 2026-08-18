"""``gparse``: emit the answer by pointing into the parse of the prompt.

The ``-003`` generation, and what makes it a generation rather than one more
model: **the parser is a parameter**. One reasoner is registered against five
different readers of the text surface, and those rows differ in nothing else, so
the spread between them is a measurement of parsing and not a comparison of
models. A sixth row is a declared ablation of the reasoner and says so.

===================  ================================================
``gparse-003``       ``template-002`` — a real, learned graph parser
``gparse-retrieve``  ``retrieve-001`` — the memorisation control
``gparse-flat``      the prefix's words, unstructured: the honest zero
``gparse-none``      no reader at all: the reasoner with nothing to read
``gparse-oracle``    **a ceiling, not a system** — see below
``gparse-nolex``     the ceiling with the two symbol-reading features
                     removed: exactly renaming-invariant, and the only
                     renaming evidence the text surface has
===================  ================================================

``gparse-oracle`` is handed the episode's true term graph, restricted to the
symbols the reader has already read (:mod:`symbolic_ai_models.prefix` carries
the definition and the leak audit). There is no oracle on real text. Its row is
the answer to "how well would this reasoner do if parsing were solved", it is a
**ceiling** everywhere it appears, and it is deliberately a word-suffixed
variant so that ``--models gparse`` can never select it by accident.

What the reasoner does
----------------------

Three steps, each of them causal and each of them checkable.

1. **Find the answer boundary.** Every episode ends its prompt with fixed
   scaffolding, so the token contexts that immediately precede an answer are
   learnable from the training text and recognisable from the prefix alone.
   Before the boundary the model abstains outright, which lands it exactly on
   the back-off: about 98.6% of scored positions are the question and its
   boilerplate, and reproducing boilerplate is not what this experiment is
   about. ``token_*`` will therefore sit near zero lift for every row here and
   the whole story is in ``answer_*``, which is the 1.4% that carries the
   reasoning.

2. **Choose the node.** Every labelled node of the parse is scored by summing
   learned log-odds over its structural features — type, slot, parent type,
   parent label, depth, arity, and how many nodes of the parse repeat its symbol
   or its siblings'. Counted, not optimised: there is no learning rate and no
   stopping rule, so two rows differ in the parse they were given and in nothing
   that could have been tuned differently for one of them. Nothing in the
   feature set is the node's *own* symbol, so the rule is about where the answer
   sits in the term and not about which words are answer-shaped. Two features do
   read the parent's and grandparent's labels; ``gparse-nolex`` drops them and is
   then exactly renaming-invariant, which is how much of the ceiling turns out to
   be vocabulary.

   The repeat counts are what make this more than a slot lookup. In
   ``unification`` the fact is ``parent alice bob`` and the pattern
   ``parent A bob``; the answer is whichever fact argument sits opposite the
   variable, and that is not a fixed slot. It *is* a fixed pattern of repeats,
   which a parse exposes and a token chain does not.

3. **Spell it.** The chosen node's symbol is emitted in whatever casing the
   prompt used for it, one token at a time, re-derived at each position and
   filtered by what has actually been emitted so far. The graph is frozen at the
   boundary, so the answer's own tokens never feed back into the choice of node.

What would refute the design
----------------------------

If ``gparse-oracle`` does not clear the LM answer floor, then a perfect parse
does not rescue the text surface and the bottleneck is the reasoning, not the
parsing. If ``gparse-flat`` matches it, the structure is doing nothing that
tokenisation does not already do, and the same conclusion follows for a
different reason.
"""

from __future__ import annotations

import collections
import math
from typing import Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.term_graph import STRUCTURAL, TermGraph
from symbolic_ai_core.data.tokenizer import SymbolTokenizer, split_words, word_spans
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, RuleBasedModel, TextView, Votes

__all__ = ["GraphParsedLM"]

#: How many tokens of context identify the position just before an answer. Five
#: is enough for the curriculum's scaffolding and short enough to survive the
#: left-truncation `collate_text` applies to a long episode.
BOUNDARY_ORDER = 5

#: How many margin buckets the confidence is calibrated in.
N_BINS = 5

#: Add-alpha on every feature count, so a feature seen once is weak evidence
#: rather than certainty and an unseen one contributes nothing.
ALPHA = 0.5


def _log_odds(positive: collections.Counter, negative: collections.Counter,
              n_pos: int, n_neg: int) -> dict[tuple, float]:
    """``log P(feature | answer) - log P(feature | not answer)``, add-alpha.

    Naive Bayes, counted in one pass. There is no optimiser here on purpose:
    two rows of this table are supposed to differ in the parse they were handed
    and in nothing that could have been tuned differently for one of them.
    """
    if not n_pos or not n_neg:
        return {}
    p_den, n_den = n_pos + 2.0 * ALPHA, n_neg + 2.0 * ALPHA
    out: dict[tuple, float] = {}
    for key in sorted(set(positive) | set(negative)):
        p = (positive.get(key, 0) + ALPHA) / p_den
        q = (negative.get(key, 0) + ALPHA) / n_den
        out[key] = math.log(p) - math.log(q)
    return out


def _norm(text: str) -> tuple[str, ...]:
    """A symbol as words, case-folded — the form two surfaces are compared in."""
    return tuple(p.lower() for p in split_words(text))


def _children(g: TermGraph) -> list[list[int]]:
    kids: list[list[int]] = [[] for _ in range(len(g))]
    for i, p in enumerate(g.parent):
        if 0 <= p < len(g):
            kids[p].append(i)
    return kids


def _multiplicity(g: TermGraph) -> list[int]:
    """How many nodes of this parse carry the same symbol as each node.

    The one feature that makes this reasoner more than a slot lookup. In
    ``unification`` the fact is ``parent alice bob`` and the pattern is
    ``parent A bob``: the answer is the fact's argument whose *sibling* is the
    repeated one, and nothing about slot, type or depth can say which that is,
    because which argument the variable occupies changes between episodes. A
    count of repeats can, it is symbol-free, and it survives renaming — rename
    every symbol and the counts are identical.
    """
    counts: collections.Counter = collections.Counter()
    keys = [_norm(lab) if lab else () for lab in g.labels]
    for k in keys:
        if k:
            counts[k] += 1
    return [min(counts.get(k, 0), 3) for k in keys]


def _features(g: TermGraph, kids: list[list[int]], mult: list[int], i: int, *,
              lexical: bool = True) -> tuple[tuple, ...]:
    """Everything the scorer may know about node ``i``. Never its own symbol.

    A rule allowed to read the node's own label would learn which *words* are
    answer-shaped — the shortcut family ``symbolic_ai_core.shortcuts`` already
    measures, and not a claim about reading the episode. The parent's and
    grandparent's labels are admitted, on the terms the ``ngram`` node contexts
    already admit them: "the second argument of ``parent``" is a fact about the
    term. They are the only lexical keys here, and ``lexical=False`` removes
    them — what is left is exactly invariant under renaming every symbol in the
    episode, and ``gparse-nolex`` is the row that says what that costs.

    These are summed rather than laddered. A ladder answers from the most
    specific context that has support and throws the rest away, which is right
    when the contexts are nested and wrong when they are independent — "an
    ``ident`` in slot 0" and "a symbol that occurs exactly once" are two
    different pieces of evidence about the same node and the model should be
    able to hold both.
    """
    p = g.parent[i]
    inside = 0 <= p < len(g)
    ptype = g.types[p] if inside else "ROOT"
    plabel = g.labels[p] if inside else ""
    slot, depth = min(g.slot[i], 8), min(g.depth[i], 8)
    arity = min(len(kids[i]), 4)
    m = mult[i]
    sibs = [mult[j] for j in (kids[p] if inside else ()) if j != i]
    sm = max(sibs) if sibs else 0
    gp = g.parent[p] if inside else -1
    glabel = g.labels[gp] if 0 <= gp < len(g) else ""
    structural = (
        ("t", g.types[i]),
        ("pt", ptype, slot),
        ("dp", depth, arity),
        ("m", m),
        ("sm", sm),
        ("t.m", g.types[i], m),
        ("m.sm", m, sm),
    )
    if not lexical:
        return structural
    return structural + (
        ("pl", plabel, slot),
        ("pl.m", plabel, m),
        ("path", glabel, plabel),
    )


def _surfaces(label: str, text: str) -> list[tuple[str, int, int, int]]:
    """How the prefix wrote this symbol: ``(spelling, count, first, last)``.

    The graph says ``frank``; the answer is ``Frank``. The casing is a fact
    about the surface, the surface is in the prefix, so it is read from there
    rather than guessed at — and reading it from there keeps the model unable to
    produce a spelling the text has not shown it.

    ``first`` and ``last`` are occurrence indices, because *which* mention a
    spelling came from is the evidence for choosing between them: this
    curriculum writes its options last, in the "Answer with exactly one of"
    line, and mentions the same symbols in the body in whatever case the body
    uses. Which of those the answer copies is learned rather than assumed.
    """
    key = _norm(label)
    if not key:
        return []
    spans = word_spans(text)
    n = len(key)
    seen: dict[str, list[int]] = {}
    hits = 0
    for j in range(len(spans) - n + 1):
        if tuple(spans[j + q][0].lower() for q in range(n)) == key:
            seen.setdefault(text[spans[j][1]:spans[j + n - 1][2]], []).append(hits)
            hits += 1
    return [(s, len(at), at[0], at[-1]) for s, at in seen.items()]


def _shape(surface: str) -> str:
    if surface.islower():
        return "lower"
    if surface.isupper():
        return "upper"
    if surface[:1].isupper() and surface[1:].islower():
        return "title"
    return "other"


def _spelling_features(spelling: str, label: str, count: int, first: int,
                       last: int, total: int) -> tuple[tuple, ...]:
    """Which of a symbol's spellings the answer will copy.

    A second, much smaller counting problem, kept separate from the node scorer
    because it is a different question: the node scorer says *which symbol*, this
    says *how it is written*. Merging them would let the casing of a distractor
    argue about which term slot the question is asking about.
    """
    return (
        ("case", _shape(spelling)),
        ("eq", spelling == label),
        ("last", last == total - 1),
        ("first", first == 0),
        ("n", min(count, 3)),
        ("case.last", _shape(spelling), last == total - 1),
    )


@register("gparse-003",
          doc="Point into a parse of the prompt to emit the answer; parser is a knob.")
class GraphParsedLM(RuleBasedModel):
    """One reasoner, one parser-shaped hole. Fill the hole to move the row."""

    family = "rule-based"
    reads_text_parser = True

    #: The knob the parser comparison turns on. Every row that leaves
    #: :attr:`ablation` empty must differ in this and nothing else.
    default_text_parser = "template-002"

    #: Whether the scorer may key on a parent's or grandparent's *label*. Off is
    #: exactly renaming-invariant; see :func:`_features`. Only a row that names
    #: itself an ablation may move it.
    use_lexical = True

    #: Non-empty when this row changes something other than the parser, and it
    #: says what. Rows with an empty ablation are the parser comparison and are
    #: held to differing in the parser alone.
    ablation = ""

    LEARNED = ("boundary", "weight", "spelling", "bin_confidence",
               "boundary_seen", "answer_reachable")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        #: token contexts that immediately precede an answer
        self.boundary: set[tuple] = set()
        #: structural feature -> its log-odds of belonging to the answer's node
        self.weight: dict[tuple, float] = {}
        #: surface feature -> its log-odds of being the spelling the answer used
        self.spelling: dict[tuple, float] = {}
        #: margin bucket -> held-out accuracy of a prediction made in it
        self.bin_confidence: list[float] = []
        #: how often the boundary rule fired at all, for the write-up
        self.boundary_seen: float = 0.0
        #: how often the answer was a node of the parse at all — the ceiling on
        #: the ceiling, and the number that says whether a miss was the parser
        #: not finding the symbol or the scorer not choosing it
        self.answer_reachable: float = 0.0

    # ---- fitting -----------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        cut = max(int(len(episodes) * 0.8), 1)
        self._learn_boundary(episodes, tok)
        self._learn_weights(episodes[:cut], tok)
        self._calibrate(episodes[cut:] or episodes, tok)

    def _learn_boundary(self, episodes: Sequence[Episode],
                        tok: SymbolTokenizer) -> None:
        """The token contexts an answer follows.

        Read off the training encodings, where the boundary is known exactly,
        and applied at evaluation by looking backwards from the current position
        only. Nothing about it consults the future; it is the same cue any
        language model would use, and it is shared by every row here so it
        cancels out of the parser comparison.
        """
        keys: set[tuple] = set()
        for ep in episodes:
            prefix = tok.encode(ep.prompt + "\n", bos=True)
            if len(prefix) >= BOUNDARY_ORDER:
                keys.add(tuple(prefix[-BOUNDARY_ORDER:]))
        self.boundary = keys

    def _learn_weights(self, episodes: Sequence[Episode],
                       tok: SymbolTokenizer) -> None:
        """Two log-odds tables, counted in one pass over the training parses.

        **Which node.** Every labelled node of every training parse is one
        example, positive iff its symbol is the episode's answer. A feature's
        weight is the log ratio of how often it sat on an answer node to how
        often it sat on any other, add-``ALPHA`` smoothed; a node's score is the
        sum over its features.

        **Which spelling.** A second, much smaller table over the surface forms
        of the symbol that *is* the answer. Kept separate on purpose: merging
        them would let the casing of a distractor argue about which term slot
        the question is asking about.

        One pass because parsing a prefix is the expensive step and a
        full-curriculum fit does it thousands of times. Counting rather than
        fitting, because there is then no learning rate and no stopping rule —
        two rows of this table differ in the parse they were handed and in
        nothing that could have been tuned differently for one of them.
        """
        node_pos: collections.Counter = collections.Counter()
        node_neg: collections.Counter = collections.Counter()
        spell_pos: collections.Counter = collections.Counter()
        spell_neg: collections.Counter = collections.Counter()
        n_pos = n_neg = s_pos = s_neg = 0

        for ep in episodes:
            view, at = self._training_view(ep, tok)
            g = view.graph(at)
            if not len(g):
                continue
            answer = _norm(ep.answer)
            kids, mult = _children(g), _multiplicity(g)
            for i in range(len(g)):
                if not g.labels[i] or g.types[i] in STRUCTURAL:
                    continue
                hit = _norm(g.labels[i]) == answer
                table = node_pos if hit else node_neg
                n_pos, n_neg = n_pos + hit, n_neg + (not hit)
                for key in _features(g, kids, mult, i,
                                     lexical=self.use_lexical):
                    table[key] += 1

            text = view.text(at)
            for label in sorted({lab for lab in g.labels
                                 if lab and _norm(lab) == answer}):
                found = _surfaces(label, text)
                total = sum(c for _, c, _, _ in found)
                for spelling, count, first, last in found:
                    hit = spelling == ep.answer
                    table = spell_pos if hit else spell_neg
                    s_pos, s_neg = s_pos + hit, s_neg + (not hit)
                    for key in _spelling_features(spelling, label, count,
                                                  first, last, total):
                        table[key] += 1

        self.weight = _log_odds(node_pos, node_neg, n_pos, n_neg)
        self.spelling = _log_odds(spell_pos, spell_neg, s_pos, s_neg)

    def _calibrate(self, episodes: Sequence[Episode],
                   tok: SymbolTokenizer) -> None:
        """How often a prediction of a given margin was right, out of sample.

        On episodes the weights were *not* fitted on. The in-sample version is a
        score maximised over the data that produced it, so it overstates — which
        in this harness changes no prediction at all and changes every stated
        probability, the mistake ``_fit_context_prior`` already had to undo once.

        Bucketed by the *margin* between the best node and the runner-up, which
        is the quantity that actually says whether the parse settled the
        question: a parse where two nodes score alike has not answered it,
        however confident either score looks on its own.
        """
        hit: collections.Counter = collections.Counter()
        seen: collections.Counter = collections.Counter()
        fired = reachable = 0
        for ep in episodes:
            view, at = self._training_view(ep, tok)
            g = view.graph(at)
            answer = _norm(ep.answer)
            reachable += any(lab and _norm(lab) == answer for lab in g.labels)
            plan = self._plan(view, at)
            if plan is None:
                continue
            fired += 1
            bucket = plan[1]
            want = tok.encode(ep.answer, eos=True)
            # Scored on the vote the model would actually cast, not on the
            # spelling that happens to rank first: the metric is the argmax of a
            # distribution over *tokens*, and two spellings can agree on their
            # first token while disagreeing as strings.
            votes = self._votes(plan, [], tok)
            seen[bucket] += 1
            if votes and want:
                pick = max(votes.items(), key=lambda kv: (kv[1], -kv[0]))[0]
                hit[bucket] += pick == want[0]
        n = len(episodes) or 1
        self.boundary_seen = fired / n
        self.answer_reachable = reachable / n

        overall = sum(hit.values()) / max(sum(seen.values()), 1)
        # Shrunk towards the global rate, so a bucket that fired three times
        # does not get to claim a confidence of its own.
        self.bin_confidence = [
            min(max((hit.get(b, 0) + 3.0 * overall) / (seen.get(b, 0) + 3.0),
                    0.0), 0.95)
            for b in range(N_BINS)]

    def _training_view(self, ep: Episode,
                       tok: SymbolTokenizer) -> tuple[TextView, int]:
        """The episode as the model will see it, cut at the answer boundary.

        The same encoding ``collate_text`` builds, so a signature counted here
        is a signature that will still resolve at evaluation — the train/test
        mismatch ``training_views`` exists to prevent, one surface over.
        """
        prefix = tok.encode(ep.prompt + "\n", bos=True)
        ids = prefix + tok.encode(ep.answer, eos=True)
        cut = max(len(ids) - self.cfg.max_len, 0)
        ids, at = ids[cut:], len(prefix) - 1 - cut
        truth = ep.graph if self.text_parser.needs_truth else None
        return self.text_parser.begin(ids, tok, truth), max(at, 0)

    # ---- prediction ---------------------------------------------------
    def _plan(self, view: TextView, at: int
              ) -> tuple[dict[str, float], int] | None:
        """``(candidate spellings, margin bucket)`` for the answer, or nothing.

        The parse is taken at the boundary and never afterwards, so the answer's
        own tokens cannot feed back into which node was chosen.

        Nodes sharing a symbol are pooled before the margin is taken. Otherwise
        an episode naming ``bob`` in two places would report a margin of zero
        between two nodes that spell the same answer, and the confidence would
        be lowest exactly where the model is surest.
        """
        g = view.graph(at)
        if not len(g) or not self.weight:
            return None
        kids, mult = _children(g), _multiplicity(g)
        best: dict[tuple, tuple[float, int]] = {}
        for i in range(len(g)):
            if not g.labels[i] or g.types[i] in STRUCTURAL:
                continue
            score = sum(self.weight.get(key, 0.0)
                        for key in _features(g, kids, mult, i,
                                             lexical=self.use_lexical))
            key = _norm(g.labels[i])
            if key not in best or score > best[key][0]:
                best[key] = (score, i)
        if not best:
            return None

        ranked = sorted(best.values(), key=lambda si: (-si[0], si[1]))
        top, node = ranked[0]
        margin = top - ranked[1][0] if len(ranked) > 1 else float(N_BINS)
        bucket = min(int(max(margin, 0.0)), N_BINS - 1)

        label = g.labels[node]
        found = _surfaces(label, view.text(at))
        total = sum(c for _, c, _, _ in found)
        spellings: dict[str, float] = {}
        for text, count, first, last in found:
            score = sum(self.spelling.get(key, 0.0) for key in
                        _spelling_features(text, label, count, first, last, total))
            spellings[text] = math.exp(min(max(score, -20.0), 20.0))
        if not spellings:
            # The parse named a symbol the prefix does not spell. That cannot
            # happen under the oracle -- its restriction forbids it -- but a real
            # parser may invent one, and inventing one is a wrong answer rather
            # than an error.
            spellings = {label: 1.0}
        return spellings, bucket

    @staticmethod
    def _votes(plan: tuple[dict[str, float], int], emitted: Sequence[int],
               tok: SymbolTokenizer) -> collections.Counter:
        """The next token, given the plan and the answer tokens so far.

        Only a spelling consistent with what has actually been emitted may still
        speak. This is the one place the answer's own tokens are read, and
        reading them is what lets the model finish a word rather than restart
        it — the choice of *symbol* was frozen at the boundary and does not move.
        """
        votes: collections.Counter = collections.Counter()
        for spelling, weight in plan[0].items():
            pieces = tok.encode(spelling)
            if list(pieces[:len(emitted)]) != list(emitted):
                continue
            nxt = (pieces[len(emitted)] if len(emitted) < len(pieces)
                   else tok.eos_id)
            votes[int(nxt)] += float(weight)
        return votes

    def text_votes_view(self, view: TextView) -> list[Votes]:
        ids = view.ids
        out: list[Votes] = [ABSTAIN] * len(ids)
        tok = self.tok
        if tok is None or not self.boundary:
            return out

        start, plan = -1, None
        for t in range(len(ids)):
            if t + 1 >= BOUNDARY_ORDER and \
                    tuple(ids[t + 1 - BOUNDARY_ORDER:t + 1]) in self.boundary:
                start, plan = t, self._plan(view, t)
            if plan is None or start < 0:
                continue
            votes = self._votes(plan, ids[start + 1:t + 1], tok)
            confidence = (self.bin_confidence[plan[1]]
                          if plan[1] < len(self.bin_confidence) else 0.0)
            if votes and confidence > 0.0:
                out[t] = (dict(votes), confidence)
        return out

    # ---- what it learned ----------------------------------------------
    def n_symbolic_parameters(self) -> int:
        return (len(self.boundary) + len(self.weight) + len(self.spelling)
                + self.text_parser.n_parameters())

    def render(self) -> str:
        """The features that most say "the answer lives here", as readable text."""
        ranked = sorted(self.weight.items(), key=lambda kv: (-kv[1], kv[0]))
        rows = [f"  {key} {w:+.2f}" for key, w in ranked[:15]]
        return (f"{self.name}: parser={self.text_parser.name} "
                f"boundary contexts={len(self.boundary)} "
                f"fired={self.boundary_seen:.3f} "
                f"answer in parse={self.answer_reachable:.3f} "
                f"confidence by margin={[round(c, 3) for c in self.bin_confidence]}\n"
                + "\n".join(rows))


@register("gparse-oracle",
          doc="CEILING, not a system: gparse on a prefix-restricted oracle parser.")
class GraphParsedOracle(GraphParsedLM):
    """What ``gparse`` would score if parsing were solved. **A ceiling.**

    Not deployable and not a claim about any system: it is handed the episode's
    true term graph, restricted to the symbols already read. Every number from
    this row must be labelled a ceiling wherever it appears. A word-suffixed
    name on purpose — ``--models gparse`` must never resolve to it.
    """

    default_text_parser = "oracle"


@register("gparse-retrieve",
          doc="gparse on retrieve-001: the nearest training prompt's graph.")
class GraphParsedRetrieve(GraphParsedLM):
    """The memorisation control. Whatever a real parser scores above this row is
    the part attributable to reading rather than to recognising the lesson."""

    default_text_parser = "retrieve-001"


@register("gparse-flat",
          doc="gparse on the prefix's words with no structure: the honest zero.")
class GraphParsedFlat(GraphParsedLM):
    """Tokenisation without parsing. A gain attributed to structure has to be a
    gain over this, not over abstention."""

    default_text_parser = "flat"


@register("gparse-none", doc="gparse with no reader at all: the reasoner alone.")
class GraphParsedNone(GraphParsedLM):
    """Nothing to point at, so it abstains and lands on the back-off. It pins
    what the machinery around the parser is worth by itself, which is zero."""

    default_text_parser = "none"


@register("gparse-nolex",
          doc="CEILING, symbol-free: the oracle row with the lexical keys removed.")
class GraphParsedNoLex(GraphParsedLM):
    """The ceiling again, with the two features that read a *symbol* removed.

    Not a parser row — an ablation of the reasoner, and the one that could
    embarrass the rest of this table. ``gparse-oracle``'s heaviest weights are
    parent labels like ``('pl', 'smaller', 1)``, which is a rule about the word
    ``smaller`` rather than about the shape of the term. With ``use_lexical``
    off, every feature is a type, a slot, a depth, an arity or a repeat count,
    so the scorer is **exactly invariant under renaming every symbol in the
    episode** — and the drop from ``gparse-oracle`` is the part of the ceiling
    that was vocabulary rather than structure.

    The repo has no renaming check on the text surface (``_renaming_check``
    scores the *node* task, which every row here abstains on), so this row is
    the only renaming evidence the LM side has.
    """

    default_text_parser = "oracle"
    use_lexical = False
    ablation = "no lexical keys"
