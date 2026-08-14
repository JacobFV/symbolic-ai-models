"""The missing spans: aligning the term graph onto the text that renders it.

Every classical parser wants a treebank — sentences with brackets over them —
and this corpus does not have one. ``langcurriculum`` hands over the term and the
string but records nothing about *which characters* a subterm produced, which is
exactly why the metric in :mod:`symbolic_ai_parsers.scoring` avoids span
alignment. A chart parser cannot avoid it: to induce a grammar you must know
which tokens a node covers.

So the spans are recovered here, heuristically, and the heuristic's coverage is
measured rather than assumed (:attr:`Treebank.coverage`). Two facts about the
curriculum make it work far better than it has any right to:

* **Arguments are copied verbatim.** ``(outranks dave erin)`` renders with
  ``dave`` and ``erin`` in it, in every language — identifiers and numbers are
  never translated. So a node's arguments can be *found* in the text by string
  match, and its span is where they are.
* **Predicates render as one clause.** A line, or a semicolon-delimited segment,
  realises one predicate. Clause boundaries are punctuation, so segmenting is
  language-independent.

The procedure, in full, because a heuristic that is not written down is a
confound:

1. Segment the prompt into lines, then each line on ``;``. Bullet markers are
   stripped. This is punctuation only — no words.
2. Take every graph node whose children are all leaves. Its *anchors* are the
   labels of those children.
3. Score each segment by how many distinct anchors occur in it as whole tokens.
   Assign nodes to segments greedily, best score first, one node per segment, so
   two predicates cannot claim the same clause.
4. Record the surface order of the matched arguments and the graph slot each one
   came from — separately, because they differ. Turkish moves the predicate to
   the end of the clause and leaves the arguments where they were; a grammar
   that did not keep the two orders apart would learn Turkish as a different
   set of predicates rather than as a different word order.

What this cannot do is recover the record-and-field scaffolding above the
clause level. Nothing tries: the classical parsers assemble that from block
layout, the same way ``bracket-001`` does, and the grammar they induce is a
grammar *of clauses*. That is a real limitation and it caps every score they can
reach; it is stated here rather than discovered in the numbers.
"""

from __future__ import annotations

import collections
import re
from dataclasses import dataclass, field
from typing import Callable, Iterator, Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.graph import Graph

from .features import fold
from .features import words_of

__all__ = ["Segment", "ClauseSample", "Treebank", "segments", "blocks"]

_BULLET = re.compile(r"^(\s*[-*•]\s*)")
_DIGITS = re.compile(r"^\d+$")
#: Leaf types that carry a value a clause can mention.
LEAF_TYPES = frozenset({"ident", "num", "token", "str", "char"})
#: Node types that render as a clause.
CLAUSE_TYPES = frozenset({"pred", "rel", "node", "app"})


@dataclass(frozen=True)
class Segment:
    """One clause of the prompt: its tokens, and which block it sat under."""

    tokens: tuple[str, ...]
    block: int
    #: the block's header text, before its colon. Used for the field label.
    header: str = ""


@dataclass(frozen=True)
class ClauseSample:
    """A clause and the subtree it realises. One training item for a grammar."""

    tokens: tuple[str, ...]
    head: str
    #: surface token index -> graph slot, for the tokens that are arguments
    arg_slots: tuple[tuple[int, int], ...]
    #: node type of the clause's root, so the grammar can emit it back
    node_type: str = "pred"

    def categories(self) -> tuple[str, ...]:
        """The right-hand side: ``ARG`` at argument positions, the word itself
        elsewhere. This is what the grammar generalises over."""
        args = dict(self.arg_slots)
        return tuple("ARG" if i in args else w
                     for i, w in enumerate(self.tokens))


#: The default word splitter. Passed explicitly everywhere below rather than
#: read from module scope, so that a parser can supply a different one without
#: any other parser's segmentation moving with it. See
#: :mod:`symbolic_ai_parsers.segment` for the alternative and why it exists.
Splitter = Callable[[str], "list[str]"]


def blocks(text: str) -> list[tuple[str, list[str]]]:
    """``(header, body lines)`` per block. Punctuation and indentation only.

    A block starts at a non-bullet line; bullet lines join the block above them.
    Shared with ``bracket-001`` in spirit and re-derived here rather than
    imported, because the two have different jobs and a shared helper that
    drifts is worse than two that are each right.
    """
    out: list[tuple[str, list[str]]] = []
    for line in fold(text).split("\n"):
        if not line.strip():
            continue
        m = _BULLET.match(line)
        if m:
            body = line[m.end():]
            if out:
                out[-1][1].append(body)
            else:
                out.append(("", [body]))
            continue
        head, sep, tail = line.partition(":")
        out.append((head if sep else line, [t for t in
                                            (p.strip() for p in tail.split(";"))
                                            if t] if sep else []))
    return out


