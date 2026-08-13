"""Brackets, from nothing but how often two words stand next to each other.

``induced`` groups words; this one groups *positions*. It is here because the
class metric and the bracket column measure different failures, and a package
whose only learned parser assigns categories cannot say whether structure is
recoverable from distribution at all.

The mechanism is the oldest unsupervised bracketing idea there is: adjacency
that beats chance is evidence of a unit. Pointwise mutual information over
adjacent word pairs,

    pmi(a, b) = log( p(a b) / (p(a) p(b)) )

is high exactly when ``b`` follows ``a`` more often than the two words'
frequencies alone would explain — which is what "these belong together" means
when nobody has told you what a phrase is. The pair with the highest such score
is bracketed, the bracket then stands in for its own edge words, and the process
repeats bottom-up until nothing clears the threshold. That is Magerman and
Marcus's mutual-information parser with SEQUITUR's habit of promoting whatever
recurs, cut down to the part that needs no grammar.

The threshold is fitted rather than picked: it is a quantile of the PMI actually
observed on the training prompts, so a corpus whose words are all mutually
predictive does not get bracketed to the root and a loose one does not get left
flat. Where that quantile sits was chosen on held-out episodes from seed ranges
this parser is not scored on, and it sits low — the bar that does most of the
work is ``min_count``, not the quantile.

Because the eval in this package scores classes, each token is also given the
label of the tightest chunk it joined, named by that chunk's first word. That is
a genuine prediction — "these tokens are the same sort of thing because the
counts said they belonged together" — but it is a by-product of bracketing, and
on the curriculum it lands only a little above the one-big-class floor. The
brackets are the output worth having; the classes are what makes the parser
comparable to one that induces them on purpose.

What it will be bad at
----------------------

* **Everything binary and greedy.** Every bracket has two children and the
  highest-scoring merge is taken irrevocably. A locally attractive pair that
  straddles a real boundary is a mistake this parser cannot undo, and the trees
  it builds are far flatter in truth than the ones it draws.
* **Recursion.** PMI is measured between adjacent words, so a dependency across
  an embedded clause is invisible; on ``center_embedding`` the brackets will be
  local texture that happens to be nested, not the embedding itself.
* **Rare pairs.** A bigram seen twice has a wild PMI estimate, which is why
  ``min_count`` exists and why the parser simply declines to bracket text made
  of words it has not counted.
* **Its classes are not categories.** Two words share a label when they landed
  in chunks with the same first word. That correlates with role on frame-like
  text and stops correlating with it as soon as the frame varies — it is a much
  weaker claim than ``induced`` makes, and it scores like one.
"""

from __future__ import annotations

import collections
import math
from typing import Iterable, Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer, split_words
from .base import Constituent, ParseResult, Parser, register

__all__ = ["ChunkParser"]


@register("chunker", learned=True,
          doc="Bottom-up brackets over adjacent words whose mutual information beats a fitted threshold.")
