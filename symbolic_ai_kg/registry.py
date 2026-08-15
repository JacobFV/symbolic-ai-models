"""The graph is a parameter.

Every caller asks for a graph **by name**. There is exactly one place that knows
a name is a file, and it is here. A larger graph arriving later is a new row in
:data:`_SOURCES` and a new data file; nothing above this module changes, which
is the whole reason the seam was built before the big integration rather than
after it.

Names shipped now:

``wordnet``
    the vendored projection of Princeton WordNet 3.0. See
    :mod:`symbolic_ai_kg._vendor` for provenance.
``wordnet-shuffled``
    its degree-preserving edge permutation — the control, derived at load time
    from the same bytes with a pinned seed, so it cannot drift independently of
    its treatment.

Loading is cached by name because a graph is immutable in use and building the
adjacency index over ~50k edges is not free. The cache is keyed on the name
only; there is no way to hand ``load`` different bytes under the same name,
which is deliberate — that is how a control ends up sharing a name with the
thing it controls.
"""

from __future__ import annotations

from typing import Callable

from . import _vendor
from .graph import KnowledgeGraph
from .scramble import degree_preserving_shuffle

__all__ = ["KG_NAMES", "load", "census", "SHUFFLE_SEED", "SHUFFLE_ROUNDS"]

#: Pinned so the control is reproducible and so a run directory can be read
#: without refitting anything. See
#: ``notes/lessons/2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable.md``.
SHUFFLE_SEED = 20260814
SHUFFLE_ROUNDS = 20


def _wordnet() -> KnowledgeGraph:
    return KnowledgeGraph.load(_vendor.GRAPH_PATH)


def _wordnet_shuffled() -> KnowledgeGraph:
    return degree_preserving_shuffle(_wordnet(), seed=SHUFFLE_SEED,
                                     rounds=SHUFFLE_ROUNDS,
                                     name="wordnet-shuffled")


_SOURCES: dict[str, Callable[[], KnowledgeGraph]] = {
    "wordnet": _wordnet,
    "wordnet-shuffled": _wordnet_shuffled,
}

#: Every graph this repo can be asked for, in a stable order.
KG_NAMES: tuple[str, ...] = tuple(sorted(_SOURCES))

_CACHE: dict[str, KnowledgeGraph] = {}


def load(name: str) -> KnowledgeGraph:
    """The graph with this name, built once per process."""
    if name not in _SOURCES:
        raise KeyError(f"unknown knowledge graph {name!r}; have {list(KG_NAMES)}")
    kg = _CACHE.get(name)
    if kg is None:
        kg = _CACHE[name] = _SOURCES[name]()
    return kg


def census() -> dict[str, dict[str, int]]:
    """Node and edge counts for every registered graph.

    Printed rather than asserted in prose: the control's whole claim is that its
    census matches its treatment's, and a claim that is checkable in one glance
    is checked more often than one that is not.
    """
    return {n: load(n).census() for n in KG_NAMES}
