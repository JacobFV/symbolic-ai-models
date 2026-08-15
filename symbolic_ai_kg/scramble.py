"""The control: same graph, same degrees, no meaning.

A knowledge graph makes a curriculum **denser** as well as **more meaningful**,
and those are different things. Without a control that holds the first fixed and
destroys the second, "semantics helped" cannot be told apart from "more
structure helped" or from "the model memorised the graph".

This is the analogue of ``vsa_hks_shuf_pure-004``, which permutes the signature
rows across nodes, preserves the Gram's value multiset bit-identically, and
falls from +0.107 to -0.071 — the control that made this repo's strongest
embedding result readable. See
``notes/lessons/2026-08-13-a-control-that-could-fail.md``.

What is held fixed, exactly
---------------------------

* the node set, and every node attribute: lemma, part of speech, lexicographer
  file, verb frames. The scramble never touches a node;
* **the in-degree and the out-degree of every node, in every relation,
  separately.** Not the degree *distribution* — the degree of each individual
  node, which is strictly stronger and is what a double-edge swap gives;
* edge count and therefore density, per relation;
* acyclicity of ``isa``. A hypernym graph is a DAG, and a scramble that returned
  cycles would differ from the real graph in a *structural* way as well as a
  semantic one, which is exactly the confound the control exists to remove. The
  swap is constrained to a fixed topological order of the original DAG, so every
  rewiring is still a DAG and ``ancestors`` still terminates for the honest
  reason rather than because of its loop guard.

What is destroyed: which node sits under which, what has which parts, what is
made of what, which adjective is a value of which dimension. A ``penguin`` in
the scrambled graph is under some node with the same number of children as
``bird`` had, and is made of whatever ``bird``'s substance slot got rewired to.

The one thing this control cannot do
------------------------------------

It cannot distinguish "the model used the semantics" from "the model used the
*specific* graph it was trained on". A model that memorises the scrambled graph
does as well on the scrambled arm as a model that memorises the real one. That
is what the permutation guard is for and it is a separate instrument: a winner
must still win when the symbols are permuted *and* the graph permuted with them.
"""

from __future__ import annotations

import random
from typing import Sequence

from .graph import KnowledgeGraph

__all__ = ["degree_preserving_shuffle", "topological_rank", "swap_report"]


def topological_rank(edges: Sequence[tuple[int, int]], n: int) -> list[int]:
    """A rank per node such that every edge goes from a higher rank to a lower.

    Kahn's algorithm over the reversed edges, with the frontier kept sorted so
    the answer is a pure function of the input rather than of set iteration
    order. Nodes in a cycle — there are none in ``isa``, but the function is not
    allowed to loop if a caller hands it one — land after everything else.
    """
    succ: dict[int, list[int]] = {}
    indeg = [0] * n
    for a, b in edges:
        succ.setdefault(b, []).append(a)
        indeg[a] += 1
    frontier = sorted(i for i in range(n) if indeg[i] == 0)
    order: list[int] = []
    while frontier:
        nxt: list[int] = []
        for v in frontier:
            order.append(v)
            for w in succ.get(v, ()):
                indeg[w] -= 1
                if indeg[w] == 0:
                    nxt.append(w)
        frontier = sorted(nxt)
    # `set(order)` hoisted out of the comprehension deliberately: inside it, it
    # was rebuilt once per candidate and the pass was O(n^2). At WordNet's
    # 13,810 nodes that is slow and survivable; at the CSKG projection's 36,257
    # it is 1.3 billion operations and was the whole cost of building the
    # control. Same result -- `order` is not modified by the comprehension.
    placed = set(order)
    order.extend(sorted(i for i in range(n) if i not in placed))
    rank = [0] * n
    for pos, v in enumerate(order):
        rank[v] = pos
    return rank


def _swap_relation(pairs: list[tuple[int, int]], rng: random.Random,
                   rank: list[int] | None, rounds: int) -> tuple[list[tuple[int, int]], dict]:
    """Double-edge swap: (a,b),(c,d) -> (a,d),(c,b).

    Out-degree of ``a`` and ``c`` and in-degree of ``b`` and ``d`` are unchanged
    by construction. A swap is rejected if it would make a self-loop, a
    duplicate, or — when ``rank`` is given — an edge that runs the wrong way in
    the original topological order.
    """
    m = len(pairs)
    if m < 2:
        return list(pairs), {"attempts": 0, "swaps": 0}
    cur = list(pairs)
    present = set(cur)
    attempts = swaps = 0
    target = rounds * m
    while attempts < target:
        attempts += 1
        i = rng.randrange(m)
        j = rng.randrange(m)
        if i == j:
            continue
        a, b = cur[i]
        c, d = cur[j]
        if a == d or c == b:
            continue
        if (a, d) in present or (c, b) in present:
            continue
        if rank is not None and not (rank[a] > rank[d] and rank[c] > rank[b]):
            continue
        present.discard((a, b)); present.discard((c, d))
        present.add((a, d)); present.add((c, b))
        cur[i] = (a, d); cur[j] = (c, b)
        swaps += 1
    return cur, {"attempts": attempts, "swaps": swaps}


def degree_preserving_shuffle(kg: KnowledgeGraph, *, seed: int = 20260814,
                              rounds: int = 20, name: str | None = None,
                              ) -> KnowledgeGraph:
    """The scrambled control for ``kg``.

    ``rounds`` is swap *attempts* per edge, not successes; the report from
    :func:`swap_report` says how many landed, and a control whose edges were
    barely moved is not a control. That number belongs in the write-up next to
    the result, for the same reason a fitted scalar belongs there with its grid.
    """
    rng = random.Random(seed)
    out: dict[str, list[tuple[int, int]]] = {}
    for rel in sorted(kg.edges):
        pairs = [tuple(e) for e in kg.edges[rel]]
        rank = topological_rank(pairs, len(kg)) if rel == "isa" else None
        out[rel], _ = _swap_relation(pairs, rng, rank, rounds)
    return kg.replacing_edges(
        out, name=name or f"{kg.name}-shuffled")


def swap_report(kg: KnowledgeGraph, *, seed: int = 20260814, rounds: int = 20) -> dict:
    """How thoroughly the control actually rewired, per relation.

    Two numbers per relation: the share of successful swaps and the share of
    original edges that survive. A control that preserved most of its edges
    would look like a control and behave like the treatment — the failure mode
    ``notes/lessons/2026-08-13-a-control-that-could-fail.md`` is about — so this
    is measured rather than assumed.
    """
    rng = random.Random(seed)
    rep: dict[str, dict] = {}
    for rel in sorted(kg.edges):
        pairs = [tuple(e) for e in kg.edges[rel]]
        rank = topological_rank(pairs, len(kg)) if rel == "isa" else None
        new, stats = _swap_relation(pairs, rng, rank, rounds)
        kept = len(set(pairs) & set(new))
        rep[rel] = {"edges": len(pairs), "attempts": stats["attempts"],
                    "swaps": stats["swaps"],
                    "kept": kept, "kept_share": kept / max(len(pairs), 1)}
    return rep
