"""Classes induced from where words are allowed to stand, and nothing else.

The idea is Harris (1954) and it is already in this repo — ``grammar`` induces
equivalence classes on its way to predicting the next token. But there it is
welded to a reasoner: the classes are over *tokenizer ids*, they are built as a
side effect of ``learn``, and the only way to ask "were those classes any good?"
is to read the perplexity of the model that used them. That conflates the two
questions this package exists to separate.

So the induction is rebuilt here as a parser and nothing more. It runs over
whole **words** rather than vocabulary pieces, because a class is a claim about
symbols and ``o2`` split into ``o`` and ``2`` is not a symbol; it is fitted on
prompts alone, because that is the text a parser is ever handed at parse time;
and it produces only ``classes``, so it can be scored directly against the roles
the generator actually used and dropped under any reasoner unchanged.

The mechanism is the whole of the model. A context is a ``(left, right)`` pair
of adjacent words, its fillers are the words seen between them, and two words
are merged once they have been seen in ``min_shared`` contexts together.
Contexts with many fillers are ignored: a slot that accepts forty words is
evidence of a frame, not of a category, and one such context would otherwise
collapse the vocabulary into a single class.

What it will be bad at
----------------------

* **One class per word type.** A word used in two roles gets one label, so
  genuine ambiguity is scored as an error and there is no mechanism here that
  could ever fix it.
* **Rare words.** Merging needs repeated evidence, so anything seen a handful of
  times stays unmerged and falls back to being its own class. Coverage on a
  long tail will be poor and that is a property of the method, not a bug.
* **Anything longer than two words.** The context is exactly one word either
  side. Agreement across an embedded clause, matched brackets, scope — none of
  it is visible from here, so on the recursive lessons this parser is reading
  local texture and nothing more.
* **No brackets, no facts.** It groups; it does not build structure. A reasoner
  that needs constituents gets nothing from this parser.
"""

from __future__ import annotations

import collections
import itertools
from typing import Iterable, Sequence

from ..data.curriculum import Episode
from ..data.tokenizer import SymbolTokenizer, split_words
from .base import ParseResult, Parser, register

__all__ = ["InducedClassParser"]

#: Sentence edges, so that a first or last word still has a context. They are
#: not words and can never be merged into a class themselves.
_BOS, _EOS = "\x02", "\x03"


class _Merge:
    """Union-find over words, with the smaller string kept as the root.

    Choosing the root by ``min`` rather than by whichever side happened to be
    argument ``a`` makes the final partition independent of the order the merges
    arrive in, which is what makes the parser reproducible from its episodes
    rather than from its episodes *and* a dictionary's iteration order.
    """

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            hi, lo = max(ra, rb), min(ra, rb)
            self.parent[hi] = lo

    def groups(self) -> list[list[str]]:
        """The merged classes, largest first, members sorted. Singletons are
        dropped: a class of one is not a finding."""
        members: dict[str, list[str]] = collections.defaultdict(list)
        for word in sorted(self.parent):
            members[self.find(word)].append(word)
        return sorted((m for m in members.values() if len(m) > 1),
                      key=lambda m: (-len(m), m))


@register("induced", learned=True,
          doc="Distributional equivalence classes over words: merge what stands in the same contexts.")
class InducedClassParser(Parser):
    """Merge words that share ``min_shared`` two-sided contexts; label the rest
    nothing at all.

    ``min_shared`` trades recall for precision directly — lower it and unrelated
    words that happened to share one frame get fused; raise it and only the
    densely attested categories survive.
    """

    def __init__(self, min_shared: int = 3, max_fillers: int = 10) -> None:
        self.min_shared = int(min_shared)
        self.max_fillers = int(max_fillers)
        #: word -> class name, only for words that were actually merged
        self.classes: dict[str, str] = {}
        #: class name -> its members, largest class first
        self.members: dict[str, list[str]] = {}

    # ---- induction -----------------------------------------------------
    def fit(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        fillers = self._context_fillers(ep.prompt for ep in episodes)
        groups = self._induce(fillers)
        # Names are assigned after sorting, so the same episodes always produce
        # the same ``C3`` — the classes are meant to be quoted in a report.
        self.members = {f"C{i}": g for i, g in enumerate(groups)}
        self.classes = {word: name
                        for name, group in self.members.items()
                        for word in group}

    @staticmethod
    def _context_fillers(texts: Iterable[str]) -> dict[tuple[str, str], set[str]]:
        """``(left, right) -> the words seen between them``.

        Lines are treated separately. A prompt here is a scene, a question and a
        menu of answers stapled together, and the last word of one and the first
        word of the next never stood in a relation the generator built — reading
        across the break would manufacture contexts out of layout.
        """
        fillers: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
        for text in texts:
            for line in text.splitlines():
                words = split_words(line)
                if not words:
                    continue
                seq = [_BOS, *words, _EOS]
                for i in range(1, len(seq) - 1):
                    fillers[(seq[i - 1], seq[i + 1])].add(seq[i])
        return fillers

    def _induce(self, fillers: dict[tuple[str, str], set[str]]) -> list[list[str]]:
        """Count how many contexts each pair of words shares, then merge.

        Only contexts with between two and ``max_fillers`` fillers vote. One
        filler is no evidence of anything — a word cannot be shown to be
        substitutable with itself — and a very open slot is evidence about the
        slot rather than about its occupants.
        """
        shared: collections.Counter[tuple[str, str]] = collections.Counter()
        for words in fillers.values():
            if 2 <= len(words) <= self.max_fillers:
                for a, b in itertools.combinations(sorted(words), 2):
                    shared[(a, b)] += 1

        merge = _Merge()
        for (a, b), count in sorted(shared.items()):
            if count >= self.min_shared:
                merge.union(a, b)
        return merge.groups()

    # ---- use -----------------------------------------------------------
    def parse(self, text: str) -> ParseResult:
        """Look each word up. A word never merged is left unlabelled rather than
        guessed at, which is why coverage is worth reading beside the F1."""
        tokens = split_words(text)
        classes = {i: self.classes[t] for i, t in enumerate(tokens)
                   if t in self.classes}
        return ParseResult(tokens=tokens, classes=classes)

    # ---- reporting ------------------------------------------------------
    def n_parameters(self) -> int:
        """The classes are the model. Membership is a lookup, not a parameter
        that was fitted independently, so it is the class count that is
        reported."""
        return len(self.members)

    def render(self) -> str:
        lines = [f"=== {len(self.members)} induced classes "
                 f"(min_shared={self.min_shared}, max_fillers={self.max_fillers}) ==="]
        for name, group in list(self.members.items())[:20]:
            shown = ", ".join(repr(w) for w in group[:10])
            more = "" if len(group) <= 10 else f" ... (+{len(group) - 10})"
            lines.append(f"  {name}: {{ {shown}{more} }}")
        if len(self.members) > 20:
            lines.append(f"  ... (+{len(self.members) - 20} more classes)")
        return "\n".join(lines)