def segments(text: str, words: Splitter = words_of) -> list[Segment]:
    """Every clause of the prompt, tagged with the block it belongs to.

    ``words`` defaults to the repo's shared splitter, so every existing parser
    segments exactly as it did. It is an argument at all because that splitter
    is script-dependent in a way that has nothing to do with parsing; see
    :mod:`symbolic_ai_parsers.segment`.
    """
    out: list[Segment] = []
    for b, (header, body) in enumerate(blocks(text)):
        for line in body:
            for piece in line.split(";"):
                toks = tuple(words(piece))
                if toks:
                    out.append(Segment(toks, b, header))
        if not body:
            toks = tuple(words(header))
            if toks:
                out.append(Segment(toks, b, header))
    return out


def _clause_nodes(g: Graph) -> Iterator[tuple[int, str, list[tuple[int, str]]]]:
    """``(index, head, [(slot, label)])`` for nodes whose children are leaves."""
    kids: dict[int, list[int]] = collections.defaultdict(list)
    for i, p in enumerate(g.parent):
        if 0 <= p < len(g):
            kids[p].append(i)
    for i in range(len(g)):
        if g.types[i] not in CLAUSE_TYPES or not g.labels[i]:
            continue
        ch = kids.get(i, [])
        if not ch or any(kids.get(c) for c in ch):
            continue
        args = [(g.slot[c], g.labels[c]) for c in ch
                if g.types[c] in LEAF_TYPES and g.labels[c]]
        if args:
            yield i, g.labels[i], args


@dataclass
class Treebank:
    """Clause samples drawn from training episodes, plus how many were found."""

    samples: list[ClauseSample] = field(default_factory=list)
    n_clause_nodes: int = 0
    n_aligned: int = 0
    n_episodes: int = 0
    #: the language each sample came from, parallel to :attr:`samples`. Empty
    #: for a monolingual build; a conditioned grammar reads it.
    languages: list[str] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        """Share of clause-shaped graph nodes that found a segment.

        The honest ceiling on everything built from this treebank. A grammar
        induced from 40% of the predicates has not seen the other 60%, and no
        amount of parsing machinery recovers them.
        """
        return self.n_aligned / self.n_clause_nodes if self.n_clause_nodes else 0.0

    @classmethod
    def build(cls, episodes: Sequence[Episode], words: Splitter = words_of
              ) -> "Treebank":
        tb = cls(n_episodes=len(episodes))
        for ep in episodes:
            tb._add(ep, words)
        return tb

    def extend(self, other: "Treebank") -> None:
        """Fold another treebank in. Used to assemble a multilingual one from
        per-language builds without re-segmenting anything."""
        self.samples.extend(other.samples)
        self.languages.extend(other.languages)
        self.n_clause_nodes += other.n_clause_nodes
        self.n_aligned += other.n_aligned
        self.n_episodes += other.n_episodes

    def _add(self, ep: Episode, words: Splitter = words_of) -> None:
        segs = segments(ep.prompt, words)
        lowered = [tuple(t.lower() for t in s.tokens) for s in segs]
        nodes = list(_clause_nodes(ep.graph))
        self.n_clause_nodes += len(nodes)
        if not segs or not nodes:
            return

        # Score every (node, segment) pair, then take them greedily best-first.
        # Greedy rather than optimal: the assignment is nearly always forced,
        # and a Hungarian solve here would be precision theatre on top of a
        # heuristic.
        scored: list[tuple[int, int, int]] = []
        for ni, (_, head, args) in enumerate(nodes):
            want = {lab.lower() for _, lab in args}
            for si, toks in enumerate(lowered):
                hit = len(want & set(toks))
                if hit:
                    scored.append((hit, ni, si))
        scored.sort(key=lambda t: (-t[0], t[1], t[2]))

        used_n: set[int] = set()
        used_s: set[int] = set()
        for _, ni, si in scored:
            if ni in used_n or si in used_s:
                continue
            used_n.add(ni)
            used_s.add(si)
            sample = self._sample(nodes[ni], segs[si], lowered[si], ep.graph)
            if sample is not None:
                self.n_aligned += 1
                self.samples.append(sample)
                self.languages.append(ep.language)

    @staticmethod
    def _sample(node: tuple[int, str, list[tuple[int, str]]], seg: Segment,
                lowered: tuple[str, ...], g: Graph) -> ClauseSample | None:
        idx, head, args = node
        taken: set[int] = set()
        arg_slots: list[tuple[int, int]] = []
        for slot, label in args:
            low = label.lower()
            for i, tok in enumerate(lowered):
                if i not in taken and tok == low:
                    taken.add(i)
                    arg_slots.append((i, slot))
                    break
        if not arg_slots:
            return None
        return ClauseSample(tokens=seg.tokens, head=head,
                            arg_slots=tuple(sorted(arg_slots)),
                            node_type=g.types[idx])
