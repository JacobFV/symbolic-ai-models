"""``TermGraph -> Expr`` and back, as the identity.

The syntax encoding, not the elaborated one. A node becomes a constant named for
its term type, applied to its label and then to its children::

    (isa alice person)   ->   Term.pred "isa" (Term.ident "alice") (Term.ident "person")

Three decisions, each of which the round-trip test over all 179 lessons would
otherwise have caught the hard way:

* **Every node emits its label**, including the structural ones whose label is
  always ``""``. Emitting the ``Lit`` conditionally would make the encoding
  lossy the moment a structural node acquired a label, and ``TermGraph.add`` is a
  public method that nothing stops from doing exactly that.
* **The label is a ``Lit``, not a ``Const`` name.** A label is an arbitrary
  string; a ``Const`` called ``Term.pred`` would be indistinguishable from a
  node labelled ``Term.pred``.
* **Rebuilding walks breadth-first**, because :func:`term_graph_from_json` assigns
  indices from a queue rather than a stack. Its own docstring says "pre-order"
  and it is not; ``test_round_trip_is_the_identity_on_every_lesson`` is what
  says so, over every graph of all 179 lessons rather than over a fixture.
  ``notes/lessons/2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property.md``
  is the reason that test covers rather than samples: ``test_encoding_is_lossless``
  passed for months while the tokenizer deleted underscores, because its fixture
  happened to draw episodes with none.
"""

from __future__ import annotations

from symbolic_ai_core.data.term_graph import TermGraph

from .expr import App, Const, Expr, Lit, apps, spine

__all__ = ["graph_to_expr", "expr_to_graph", "NODE_PREFIX"]

#: Namespace for the syntax constructors, one per term type.
NODE_PREFIX = "Term."


def graph_to_expr(g: TermGraph, root: int = 0) -> Expr:
    """The subtree at ``root``, as one ``Expr``. Iterative: a curriculum graph
    can be 512 nodes deep in the worst case and Python's stack is not."""
    if not len(g):
        raise ValueError("cannot encode an empty graph")
    kids: dict[int, list[int]] = {i: [] for i in range(len(g))}
    for i, p in enumerate(g.parent):
        if 0 <= p < len(g):
            kids[p].append(i)

    built: dict[int, Expr] = {}
    order: list[int] = []
    stack = [root]
    while stack:                                     # post-order, iteratively
        i = stack.pop()
        order.append(i)
        stack.extend(kids[i])
    for i in reversed(order):
        built[i] = apps(Const(NODE_PREFIX + g.types[i]),
                        [Lit(g.labels[i])] + [built[c] for c in kids[i]])
    return built[root]


def expr_to_graph(e: Expr) -> TermGraph:
    """The inverse. Node order is breadth-first, matching ``term_graph_from_json``."""
    g = TermGraph()
    queue: list[tuple[Expr, int, int]] = [(e, -1, 0)]
    while queue:
        node, parent, slot = queue.pop(0)
        head, args = spine(node)
        if not isinstance(head, Const) or not head.name.startswith(NODE_PREFIX):
            raise ValueError(f"not a term node: {head!r}")
        if not args or not isinstance(args[0], Lit):
            raise ValueError(f"term node with no label: {head.name}")
        idx = g.add(args[0].value, head.name[len(NODE_PREFIX):], parent, slot)
        queue.extend((c, idx, k) for k, c in enumerate(args[1:]))
    return g


def is_term_node(e: Expr) -> bool:
    """Whether ``e`` is a syntax node this module produced."""
    head, args = spine(e)
    return (isinstance(head, Const) and head.name.startswith(NODE_PREFIX)
            and bool(args) and isinstance(args[0], Lit))
