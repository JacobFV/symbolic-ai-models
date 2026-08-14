"""Reading the text surface through a parser, one prefix at a time.

The text task hands a model a flat chain of tokens: ``collate_text`` sets
``rel=None``, so there is no structure at all on the surface where language
lives, while ``collate_graph`` hands the same model the true term graph. Every
model that scores well in this repo scores on the graph.

That leaves the interesting question unanswered — **is the text-surface failure a
parsing failure or a reasoning failure?** — and it is unanswerable while the two
are welded together. So this module makes the parser a *parameter*: a model
names one, is handed whatever structure it recovers from the text read so far,
and reasons over that. Swapping the parser under a fixed reasoner then measures
the parser; swapping the reasoner under a fixed parser measures the reasoner.

The seam
--------

:class:`PrefixParser` is ``ids -> one Graph per position``. Two implementations
matter and they answer to the same interface:

* :class:`TextPrefix` adapts any parser registered in ``symbolic_ai_parsers``
  (``retrieve-001``, ``template-002``, ...). Its causality is *structural*: it
  is handed ``text[:c]`` and there is no other string in scope, so it cannot
  read forward however it is implemented.
* :class:`OraclePrefix` is what a parser would be if parsing were solved. It is
  handed the episode's true term graph and returns the part of it the reader has
  already earned. **It is a ceiling and not a system**: there is no oracle on
  real text, every number it produces must be labelled as such, and it returns
  nothing at all when the true graph is absent — which is why ``decode`` and the
  agent evaluation, which build batches from ids rather than from episodes, get
  an empty parse out of it. That is the correct behaviour, not a bug.

Why the oracle is not a ``symbolic_ai_parsers.Parser``
------------------------------------------------------

Because it is not a parser. That package's contract is ``str -> Graph`` and the
oracle cannot honour it — it needs the answer key. Registering it there would
put a by-construction perfect row in a scoreboard next to rows that had to work
for theirs. The protocol is still *reused* rather than duplicated: real parsers
reach this seam through :class:`TextPrefix`, which wraps the registry.

THE LEAK, and what is done about it
-----------------------------------

The episode's graph contains the answer symbol — measured on the full 179-lesson
curriculum's 3,580 training episodes, **85.3%** of answers are literally the
label of some node of that episode's graph, and 84.5% on its 716 eval episodes.
Handing a model the whole graph while it predicts the next token is therefore
not a ceiling, it is cheating, and it would produce a large and worthless
number.

So the oracle is prefix-restricted, and the restriction is defined as:

    **The prefix parse is the true term graph restricted to the nodes whose
    symbol the reader has already read.** A node labelled ``L`` is available at
    position ``t`` iff ``L`` has occurred, as a *complete* word, in
    ``decode(ids[:t+1])`` at least as often as that node's rank among the nodes
    sharing ``L``. A node carrying no symbol — ``list``, ``record``, ``tuple``,
    ``app``, ``nil`` — is available once any descendant of it is. Unavailable
    nodes are deleted and their children re-attached to the nearest available
    ancestor.

The property that buys, and the reason this is the right definition rather than
a convenient one:

**The oracle can never name a symbol the model has not already read.** It
supplies relations among seen symbols, which is precisely what a parser
supplies; it cannot supply vocabulary, which is what a leak would look like.
Consistent with that, the leak surface is measured and it is empty: of answers on
the full curriculum, 100.0% occur as a word in the prompt and **0.0%** appear in
the graph while being absent from the prompt. There is no answer for the oracle
to smuggle that the text does not already carry.

A word still being typed does not count. A prefix ending in an alphanumeric
character drops its final word, because ``fran`` may yet become ``frank`` or
``france``; the restriction is therefore conservative at exactly the position
where the answer is about to be emitted.

:func:`audit_prefix_parser` checks both halves of this on real episodes rather
than asserting them in a docstring, and ``tests/test_prefix_parser.py`` runs it.
The two properties are:

* **suffix-freedom** — the parse at ``t`` computed from the whole sequence is
  the parse at ``t`` computed from ``ids[:t+1]`` alone, node for node;
* **no unseen symbol** — every label in the parse at ``t`` occurs in
  ``decode(ids[:t+1])``.

Suffix-freedom alone is not enough and it is worth being explicit about why: an
oracle that returned the *entire* graph at every position would pass it, since
its output would still not vary with the suffix. The second property is the one
that bites, and the model-level test that a graph node labelled with a symbol
the text never contains cannot move any prediction is the one that closes it.
"""

