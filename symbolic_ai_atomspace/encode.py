"""``Graph -> AtomSpace -> Graph``, and the reason it is not the obvious map.

The obvious map is the one the pre-registration wrote down: a term node with
children becomes an ``Expression`` whose head is its label and whose tail is its
slots, a leaf becomes a ``Symbol``, and the node type rides as ``(: label
type)``. **It is not invertible, and it fails for two separate reasons**, both
of which are properties of an atomspace rather than accidents of this encoder:

1. **Atoms are unique by content.** A ``Graph`` is a tree of *occurrences*; an
   ``AtomSpace`` is a set of *values*. Two sibling leaves both labelled ``a``
   are two nodes and one atom, so the arity of their parent is not recoverable.
   Measured on this curriculum in
   ``tests/test_atomspace.py::test_content_addressing_would_collapse_occurrences``
   — the collapse is not hypothetical and it is not rare.
2. **``(: label type)`` keys the type on the label**, and labels repeat across
   types. The empty label alone is carried by every one of the five
   ``STRUCTURAL`` types.

So the encoding names occurrences. Each graph node ``i`` becomes an opaque
occurrence symbol ``nI``, and five relations carry everything the flat arrays
carry::

    (node n3 3)          the occurrence, and its position in the node array
    (: n3 pred)          its type -- the typing atom, first-class as MeTTa has it
    (label n3 parent)    its label, always present, "" included
    (child n1 0 n3)      n3 is the child of n1 in slot 0
    (root n0)            the node with no parent

``depth`` is not stored: it is a function of ``parent`` that ``Graph.add``
computes, so storing it would let a space hold a graph that ``Graph`` itself
cannot represent. The decoder recomputes it, and the round trip asserts on the
recomputed value, which is a strictly stronger check.

The one redundancy, stated
--------------------------
``(node n3 3)`` names a position that the symbol ``n3`` also spells. It is there
so the decoder never parses an identity out of a string: the occurrence symbol
is opaque and the ordering is *data*. A decoder that read the digits would pass
this module's tests and break the moment an occurrence was named anything else —
which is precisely what a conformance oracle emitting its own names would do.

What the space can express that ``Graph`` cannot
-------------------------------------------------
Everything above is a faithful re-encoding, and a faithful re-encoding is a
rename. The native operations are in :mod:`symbolic_ai_atomspace.metta` and
:mod:`symbolic_ai_atomspace.roles`, and the concrete thing they buy is named in
:data:`DERIVED_RULES`: a typed, slot-selected sibling is one conjunctive query
here and is inexpressible in the twelve-route ``CLAWS`` enum, which is why
``omegaclaw_reach-001`` had to add a branch to reach ``ilp``'s best clause.
"""

from __future__ import annotations

from typing import Sequence

from symbolic_ai_core.data.graph import Graph
from symbolic_ai_core.graphview import GraphView

from .atoms import Atom, E, G, S, Symbol, V
from .metta import Rule, rule
from .space import AtomSpace

__all__ = ["NODE", "TYPE", "LABEL", "CHILD", "ROOT", "HIDDEN",
           "occurrence", "graph_to_atomspace", "atomspace_to_graph",
           "view_to_atomspace", "term_atom", "DERIVED_RULES"]

#: The five relation heads. Named constants rather than string literals at
#: seventy call sites, because a typo in one of them would produce a space that
#: is merely missing a relation — every query over it returns nothing, no error
#: is raised, and the model quietly degrades to its back-off. That is the
#: failure shape ``notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-
#: the-models-name.md`` is about.
NODE = S("node")
TYPE = S(":")
LABEL = S("label")
CHILD = S("child")
ROOT = S("root")
#: Marks a node the reader is being asked to predict. Only ever in a space built
#: from a :class:`GraphView`; a ``Graph`` has no hidden nodes.
HIDDEN = S("hidden")

#: The type an occurrence carries when its true type is hidden. A distinct
#: symbol rather than the absence of a typing atom, so that "this node's type is
#: unknown" is something a query can *ask about* instead of something it can
#: only fail to find.
UNKNOWN_TYPE = S("%hidden%")


def occurrence(i: int) -> Symbol:
    """The opaque name of graph node ``i``."""
    return S(f"n{i}")


# ---------------------------------------------------------------------------
# Graph -> AtomSpace
# ---------------------------------------------------------------------------
def graph_to_atomspace(graph: Graph, space: AtomSpace | None = None) -> AtomSpace:
    """Every node of ``graph`` as five relations. Lossless; see the module doc."""
    space = space if space is not None else AtomSpace()
    for i in range(len(graph)):
        name = occurrence(i)
        space.add(E(NODE, name, G(i)))
        space.add(E(TYPE, name, S(graph.types[i])))
        space.add(E(LABEL, name, S(graph.labels[i])))
        parent = graph.parent[i]
        if parent < 0:
            space.add(E(ROOT, name))
        else:
            space.add(E(CHILD, occurrence(parent), G(graph.slot[i]), name))
    return space


