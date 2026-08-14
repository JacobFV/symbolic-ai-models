"""``gsite``: point at the head each word attaches under, through a parse.

The first model in the repo that answers the ``site`` readout, and it is
deliberately built the way ``gparse-003`` is built: **one reasoner, one
parser-shaped hole**. Five rows differ in the reader of the text surface and in
nothing else, so the spread between them is a measurement of parsing rather than
a comparison of models.

===================  ================================================
``gsite-001``        ``template-002`` — a real, learned graph parser
``gsite-retrieve``   ``retrieve-001`` — the memorisation control
``gsite-flat``       the prefix's words, unstructured: the honest zero
``gsite-none``       no reader at all: the reasoner with nothing to read
``gsite-oracle``     **a ceiling, and a tautology** — see below
===================  ================================================

``gsite-retrieve`` is registered and is **not in the full-curriculum table**,
which is a cost statement rather than a result. ``retrieve-001`` finds the
nearest training prompt, so a per-prefix reader runs it once per word: on 179
lessons that is a nearest-neighbour search over 3,580 prompts, some forty times
per episode, and it does not finish inside the twenty minutes this machine
allows one process. Its three-lesson row is 0.427 against a floor of 0.350 —
a hypothesis, and a slice, and this repo has been wrong about eight of those.

The reasoner
------------

Parameter-free, on purpose. At each position where a word has just been read:

1. find the node of *its own* parse that the word realises, by **mention rank** —
   the ``r``-th node carrying a symbol is revealed by the ``r``-th occurrence of
   that symbol, which is the convention the prefix restriction already states
   and which a reader can apply from the text alone;
2. walk up to the nearest ancestor of that node carrying a label, skipping the
   structural nodes, which have no surface and therefore no position to point
   at;
3. point at the most recent earlier position that spelled that ancestor's last
   word; point at position 0 — ROOT — when there is no such ancestor.

There is no learning rate, no feature weighting and no stopping rule, so two
rows differ in the parse they were handed and in nothing that could have been
tuned differently for one of them. What *is* fitted is the confidence: how often
this rule was right, on held-out training episodes, bucketed by the depth it
had to walk. That matters because the mixture underneath spends ``1 - c`` of its
mass on a flat back-off, and a rule that is right a third of the time must not
claim more.

Why ``gsite-oracle`` is not a result
------------------------------------

The oracle prefix parser hands the reasoner the true term restricted to the
symbols already read, which is *the same object* the site target is derived
from. Its score — **0.998** on the full curriculum — is therefore the definition
of the target agreeing with itself, and ``tests/test_readouts.py`` asserts it as
a consistency check. It is not evidence about attachment and must never be
quoted as though it were.

The residual 0.2% is understood rather than tolerated: on a multi-word label the
head can become readable part-way through the phrase that attaches to it, and
the target then walks past it (it requires the head to have been read before the
phrase *began*) while the restricted parse hands it over. Two defensible
definitions of "already read", differing on 64 of 30,748 positions.

What would refute the design
----------------------------

If ``gsite-flat`` matches ``gsite-001``, then structure is doing nothing that
tokenisation does not already do, and the attachment signal such as it is comes
from word order. If neither clears the ``site`` floor, then the text surface
carries no attachment a real parser can reach and the readout is a ceiling with
nothing under it.
"""

from __future__ import annotations

import collections
from typing import Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.graph import Graph
from symbolic_ai_core.data.tokenizer import SymbolTokenizer, split_words
from symbolic_ai_core.graphview import Votes

from ...readouts.site import (position_of_word, site_targets, words_at_position,
                              words_read)
from ..base import ModelConfig
from ..registry import register
from ..symbolic import RuleBasedModel, TextView

__all__ = ["GraphSiteLM"]

#: How many depths of walk get their own confidence. Beyond this they share the
#: last bucket: a walk of six and a walk of nine are the same kind of failure.
N_BINS = 5


def _key(label: str) -> tuple[str, ...]:
    """A symbol as case-folded words — the form the reading is compared in."""
    return tuple(p.lower() for p in split_words(label))


def _last_word(label: str) -> str:
    parts = _key(label)
    return parts[-1] if parts else ""


@register("gsite-001",
          doc="Point at the head each word attaches under; the parser is a knob.")