from __future__ import annotations

import bisect
import collections
from typing import Callable, Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.graph import Graph
from symbolic_ai_core.data.tokenizer import (SPECIALS, SymbolTokenizer,
                                             split_words, word_spans)

__all__ = ["PrefixParser", "NullPrefix", "FlatPrefix", "TextPrefix",
           "OraclePrefix", "TextView", "Reading", "build_prefix_parser",
           "prefix_parser_names", "audit_prefix_parser"]

#: Shared and never mutated: a parse of nothing.
EMPTY = Graph()

_NEVER = 1 << 30


# ---------------------------------------------------------------------------
# prefix geometry
# ---------------------------------------------------------------------------
class Reading:
    """The character and word geometry of every prefix of one id sequence.

    Built once per sequence and consulted per position, so that a per-position
    parser does not re-decode the sequence a length-squared number of times.

    The two facts it answers are ``how much text have I read by position t``
    and ``how many complete words is that``. Both are computed so that
    perturbing the ids *after* ``t`` cannot change either, which is what makes
    everything built on top of it causal:

    * character length excludes bytes still sitting in the UTF-8 buffer, so a
      prefix boundary is always a character boundary and always a prefix of the
      full decode;
    * a word whose match ends exactly at the boundary is dropped when its last
      character is alphanumeric, because such a match can grow. Every other
      branch of the word pattern matches a single character and cannot.

    Matches that end strictly before the boundary are untouchable by anything
    after it — regex scanning is left to right, so only the match spanning the
    boundary can be affected by what follows.
    """

    def __init__(self, ids: Sequence[int], tok: SymbolTokenizer) -> None:
        self.ids = list(ids)
        self.tok = tok
        self.text = tok.decode(self.ids)
        self.clen = _prefix_lengths(self.ids, tok)
        spans = word_spans(self.text)
        self.words = [w for w, _, _ in spans]
        self._ends = [e for _, _, e in spans]

    def __len__(self) -> int:
        return len(self.ids)

    def prefix(self, t: int) -> str:
        """``decode(ids[:t+1])``, up to bytes not yet forming a character."""
        return self.text[:self.clen[t]]

    def n_complete_words(self, t: int) -> int:
        """How many whole words the reader has seen by position ``t``."""
        c = self.clen[t]
        k = bisect.bisect_right(self._ends, c)
        if k and self._ends[k - 1] == c and c and self.text[c - 1].isalnum():
            k -= 1                      # the last word may still be growing
        return k


def _prefix_lengths(ids: Sequence[int], tok: SymbolTokenizer) -> list[int]:
    """Characters emitted by ``decode(ids[:t+1])``, for every ``t``.

    Mirrors :meth:`SymbolTokenizer.decode` except that pending bytes are not
    counted until they complete: a half-decoded character is not something the
    reader has read.

    Bytes are flushed as soon as they form whole characters rather than when the
    next piece-token arrives, which is where ``decode`` flushes them. That is not
    a cosmetic difference. This curriculum's answers encode to byte tokens
    routinely — ``Frank`` is in the vocabulary only as `` Frank`` — so a sequence
    can end in a long byte run, and waiting for a flush that never comes would
    have hidden the last several *words* from the reader at exactly the
    positions the answer is emitted at. A byte run that is not valid UTF-8 is
    still held back, which is the conservative direction.
    """
    out: list[int] = []
    n = 0
    buf = bytearray()
    for i in ids:
        s = tok.itos[i] if 0 <= i < len(tok.itos) else "<unk>"
        if len(s) == 6 and s.startswith("<0x") and s.endswith(">"):
            buf.append(int(s[3:5], 16))
            try:
                n += len(bytes(buf).decode("utf-8"))
            except UnicodeDecodeError:
                pass                      # a character still being assembled
            else:
                buf.clear()
        else:
            if buf:
                n += len(buf.decode("utf-8", errors="replace"))
                buf.clear()
            if s not in SPECIALS:
                n += len(s)
        out.append(n)
    return out