class ChunkParser(Parser):
    """Count bigrams, then merge greedily by PMI until nothing clears the bar.

    ``min_count`` is the evidence a bigram needs before it is allowed an
    opinion; ``quantile`` is where in the observed PMI distribution the
    threshold is placed, and so how much of the text ends up bracketed.
    """

    def __init__(self, min_count: int = 3, quantile: float = 0.1) -> None:
        self.min_count = int(min_count)
        self.quantile = float(quantile)
        #: retained ``(a, b) -> pmi``; the whole of what this parser knows
        self.pmi: dict[tuple[str, str], float] = {}
        #: the fitted bar a pair must clear to be bracketed
        self.threshold: float = math.inf

    # ---- counting -------------------------------------------------------
    def fit(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        unigrams: collections.Counter[str] = collections.Counter()
        bigrams: collections.Counter[tuple[str, str]] = collections.Counter()
        for words in _lines(ep.prompt for ep in episodes):
            unigrams.update(words)
            bigrams.update(zip(words, words[1:]))

        total_uni = sum(unigrams.values())
        total_bi = sum(bigrams.values())
        if not total_bi:
            self.pmi, self.threshold = {}, math.inf
            return

        # Rare bigrams are dropped before the PMI is computed, not after: a
        # pair seen once has the highest PMI in the corpus by construction, and
        # keeping it would put the threshold somewhere meaningless.
        self.pmi = {
            (a, b): math.log((count / total_bi)
                             / ((unigrams[a] / total_uni) * (unigrams[b] / total_uni)))
            for (a, b), count in sorted(bigrams.items()) if count >= self.min_count}
        self.threshold = _quantile(sorted(self.pmi.values()), self.quantile)

    # ---- use -----------------------------------------------------------
    def parse(self, text: str) -> ParseResult:
        """Bracket each line independently, bottom-up.

        Lines are separate because a prompt is a scene, a question and an answer
        menu glued together — bracketing across the break would assert a
        constituent the layout never claimed. Text made of unseen words simply
        produces no merges, which is the intended degradation: tokens, and no
        false structure.
        """
        tokens = split_words(text)
        constituents: list[Constituent] = []
        classes: dict[int, str] = {}
        at = 0
        for line in text.splitlines():
            n = len(split_words(line))
            if n:
                self._chunk_span(tokens, at, at + n, constituents, classes)
            at += n
        return ParseResult(tokens=tokens, classes=classes,
                           constituents=constituents)

    def _chunk_span(self, tokens: Sequence[str], start: int, end: int,
                    constituents: list[Constituent],
                    classes: dict[int, str]) -> None:
        """Repeatedly bracket the best adjacent pair of units in one line.

        A unit is a span standing in for its own edge words: after ``a b`` is
        bracketed, the score against what follows is read off ``b``, so a chunk
        continues to grow rightwards on the evidence of its own right edge. Ties
        go to the leftmost pair, which is arbitrary but fixed — without a rule
        the parse would depend on iteration order and stop being reproducible.
        """
        units: list[tuple[int, int]] = [(i, i + 1) for i in range(start, end)]
        while len(units) > 1:
            best, best_score = -1, self.threshold
            for k in range(len(units) - 1):
                score = self.pmi.get((tokens[units[k][1] - 1], tokens[units[k + 1][0]]))
                if score is not None and score > best_score:
                    best, best_score = k, score
            if best < 0:
                break
            left, right = units[best], units[best + 1]
            span = (left[0], right[1])
            label = _label(tokens[span[0]])
            # Appended as they are built, so the list is innermost-first — the
            # convention ``ParseResult`` documents.
            constituents.append(Constituent(span[0], span[1], label))
            # ``setdefault``, so a token keeps the label of the *tightest*
            # chunk it ever joined. The outer brackets of a greedy binary parse
            # are mostly an artefact of having to attach everything somewhere;
            # the first merge is the one the mutual information argued for, and
            # labelling from it scored better on held-out episodes than
            # labelling from the top-level chunk did.
            for i in range(span[0], span[1]):
                classes.setdefault(i, label)
            units[best:best + 2] = [span]

    # ---- reporting ------------------------------------------------------
    def n_parameters(self) -> int:
        """One per retained bigram. The threshold is fitted too, but a single
        scalar is not worth pretending is a parameter alongside thousands."""
        return len(self.pmi)

    def render(self) -> str:
        lines = [f"=== {len(self.pmi)} retained bigrams, "
                 f"threshold {self.threshold:.3f} (q={self.quantile}) ==="]
        top = sorted(self.pmi.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
        for (a, b), score in top:
            lines.append(f"  {score:8.3f}  {a!r} {b!r}")
        if len(self.pmi) > 20:
            lines.append(f"  ... (+{len(self.pmi) - 20} more)")
        return "\n".join(lines)


def _label(word: str) -> str:
    """A chunk's name. Bracketed so it cannot be confused with a bare word: a
    token *in* a chunk beginning with ``at`` is making a different claim from an
    unchunked token that happens to be ``at``."""
    return f"[{word}"


def _lines(texts: Iterable[str]) -> Iterable[list[str]]:
    for text in texts:
        for line in text.splitlines():
            words = split_words(line)
            if words:
                yield words


def _quantile(values: Sequence[float], q: float) -> float:
    """Nearest-rank quantile of an already sorted sequence.

    No interpolation, so the threshold is always a PMI that was actually
    observed — the bar is a real pair's score rather than a number between two
    of them.
    """
    if not values:
        return math.inf
    i = min(len(values) - 1, max(0, int(q * len(values))))
    return values[i]
