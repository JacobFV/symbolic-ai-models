"""How right a parse is, in six numbers, none of which is sufficient alone.

A parse is not right or wrong. A graph with one node in the wrong place and a
graph that is unrelated to the text both score zero on exact match, and a
harness that only reported exact match would call them the same thing. So six
scores are reported for every parse, chosen so that they fail in *different*
directions:

``exact``
    The canonical graphs are equal. Order-independent (see
    :func:`~symbolic_ai_parsers.align.canonical`) but otherwise all-or-nothing.

``uas`` / ``las``
    Labelled-attachment-style, over parent edges, under the **content**
    alignment — the k-th node carrying a label is the k-th gold node carrying
    it, exactly as dependency parsing compares two analyses token index by token
    index. A node's edge is right when its parent is aligned to its gold
    parent's counterpart; ``las`` additionally demands the arc label, which here
    is the slot index. Reported as F1 over edges rather than accuracy over gold
    edges, because accuracy alone cannot see a parser that emits ten times too
    many nodes.

    These are **not** computed under the tree alignment, and that is a
    correction rather than a preference: the tree alignment only pairs nodes
    whose parents are already paired, so attachment under it is identically
    right on every aligned node. It was written that way first and produced a
    UAS of 0.95 for a parser that copies a remembered graph. See
    :func:`~symbolic_ai_parsers.align.content_align`.

``type_acc``
    Fraction of *gold* nodes whose counterpart under the **tree** alignment
    carries the same node type — "is the right kind of thing in this position".
    The tree alignment is the right one here for the same reason it is the wrong
    one above: it identifies a node by where it sits, so agreeing about its type
    is a real question. An unaligned gold node counts as wrong. This metric is
    recall-shaped and therefore gameable by over-generating, which is why
    ``size_ratio`` (predicted nodes / gold nodes) is printed beside it in every
    table. Two numbers that can be read against each other beat one number with
    a caveat.

``bracket_f1`` — the span/label score
    PARSEVAL, moved from token offsets onto a graph whose leaves are labels
    rather than positions. A bracket is ``(type, label, yield)`` where the yield
    is the tuple of leaf labels under the node, in order. Non-leaf nodes only,
    as in PARSEVAL. Multiset F1.

``label_f1``
    Multiset F1 over the non-empty node labels, structure ignored entirely. Pure
    vocabulary recovery. It is here because it is the score a dictionary is
    supposed to move, and separating it from ``bracket_f1`` is what makes
    "learned the grammar" and "learned the words" separately visible.

``bracket_f1`` and ``label_f1`` never call the aligner. That is the point of
them: if the alignment-based scores and the alignment-free scores rank two
parsers differently, the disagreement is the finding and both get reported.

Aggregation is **per episode, then macro over lessons**. Never pooled over
nodes. A pooled node average is a weighted vote in which one 128-node episode
outvotes twenty 6-node ones, and this repo has twice published a confidently
wrong sign from exactly that mistake.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from symbolic_ai_models.data.graph import Graph

from .align import align, canonical, children_of, content_align

__all__ = ["METRICS", "score_graph", "Scores", "mean_scores", "macro_scores",
           "brackets", "label_bag"]

#: Every metric this package reports, in table order. A parser is never quoted
#: on one of these without saying which; a ranking is a property of a metric.
METRICS = ("exact", "uas", "las", "type_acc", "bracket_f1", "label_f1")


def _f1(correct: int, n_pred: int, n_gold: int) -> float:
    if not n_pred or not n_gold:
        return 0.0
    p, r = correct / n_pred, correct / n_gold
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def _multiset_f1(a: collections.Counter, b: collections.Counter) -> float:
    common = sum((a & b).values())
    return _f1(common, sum(a.values()), sum(b.values()))


def _yield_of(g: Graph, kids: Sequence[Sequence[int]]) -> list[tuple[str, ...]]:
    """Leaf labels under every node, in index order. Iterative, so a pathological
    depth cannot blow the stack in the middle of an evaluation."""
    out: list[tuple[str, ...]] = [()] * len(g)
    for i in range(len(g) - 1, -1, -1):
        if not kids[i]:
            out[i] = (g.labels[i] or g.types[i],)
        else:
            acc: list[str] = []
            for c in kids[i]:
                acc.extend(out[c])
            out[i] = tuple(acc)
    return out


def brackets(g: Graph) -> collections.Counter:
    """``(type, label, yield)`` for every non-leaf node. The span/label score's
    unit, and computed without reference to any other graph."""
    kids = children_of(g)
    ys = _yield_of(g, kids)
    return collections.Counter(
        (g.types[i], g.labels[i], ys[i]) for i in range(len(g)) if kids[i])


def label_bag(g: Graph) -> collections.Counter:
    """Multiset of non-empty node labels. Structure ignored on purpose."""
    return collections.Counter(l for l in g.labels if l)


@dataclass
class Scores:
    """One parse, scored. ``size_ratio`` travels with the scores, never apart."""

    exact: float = 0.0
    uas: float = 0.0
    las: float = 0.0
    type_acc: float = 0.0
    bracket_f1: float = 0.0
    label_f1: float = 0.0
    size_ratio: float = 0.0
    #: gold nodes the tree alignment found a counterpart for. Not a metric —
    #: the diagnostic that ``uas`` used to be by accident, kept where it can be
    #: read but not quoted as a parsing score.
    node_cov: float = 0.0
    n_gold: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return dict(self.__dict__)


def score_graph(pred: Graph, gold: Graph) -> Scores:
    """Score one predicted graph against the term the text was generated from."""
    n_gold = len(gold)
    if not n_gold:
        return Scores(exact=float(not len(pred)), n_gold=0.0)

    # Both sides are canonicalised first. Every score below then depends on the
    # tree and not on the order a parser happened to emit it in -- which the
    # occurrence-counting content alignment silently did until a test caught it.
    cp, cg = canonical(pred), canonical(gold)
    s = Scores(n_gold=float(n_gold), size_ratio=len(pred) / n_gold,
               exact=float(cp.to_dict() == cg.to_dict()),
               bracket_f1=_multiset_f1(brackets(cp), brackets(cg)),
               label_f1=_multiset_f1(label_bag(cp), label_bag(cg)))

    n_pred = len(cp)

    # Attachment, under the content alignment. See the module docstring for why
    # it is not the tree alignment.
    content = content_align(cp, cg)
    uas_ok = las_ok = 0
    for i, j in content.items():
        pp, gp = cp.parent[i], cg.parent[j]
        head_ok = (pp < 0 and gp < 0) or (pp >= 0 and content.get(pp, -2) == gp)
        uas_ok += head_ok
        las_ok += head_ok and cp.slot[i] == cg.slot[j]
    s.uas = _f1(uas_ok, n_pred, n_gold)
    s.las = _f1(las_ok, n_pred, n_gold)

    # Node type, under the tree alignment.
    tree = align(cp, cg)
    s.node_cov = len(tree) / n_gold
    s.type_acc = sum(cp.types[i] == cg.types[j]
                     for i, j in tree.items()) / n_gold
    return s


def mean_scores(scores: Iterable[Scores]) -> dict[str, float]:
    rows = [s.as_dict() for s in scores]
    if not rows:
        return {k: float("nan") for k in list(Scores().as_dict())}
    return {k: sum(r[k] for r in rows) / len(rows) for k in rows[0]}


def macro_scores(scores: Sequence[Scores], lessons: Sequence[str]
                 ) -> dict[str, float]:
    """Mean within each lesson, then mean over lessons.

    Lessons differ by a factor of twenty in graph size and by more than that in
    how templated they are. An episode-weighted mean over an unbalanced draw is
    a statement about the draw; the macro mean is a statement about the
    curriculum.
    """
    by_lesson: dict[str, list[Scores]] = collections.defaultdict(list)
    for s, lid in zip(scores, lessons):
        by_lesson[lid].append(s)
    if not by_lesson:
        return mean_scores([])
    per = [mean_scores(v) for v in (by_lesson[k] for k in sorted(by_lesson))]
    return {k: sum(p[k] for p in per) / len(per) for k in per[0]}