class GraphSiteLM(RuleBasedModel):
    """One reasoner, one parser-shaped hole, on the ``site`` channel."""

    family = "rule-based"
    reads_text_parser = True
    emits_site = True

    #: The knob the parser comparison turns on. Every row that leaves
    #: :attr:`ablation` empty must differ in this and nothing else.
    default_text_parser = "template-002"

    #: Non-empty when this row changes something other than the parser.
    ablation = ""

    LEARNED = ("bin_confidence", "site_seen")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        #: walk depth -> held-out accuracy of a site chosen after that walk
        self.bin_confidence: list[float] = []
        #: how often the rule had anything to say at all, for the write-up
        self.site_seen: float = 0.0

    # ---- fitting -----------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Nothing to count but the confidence, and that is measured out of sample.

        The reasoner is written down rather than fitted, so the only free
        quantity is how much to trust it. Measured on episodes the rest of the
        model never saw — which here means all of them, since nothing else is
        fitted, and the split is kept anyway so that a later version that *does*
        count something cannot quietly calibrate on its own training data.
        """
        cut = max(int(len(episodes) * 0.8), 1)
        held = episodes[cut:] or episodes
        hit: collections.Counter = collections.Counter()
        seen: collections.Counter = collections.Counter()
        fired = asked = 0

        for ep in held:
            ids = tok.encode(ep.prompt + "\n", bos=True) + tok.encode(ep.answer,
                                                                     eos=True)
            ids = ids[max(len(ids) - self.cfg.max_len, 0):]
            truth = ep.graph if self.text_parser.needs_truth else None
            view = self.text_parser.begin(ids, tok, truth)
            reading = view.reading
            read = words_read(reading)
            at = position_of_word(reading, read)
            lower = [w.lower() for w in reading.words]
            targets = site_targets(ep.graph, reading)
            asked += len(targets)
            for t, (_, key) in targets.items():
                got = self._site_at(view, t, read, at, lower)
                if got is None:
                    continue
                fired += 1
                position, depth = got
                bucket = min(depth, N_BINS - 1)
                seen[bucket] += 1
                hit[bucket] += key in words_at_position(reading, position, read)

        self.site_seen = fired / max(asked, 1)
        overall = sum(hit.values()) / max(sum(seen.values()), 1)
        # Shrunk towards the global rate, so a bucket that fired three times
        # does not get to claim a confidence of its own.
        self.bin_confidence = [
            min(max((hit.get(b, 0) + 3.0 * overall) / (seen.get(b, 0) + 3.0),
                    0.0), 0.95)
            for b in range(N_BINS)]

    # ---- the reasoner --------------------------------------------------
    @staticmethod
    def _node_for(g: Graph, lower: Sequence[str], k: int) -> int:
        """Which node of ``g`` the word ending at ``lower[k - 1]`` realises.

        By **mention rank**, which is the convention the prefix restriction
        already states: the ``r``-th node carrying a symbol is revealed by the
        ``r``-th occurrence of that symbol. Counting occurrences is something a
        reader can do from the text alone, so the rule is parser-agnostic — it
        needs the parse only to say which nodes exist.

        The first version of this took "the last node in index order whose label
        ends in this word", which is neither the mention rank nor anything else,
        and it cost the oracle row fifteen points against a reasoner that had
        been handed the answer. Longest label first, so a node labelled
        ``greater than`` is not found as a node labelled ``than``.
        """
        # Longest first, and as long as any label on this curriculum gets. A
        # three-word cap was the first version and it cost the oracle row 0.3%
        # of the full curriculum -- small, and entirely the labels of four words
        # or more, which is exactly the wrong 0.3% to be silently missing.
        for m in (6, 5, 4, 3, 2, 1):
            if k - m < 0:
                continue
            key = tuple(lower[k - m:k])
            nodes = [i for i in range(len(g))
                     if g.labels[i] and _key(g.labels[i]) == key]
            if not nodes:
                continue
            r = sum(1 for j in range(0, k - m)
                    if tuple(lower[j:j + m]) == key)
            return nodes[r] if 0 <= r < len(nodes) else nodes[-1]
        return -1

    def _site_at(self, view: TextView, t: int, read: Sequence[int],
                 at: Sequence[int], lower: Sequence[str]
                 ) -> tuple[int, int] | None:
        """``(position of the head, how far up the walk went)``, or nothing.

        Reads ``view.graph(t)`` and ``view.reading`` and nothing else, both of
        which are functions of ``ids[:t + 1]``. The position returned is always
        strictly earlier than ``t``, so no answer of this reasoner could be
        satisfied by looking forward.
        """
        if t <= 0 or t >= len(read) or not read[t]:
            return None
        if read[t] == read[t - 1]:
            # No word became readable here, so no node was realised here and
            # there is nothing to attach. Checked *before* asking for the parse:
            # a real parser is re-run per prefix, and asking at every position
            # rather than at every word is a factor of six on a 320-token
            # sequence for answers that are all None.
            return None
        g: Graph = view.graph(t)
        if not len(g):
            return None

        # One token can finish more than one word — the curriculum ends every
        # clause with a token carrying `frank` and `.` together, and the
        # conservative "the last word may still be growing" rule means both
        # arrive at the same position. Only one of them realises a node, so the
        # words that became readable *here* are tried newest first rather than
        # assuming it is the last one. Assuming it was cost the oracle row every
        # sentence-final argument in the corpus, which is a third of them.
        node, k = -1, 0
        for w in range(read[t] - 1, -1, -1):
            if at[w] != t:
                break
            node = self._node_for(g, lower, w + 1)
            if node >= 0:
                k = w + 1
                break
        if node < 0:
            return None

        depth, p = 0, g.parent[node]
        while 0 <= p < len(g):
            depth += 1
            if g.labels[p]:
                head = _last_word(g.labels[p])
                # The most recent *earlier* mention of the head's last word.
                # "Most recent" rather than "first" because a term is read left
                # to right and the nearest antecedent is the one a reader has in
                # hand; nothing here consults a later one.
                for w in range(k - 2, -1, -1):
                    if lower[w] == head and 0 <= at[w] < t:
                        return at[w], depth
                break
            p = g.parent[p]
        return 0, depth                    # attaches at the top

    def site_votes_view(self, view: TextView) -> dict[int, Votes]:
        out: dict[int, Votes] = {}
        if not self.bin_confidence:
            return out
        reading = view.reading
        read = words_read(reading)
        at = position_of_word(reading, read)
        lower = [w.lower() for w in reading.words]
        for t in range(len(view.ids)):
            got = self._site_at(view, t, read, at, lower)
            if got is None:
                continue
            position, depth = got
            confidence = self.bin_confidence[min(depth, N_BINS - 1)]
            if confidence > 0.0:
                out[t] = ({position: 1.0}, confidence)
        return out

    # ---- what it learned ----------------------------------------------
    def n_symbolic_parameters(self) -> int:
        return len(self.bin_confidence) + self.text_parser.n_parameters()

    def render(self) -> str:
        return (f"{self.name}: parser={self.text_parser.name} "
                f"fired={self.site_seen:.3f} "
                f"confidence by walk depth="
                f"{[round(c, 3) for c in self.bin_confidence]}")


@register("gsite-oracle",
          doc="CEILING and a tautology: gsite on the prefix-restricted oracle.")
class GraphSiteOracle(GraphSiteLM):
    """1.000 by construction. A consistency check, never a result.

    The oracle prefix parser hands this reasoner the very object the site target
    is derived from, so agreeing with it is not evidence. The row exists because
    a disagreement *would* be evidence — that the target and the prefix
    restriction have come apart — and ``tests/test_readouts.py`` asserts it.
    """

    default_text_parser = "oracle"
    ablation = "reads the answer key through the oracle parser"


@register("gsite-retrieve",
          doc="gsite on retrieve-001: the nearest training prompt's graph.")
class GraphSiteRetrieve(GraphSiteLM):
    """The memorisation control. Whatever a real parser scores above this row is
    the part attributable to reading rather than to recognising the lesson."""

    default_text_parser = "retrieve-001"


@register("gsite-flat",
          doc="gsite on the prefix's words with no structure: the honest zero.")
class GraphSiteFlat(GraphSiteLM):
    """Tokenisation without parsing. Every word is a child of one root, so this
    row attaches everything at ROOT and pins what word order alone is worth."""

    default_text_parser = "flat"


@register("gsite-none", doc="gsite with no reader at all: the reasoner alone.")
class GraphSiteNone(GraphSiteLM):
    """Nothing to point at, so it abstains and lands on the flat back-off. It
    pins what the machinery around the parser is worth by itself, which is
    zero."""

    default_text_parser = "none"
