"""Where an answer lives, relative to the node being asked about.

A *route* is a structural path — "my slot-0 sibling", "the same slot of another
subtree with my parent's head" — and it is the only thing worth carrying between
two episodes of this curriculum. A remembered symbol is worthless because the
next episode will not contain it; a route is a fact about shape and survives
intact.

The vocabulary lives here rather than inside one model because two of them need
it for different reasons. :mod:`symbolic_ai_models.models.analogy` recovers the
route that explains a *remembered* case and replays it. :mod:`
symbolic_ai_models.models.episodic` fits the route against the episode in front
of it. Same alphabet, different way of choosing a letter.

Everything here works on plain arrays — ``labels``, ``parent``, ``slot`` — so it
serves a live :class:`~symbolic_ai_models.models.symbolic.GraphView` and a stored
case without either having to know about the other.
"""

from __future__ import annotations

__all__ = ["MAX_STEP", "ROUTES", "follow", "explaining_routes"]


#: Structural paths from a node to somewhere else in the same episode. A route
#: is the *answer to* "where does the answer live, relative to me" — and it is
#: the only thing an analogy is allowed to carry across, because it is the only
#: part of a remembered case that survives the vocabulary being reinvented.
MAX_STEP = 4


def follow(labels, parent, slot, node: int, route: tuple) -> int | None:
    """Walk one structural route from ``node``; ``None`` if it does not exist."""
    kind = route[0]
    if kind == "parent":
        p = parent[node]
        return p if p >= 0 else None
    if kind == "grandparent":
        p = parent[node]
        return parent[p] if p >= 0 and parent[p] >= 0 else None
    if kind == "sibling":
        p = parent[node]
        if p < 0:
            return None
        sibs = [j for j, q in enumerate(parent) if q == p and j != node]
        return sibs[route[1]] if route[1] < len(sibs) else None
    if kind == "child":
        kids = [j for j, q in enumerate(parent) if q == node]
        return kids[route[1]] if route[1] < len(kids) else None
    if kind == "aunt":
        p = parent[node]
        g = parent[p] if p >= 0 else -1
        if g < 0:
            return None
        aunts = [j for j, q in enumerate(parent) if q == g and j != p]
        return aunts[route[1]] if route[1] < len(aunts) else None
    if kind == "prev":
        for j in range(node - 1, -1, -1):
            if labels[j] is not None:
                return j
        return None
    if kind == "peer":
        # the same slot of another subtree whose head matches: coreference
        # *within* the episode, which is structure, not a remembered symbol
        p = parent[node]
        if p < 0 or labels[p] is None:
            return None
        head = labels[p]
        for other, other_label in enumerate(labels):
            if other != p and other_label == head:
                kids = [j for j, q in enumerate(parent) if q == other]
                if slot[node] < len(kids):
                    return kids[slot[node]]
        return None
    return None


def _routes_impl() -> tuple:
    return (("peer",), ("parent",), ("grandparent",), ("prev",),
            *[("sibling", k) for k in range(MAX_STEP)],
            *[("child", k) for k in range(MAX_STEP)],
            *[("aunt", k) for k in range(MAX_STEP)])



#: The whole vocabulary, fixed. Fixed on purpose: a route set that grew with the
#: data would be another thing fitted on training, and the point of a route is
#: that it is a claim about shape rather than a claim about this corpus.
ROUTES = _routes_impl()


def explaining_routes(labels, parent, slot, node: int, answer) -> list[tuple]:
    """Every route that, followed from ``node``, lands on ``answer``.

    The plural matters. Several routes often agree — in a scene, the peer and
    the previous sibling can be the same node — and which of them is the *reason*
    is exactly what a single episode cannot tell you. Returning all of them lets
    the caller decide by weight of evidence instead of by tie-break.
    """
    out = []
    for route in ROUTES:
        target = follow(labels, parent, slot, node, route)
        if target is not None and labels[target] == answer:
            out.append(route)
    return out
