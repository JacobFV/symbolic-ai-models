"""Putting a predicted graph next to the true one, node by node.

Every edge- and node-level score needs to know which predicted node *is* which
true node, and unlike dependency parsing there is no shared token sequence to
get that for free: a parser here may emit more nodes, fewer nodes, or the right
count in the wrong places. So an alignment has to be computed, and the choice of
alignment is a harness decision — which in this repo is the class of decision
that has produced the largest measured effects. It is therefore written down
exactly, and two of the metrics in :mod:`symbolic_ai_parsers.scoring` are
alignment-*free* on purpose, so that a result resting on this file has a witness
that does not.

The alignment
-------------

Both graphs are ordered trees (children in slot order). The mapping computed
here is the **top-down / isolated-subtree** mapping: roots align, and the
children of two aligned nodes are aligned to each other by an optimal ordered
sequence alignment. Whole subtrees may be inserted or deleted; a node may not be
matched to a node at a different depth, and two siblings may not cross.

That constraint is what makes it cheap and what makes it deterministic. It also
makes it *strict*: a parser that gets the whole document right but wraps it in
one extra node scores zero, because everything moved down a level. That is a
real weakness and it is the reason ``bracket_f1`` and ``label_f1`` exist.

Cost is ``O(sum_d |P_d| * |G_d|)`` — the depth-matched pair count — because the
sub-similarity of two nodes is only ever needed when they sit at the same depth,
and the sequence-alignment work at a node pair is exactly the pair count one
level below. On the curriculum's graphs (mean 60 nodes) that is a few thousand
cells per episode.

Similarity, and why it is integers
----------------------------------

``match(a, b) = (labels equal) + (types equal)``, so 0, 1 or 2. Integer and
tiny on purpose: a weighted similarity would be a set of numbers I chose, and
the alignment would then be tunable in the direction of whichever parser I was
writing up. Ties break toward the earlier index, which is deterministic and
independent of hash order — this repo has already been bitten by a tie-break
that rested on set iteration order and flapped between processes.
"""

from __future__ import annotations

from typing import Sequence

from symbolic_ai_core.data.graph import Graph

__all__ = ["children_of", "canonical", "align", "content_align"]


def children_of(g: Graph) -> list[list[int]]:
    """``node -> its children, in index order`` (which is slot order)."""
    kids: list[list[int]] = [[] for _ in range(len(g))]
    for i, p in enumerate(g.parent):
        if 0 <= p < len(g):
            kids[p].append(i)
    return kids


def roots_of(g: Graph) -> list[int]:
    return [i for i, p in enumerate(g.parent) if p < 0 or p >= len(g)]


def canonical(g: Graph) -> Graph:
    """Renumber breadth-first, so every score is about the tree and not the
    order somebody happened to emit it in.

    Exact match is otherwise a statement about node numbering, and — less
    obviously, and caught by a test rather than by reading — so is
    :func:`content_align`, which pairs the k-th occurrence of a label with the
    k-th occurrence of it. "The k-th" needs an order to mean anything, so the
    order is fixed here, once, for both graphs. Scoring canonicalises both sides
    before it does anything else.

    Node count is preserved even for input that is not a tree: a forest keeps
    all its roots, and anything unreachable (a cycle from a broken parser) is
    appended as its own root rather than silently dropped. Dropping it would
    shrink the prediction and quietly raise its precision.
    """
    kids = children_of(g)
    out = Graph()
    seen = [False] * len(g)
    queue: list[tuple[int, int, int]] = [(r, -1, k)
                                         for k, r in enumerate(roots_of(g))]
    while queue:
        old, parent, slot = queue.pop(0)
        if seen[old]:
            continue
        seen[old] = True
        new = out.add(g.labels[old], g.types[old], parent, slot)
        queue.extend((c, new, k) for k, c in enumerate(kids[old]))
    for i, done in enumerate(seen):
        if not done:
            out.add(g.labels[i], g.types[i], -1, 0)
    return out


def _match(a_lab: str, a_typ: str, b_lab: str, b_typ: str) -> int:
    return (a_lab == b_lab) + (a_typ == b_typ)