def atomspace_to_graph(space: AtomSpace) -> Graph:
    """The inverse. ``depth`` is recomputed from ``parent``, never read back.

    Raises rather than guesses. A space missing a node's type or label is not a
    graph with a default in that slot, it is a broken encoding, and the one
    thing this function must never do is return something plausible — the whole
    line's attributability rests on this being the identity.
    """
    index: dict[Atom, int] = {}
    for b in space.query(E(NODE, V("id"), V("i"))):
        idx = b["i"]
        index[b["id"]] = int(getattr(idx, "value", -1))
    if not index:
        return Graph()

    n = len(index)
    if sorted(index.values()) != list(range(n)):
        raise ValueError("occurrence indices are not 0..n-1")

    types: list[str | None] = [None] * n
    labels: list[str | None] = [None] * n
    for b in space.query(E(TYPE, V("id"), V("t"))):
        i = index.get(b["id"])
        if i is not None:
            types[i] = getattr(b["t"], "name", None)
    for b in space.query(E(LABEL, V("id"), V("s"))):
        i = index.get(b["id"])
        if i is not None:
            labels[i] = getattr(b["s"], "name", None)

    parent = [-1] * n
    slot = [0] * n
    for b in space.query(E(CHILD, V("p"), V("k"), V("c"))):
        i = index.get(b["c"])
        p = index.get(b["p"])
        if i is None or p is None:
            raise ValueError("a child link names an occurrence with no node atom")
        parent[i] = p
        slot[i] = int(getattr(b["k"], "value", 0))

    for i in range(n):
        if types[i] is None or labels[i] is None:
            raise ValueError(f"occurrence {i} has no type or no label atom")

    out = Graph()
    for i in range(n):
        # `Graph.add` derives `depth` from the parent it is handed, so a
        # pre-order build recomputes the whole depth array. Nodes are added in
        # index order, and a parent is always at a lower index in a graph
        # `graph_from_json` produced -- which the check below enforces rather
        # than assumes, since a space is not obliged to have come from one.
        if parent[i] >= i:
            raise ValueError(f"occurrence {i} has a parent at or after it")
        out.add(labels[i], types[i], parent[i], slot[i])
    return out


# ---------------------------------------------------------------------------
# the masked view, which is what a model actually sees
# ---------------------------------------------------------------------------
def view_to_atomspace(view: GraphView, space: AtomSpace | None = None) -> AtomSpace:
    """A :class:`GraphView` as a space. Hidden nodes keep their structure.

    Labels are the tokenizer's integer ids, carried as grounded integers rather
    than as symbols, so that nothing reading the space can confuse a label with
    a type or with an occurrence name.

    A hidden node gets ``(hidden nI)`` and ``(: nI %hidden%)`` and **no**
    ``label`` atom. There is no field anywhere holding the value being
    predicted, which is the same guarantee :class:`GraphView` itself makes.
    """
    space = space if space is not None else AtomSpace()
    for i in range(len(view)):
        name = occurrence(i)
        space.add(E(NODE, name, G(i)))
        type_ = view.types[i]
        space.add(E(TYPE, name, S(type_) if type_ is not None else UNKNOWN_TYPE))
        label = view.labels[i]
        if label is None:
            space.add(E(HIDDEN, name))
        else:
            space.add(E(LABEL, name, G(int(label))))
        parent = view.parent[i]
        if parent < 0:
            space.add(E(ROOT, name))
        else:
            space.add(E(CHILD, occurrence(parent), G(int(view.slot[i])), name))
    return space


# ---------------------------------------------------------------------------
# the content view, used only to measure what content addressing would cost
# ---------------------------------------------------------------------------
def term_atom(graph: Graph, root: int = 0) -> Atom:
    """The subtree at ``root`` as a nested expression — the *content* of a node.

    This is the encoding the pre-registration proposed and this module rejects.
    It is kept, and exercised by a test, because "the obvious map is lossy" is a
    claim that should be measured rather than asserted: two occurrences with
    equal ``term_atom`` are two nodes an atomspace would store once.
    """
    kids = [i for i, p in enumerate(graph.parent) if p == root]
    head: Atom = S(graph.labels[root] or graph.types[root])
    if not kids:
        return head
    kids.sort(key=lambda i: (graph.slot[i], i))
    return E(head, *(term_atom(graph, k) for k in kids))


# ---------------------------------------------------------------------------
# the native operations: derived relations that no flat array carries
# ---------------------------------------------------------------------------
#: Rules whose conclusions are the structure ``CLAWS`` cannot name.
#:
#: ``sibling`` is the one that matters. The twelve-route enum has ``sibling0``
#: and ``prev_sibling`` and no way to say *which* sibling, and ``ilp``'s
#: strongest discovered clause is a typed, slot-selected one — so
#: ``omegaclaw_reach-001`` had to add a branch, and still lost (+0.226 against
#: +0.234). Here it is a rule, and selecting the sibling by type and slot is a
#: query against the conclusion rather than a second rule.
DERIVED_RULES: tuple[Rule, ...] = (
    rule("(= (sibling $a $k $b $j) (, (child $p $k $a) (child $p $j $b)))"),
    rule("(= (gparent $g $a $k $c) (, (child $g $a $p) (child $p $k $c)))"),
)


def derived_space(view: GraphView, *, max_atoms: int = 20_000) -> AtomSpace:
    """A view's space with :data:`DERIVED_RULES` chained in, once.

    Not used by the registered models — they read the base relations directly
    for cost — and kept because it is the honest demonstration of the native
    operation, exercised by ``tests/test_atomspace.py``.
    """
    from .metta import chain
    space = view_to_atomspace(view)
    chain(space, DERIVED_RULES, max_rounds=1, max_atoms=max_atoms)
    return space


def spaces_for(graphs: Sequence[Graph]) -> list[AtomSpace]:
    """Convenience for the round-trip test; no cleverness."""
    return [graph_to_atomspace(g) for g in graphs]