class TextView:
    """What a model reads on the text surface: the tokens, and their structure.

    The counterpart of :class:`~symbolic_ai_models.models.symbolic.GraphView`,
    and built on the same principle — there is no field on it holding anything
    the model is not allowed to see. ``graph(t)`` is a function of ``ids[:t+1]``
    (plus, for the oracle, the episode's answer key, which the model never
    touches), memoised because a reasoner asks for the same position more than
    once.
    """

    def __init__(self, reading: Reading, at: Callable[[int], Graph]) -> None:
        self.reading = reading
        self.ids = reading.ids
        self.tok = reading.tok
        self._at = at
        self._cache: dict[int, Graph] = {}

    def __len__(self) -> int:
        return len(self.ids)

    def graph(self, t: int) -> Graph:
        """The structure recoverable from ``ids[:t+1]``, and nothing later."""
        g = self._cache.get(t)
        if g is None:
            g = self._cache[t] = self._at(t)
        return g

    def text(self, t: int) -> str:
        return self.reading.prefix(t)


# ---------------------------------------------------------------------------
# the seam
# ---------------------------------------------------------------------------
class PrefixParser:
    """``fit`` on training episodes; map every prefix of a sequence to a graph.

    ``needs_truth`` is the whole difference between a parser and an oracle, and
    it is a flag rather than a comment so that "which rows in this table are
    ceilings" is greppable.
    """

    #: knob name, as it appears in ``ModelConfig.extra["text_parser"]``
    name: str = ""
    #: whether ``begin`` must be handed the episode's true graph. Only the
    #: oracle says True, and it is not deployable for exactly that reason.
    needs_truth: bool = False

    def fit(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Learn from training episodes. A written-down parser does nothing."""

    def begin(self, ids: Sequence[int], tok: SymbolTokenizer,
              truth: Graph | None = None) -> TextView:
        raise NotImplementedError

    def n_parameters(self) -> int:
        return 0


class NullPrefix(PrefixParser):
    """No structure at all: the control every other column is read against.

    A model configured with this is bit-identical to one that never heard of a
    parser, which is the property that makes the parser × reasoner comparison
    readable rather than a comparison between differently-shaped models.
    """

    name = "none"

    def begin(self, ids, tok, truth=None) -> TextView:
        return TextView(Reading(ids, tok), lambda t: EMPTY)


class FlatPrefix(PrefixParser):
    """The prefix's words as children of one root — tokenisation, no parsing.

    The honest zero for this experiment. A reasoner that picks a node out of a
    parse can still pick a *word* out of a bag, so a gain attributed to
    structure has to be a gain over this and not over abstention. Everything
    here is available to the tokenizer alone, so nothing about it is an oracle.
    """

    name = "flat"

    def begin(self, ids, tok, truth=None) -> TextView:
        reading = Reading(ids, tok)
        cache: dict[int, Graph] = {}

        def at(t: int) -> Graph:
            k = reading.n_complete_words(t)
            g = cache.get(k)
            if g is None:
                g = Graph()
                root = g.add("", "list", -1, 0)
                for s, w in enumerate(reading.words[:k]):
                    g.add(w, "token", root, min(s, 8))
                cache[k] = g
            return g

        return TextView(reading, at)


class TextPrefix(PrefixParser):
    """Any registered ``symbolic_ai_parsers`` parser, applied to every prefix.

    Causal by construction rather than by discipline: the parser is handed the
    prefix string and no other string is in scope, so it cannot read forward
    however it is written. That is the point of adapting the existing protocol
    instead of inventing a second one — a parser does not have to be rewritten,
    or trusted, to be measured here.
    """

    def __init__(self, name: str) -> None:
        from symbolic_ai_parsers import build as build_graph_parser
        self.name = name
        self.parser = build_graph_parser(name)

    def fit(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        self.parser.fit(list(episodes))

    def n_parameters(self) -> int:
        return self.parser.n_parameters()

    def begin(self, ids, tok, truth=None) -> TextView:
        reading = Reading(ids, tok)
        cache: dict[int, Graph] = {}

        def at(t: int) -> Graph:
            c = reading.clen[t]
            g = cache.get(c)
            if g is None:
                g = cache[c] = self.parser.parse(reading.text[:c])
            return g

        return TextView(reading, at)


class OraclePrefix(PrefixParser):
    """The true term graph, restricted to the symbols already read.

    **A ceiling, not a system.** See the module docstring for what "restricted"
    means exactly and for the audit that says the restriction is real. Handed no
    truth — which is what happens on any batch not built from episodes — it
    returns nothing, and a model on it abstains.
    """

    name = "oracle"
    needs_truth = True

    def begin(self, ids, tok, truth=None) -> TextView:
        reading = Reading(ids, tok)
        if truth is None or not len(truth):
            return TextView(reading, lambda t: EMPTY)

        state: dict[str, object] = {}
        cache: dict[int, Graph] = {}

        def at(t: int) -> Graph:
            ready = state.get("ready")
            if ready is None:
                ready = state["ready"] = availability(truth, reading.words)
            k = reading.n_complete_words(t)
            g = cache.get(k)
            if g is None:
                g = cache[k] = restrict(truth, ready, k)      # type: ignore[arg-type]
            return g

        return TextView(reading, at)


def availability(g: Graph, words: Sequence[str]) -> list[int]:
    """``node -> how many words must be read before it may be revealed``.

    The ``r``-th node carrying a symbol waits for the ``r``-th occurrence of
    that symbol, so an episode naming ``dave`` twice reveals its two ``dave``
    nodes one at a time. A symbol the text never uses waits forever — which is
    the clause that makes a leak impossible rather than unlikely, since a
    reader can then never be told a name it has not read.

    Nodes carrying no symbol wait for their first available descendant. They
    are ``list``, ``record``, ``tuple``, ``app`` and ``nil``: revealing one
    discloses that something is a record, never which record, and its arity
    stays prefix-bounded because only available children are ever attached.
    """
    lower = [w.lower() for w in words]
    keys = [tuple(p.lower() for p in split_words(lab)) if lab else ()
            for lab in g.labels]

    # Indexed by first word rather than scanned per key: a full-curriculum fit
    # asks this of every training episode and the scan is the hot loop.
    starts: dict[str, list[int]] = {}
    for j, w in enumerate(lower):
        starts.setdefault(w, []).append(j)
    occurrences: dict[tuple, list[int]] = {}
    for key in {k for k in keys if k}:
        m = len(key)
        occurrences[key] = [j + m for j in starts.get(key[0], ())
                            if j + m <= len(lower)
                            and tuple(lower[j:j + m]) == key]

    need = [_NEVER] * len(g)
    rank: collections.Counter = collections.Counter()
    for i, key in enumerate(keys):
        if not key:
            continue
        r = rank[key]
        rank[key] += 1
        hits = occurrences.get(key) or []
        if r < len(hits):
            need[i] = hits[r]

    kids: list[list[int]] = [[] for _ in range(len(g))]
    for i, p in enumerate(g.parent):
        if 0 <= p < len(g):
            kids[p].append(i)
    for i in sorted(range(len(g)), key=lambda j: -g.depth[j]):
        if not keys[i]:
            below = [need[c] for c in kids[i]]
            need[i] = min(below) if below else _NEVER
    return need


def restrict(g: Graph, need: Sequence[int], k: int) -> Graph:
    """The subgraph readable after ``k`` words, re-attached and renumbered.

    A kept node whose parent is not kept takes its nearest kept ancestor, so the
    result is a forest of the structure actually earned rather than a graph with
    holes in it. Slots are renumbered among the kept siblings: the original slot
    would say how many siblings were skipped, and how many were skipped is a
    fact about the part of the episode that has not been read.
    """
    keep = [i for i in range(len(g)) if need[i] <= k]
    if not keep:
        return EMPTY
    kept = set(keep)
    out = Graph()
    new: dict[int, int] = {}
    slots: collections.Counter = collections.Counter()
    for i in keep:                       # index order is pre-order: parents first
        p = g.parent[i]
        while 0 <= p < len(g) and p not in kept:
            p = g.parent[p]
        np_ = new.get(p, -1) if 0 <= p < len(g) else -1
        s = slots[np_]
        slots[np_] += 1
        new[i] = out.add(g.labels[i], g.types[i], np_, s)
    return out


# ---------------------------------------------------------------------------
# construction
# ---------------------------------------------------------------------------
#: The ones that are not names from ``symbolic_ai_parsers``.
_BUILTIN: dict[str, type[PrefixParser]] = {
    "none": NullPrefix, "flat": FlatPrefix, "oracle": OraclePrefix,
}


def build_prefix_parser(name: str) -> PrefixParser:
    """``none``/``flat``/``oracle``, or any ``symbolic_ai_parsers`` parser."""
    cls = _BUILTIN.get(name)
    return cls() if cls is not None else TextPrefix(name)


def prefix_parser_names() -> list[str]:
    from symbolic_ai_parsers import parser_names
    return sorted(_BUILTIN) + parser_names()


# ---------------------------------------------------------------------------
# the audit
# ---------------------------------------------------------------------------
def audit_prefix_parser(parser: PrefixParser, episodes: Sequence[Episode],
                        tok: SymbolTokenizer, *, max_len: int = 320,
                        stride: int = 7) -> dict[str, float]:
    """Check, on real episodes, that a prefix parser is one.

    Returns counts rather than a verdict, because the interesting failure is a
    *rate*: one leaking node in ten thousand is still a leak and would be
    rounded away by a boolean.

    ``suffix_violations`` — positions where the parse computed from the whole
    sequence differs from the parse computed from ``ids[:t+1]`` alone. Any
    non-zero value means the reader is reading forward.

    ``symbol_violations`` — labels appearing in a parse that do not occur in the
    prefix that produced it. Any non-zero value means the parser is naming
    something the model has not read, which on this curriculum is how the answer
    would get in.

    ``nodes`` and ``positions`` are the denominators, and ``coverage`` is the
    mean node count of a parse — a parser that never returns anything passes
    both checks trivially, and the number that says so belongs next to them.
    """
    suffix = symbol = nodes = positions = 0
    for ep in episodes:
        ids = tok.encode(ep.prompt + "\n", bos=True) + tok.encode(ep.answer, eos=True)
        ids = ids[-max_len:]
        truth = ep.graph if parser.needs_truth else None
        whole = parser.begin(ids, tok, truth)
        for t in range(0, len(ids), stride):
            g = whole.graph(t)
            positions += 1
            nodes += len(g)
            alone = parser.begin(ids[:t + 1], tok, truth).graph(t)
            suffix += g != alone
            seen = {w.lower() for w in split_words(whole.text(t))}
            for label in g.labels:
                if label and not all(p.lower() in seen
                                     for p in split_words(label)):
                    symbol += 1
    return {"suffix_violations": float(suffix),
            "symbol_violations": float(symbol),
            "positions": float(positions), "nodes": float(nodes),
            "coverage": nodes / positions if positions else float("nan")}