def _seq_align(pa: Sequence[int], ga: Sequence[int],
               sim: dict[tuple[int, int], int]) -> tuple[int, list[tuple[int, int]]]:
    """Needleman-Wunsch with zero gap cost over two child lists.

    Returns ``(total, pairs)``. Gaps are free because an unmatched subtree is
    already unscored everywhere else; charging for it here would double-count
    it and would make the alignment depend on a penalty I invented.
    """
    n, m = len(pa), len(ga)
    if not n or not m:
        return 0, []
    # dp[i][j] = best total over pa[i:], ga[j:]
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        row, nxt = dp[i], dp[i + 1]
        for j in range(m - 1, -1, -1):
            diag = nxt[j + 1] + sim[(pa[i], ga[j])]
            row[j] = diag if diag >= row[j + 1] and diag >= nxt[j] else max(row[j + 1], nxt[j])
    pairs: list[tuple[int, int]] = []
    i = j = 0
    while i < n and j < m:
        diag = dp[i + 1][j + 1] + sim[(pa[i], ga[j])]
        if diag >= dp[i][j + 1] and diag >= dp[i + 1][j]:
            pairs.append((pa[i], ga[j]))
            i += 1
            j += 1
        elif dp[i][j + 1] >= dp[i + 1][j]:
            j += 1
        else:
            i += 1
    return dp[0][0], pairs


def align(pred: Graph, gold: Graph) -> dict[int, int]:
    """``predicted node -> gold node``, under the top-down mapping above.

    An empty prediction, or one with no root, aligns nothing rather than
    raising: a parser that fails on an input must be scorable, or the evaluation
    silently drops its hardest cases and reports the rest.
    """
    p_roots, g_roots = roots_of(pred), roots_of(gold)
    if not p_roots or not g_roots or not len(pred) or not len(gold):
        return {}

    p_kids, g_kids = children_of(pred), children_of(gold)
    p_depth, g_depth = pred.depth, gold.depth
    by_depth_p: dict[int, list[int]] = {}
    by_depth_g: dict[int, list[int]] = {}
    for i, d in enumerate(p_depth):
        by_depth_p.setdefault(d, []).append(i)
    for j, d in enumerate(g_depth):
        by_depth_g.setdefault(d, []).append(j)

    # sim[(i, j)] for depth-matched pairs, deepest level first so that a level's
    # children are always already solved.
    sim: dict[tuple[int, int], int] = {}
    for d in sorted(set(by_depth_p) & set(by_depth_g), reverse=True):
        for i in by_depth_p[d]:
            ki = p_kids[i]
            for j in by_depth_g[d]:
                below, _ = _seq_align(ki, g_kids[j], sim) if ki and g_kids[j] else (0, [])
                sim[(i, j)] = _match(pred.labels[i], pred.types[i],
                                     gold.labels[j], gold.types[j]) + below

    mapping: dict[int, int] = {p_roots[0]: g_roots[0]}
    stack = [(p_roots[0], g_roots[0])]
    while stack:
        i, j = stack.pop()
        _, pairs = _seq_align(p_kids[i], g_kids[j], sim)
        for a, b in pairs:
            mapping[a] = b
            stack.append((a, b))
    return mapping


def content_align(pred: Graph, gold: Graph) -> dict[int, int]:
    """``predicted node -> gold node``, by *content*, ignoring structure entirely.

    The k-th node with key ``(label, type)`` in the prediction is the k-th node
    with that key in the gold, in index order. Nothing else is consulted.

    This exists because :func:`align` cannot be used to score attachment, and
    that is not a matter of taste. The top-down mapping only ever adds a pair
    once the pair's parents are already mapped, so *every* node it aligns has a
    correctly attached parent by construction. An attachment score computed over
    it is identically 1 on every aligned node, which makes it a measure of how
    many nodes were alignable wearing the name of a parsing score. It was
    written that way here first, and it read as a strong result.

    A content alignment is the exact analogue of what dependency parsing gets
    for free: there, two parses of one sentence are compared token index by
    token index, because the tokens are shared. Here the shared thing is the
    label a node carries, so the k-th occurrence of a label plays the part of
    the k-th token. Attachment is then a real question — the node is identified
    without reference to where it sits, and the score asks whether it sits in
    the right place.
    """
    buckets: dict[tuple[str, str], list[int]] = {}
    for j in range(len(gold)):
        buckets.setdefault((gold.labels[j], gold.types[j]), []).append(j)
    used: dict[tuple[str, str], int] = {}
    mapping: dict[int, int] = {}
    for i in range(len(pred)):
        key = (pred.labels[i], pred.types[i])
        k = used.get(key, 0)
        got = buckets.get(key)
        if got and k < len(got):
            mapping[i] = got[k]
            used[key] = k + 1
    return mapping
