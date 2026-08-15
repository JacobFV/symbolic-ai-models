"""Parse-tree infilling: the masked-node task with a bigger, shaped hole.

The masked-node task hides 15% of a term graph's nodes and asks for each one's
label and type. That **is** infilling, and the renderer this repo owns is
deterministic and tested, so ``graph -> text`` is exact and free. Generation
then reduces to graph completion followed by a render, and the missing piece is
not a decoder but the fact that nobody had turned the mask rate up or changed
the *shape* of what is hidden. See
``notes/decisions/2026-08-14-generation-is-parse-tree-infilling.md``.

Two things are hidden here that scattered masking does not hide:

* :class:`SubtreeMaskedNode` removes **whole constituents** rather than
  independent nodes. Scattered masking almost always leaves a hidden node's
  parent, siblings and children visible — filling that gap is interpolation
  inside a graph that is mostly given. Drawing subtrees to the same budget keeps
  the amount hidden fixed and varies only the shape of the hole, which is what
  makes the two comparable.
* :class:`AnswerMaskedNode` removes the constituent the curriculum itself asks
  about: the node whose label is the episode's answer. That is the curriculum's
  own question put to the graph instead of to the text, and it is the row to
  read against `answer_acc`, which every rule-based model scores 0.000 on.

**What these tasks do not ask.** The tree skeleton is never hidden in any mode
— `relation_matrix` withholds a masked node's coreference edges and keeps
parent, child-slot, sibling and ancestor. So this is infilling on a *given*
shape at every rate, not tree generation, and every number here is an upper
bound on generation for that reason.

Registered beside ``node``, never in place of it. ``node`` at ``mask_rate=0.15``
is what every published number in this repo means and it is unchanged: the
scattered draw is the same arithmetic on the same generator in the same order.
"""

from __future__ import annotations

from .masked_node import MaskedNode

__all__ = ["SubtreeMaskedNode", "AnswerMaskedNode", "AnswerOnceMaskedNode"]


class SubtreeMaskedNode(MaskedNode):
    """Hide whole subtrees, to the same node budget as ``node``'s mask rate."""

    name = "nodesub"
    mask_mode = "subtree"


class AnswerMaskedNode(MaskedNode):
    """Hide the episode's answer, wherever it sits in the graph, and its subtree.

    ``mask_rate`` is ignored — what is hidden is decided by the answer — and the
    ~21% of episodes whose answer is nowhere in their graph are **unscored**
    rather than scored zero. ``ansnode_*`` is the score restricted to the
    positions that carry the answer itself, which is the number comparable with
    `answer_acc`; ``label_*`` additionally includes the answer node's
    descendants, which 8 of 283 answer-bearing episodes have.

    Three asymmetries all favour this over `answer_acc` and are stated in the
    pre-registration rather than discovered later: the position of the answer is
    given, only the covered subset is scored, and one symbol is named rather
    than a string spelled. A score near zero here is therefore a clean
    refutation; a score well above the floor is not by itself a clean
    confirmation.
    """

    name = "nodeans"
    mask_mode = "answer"


class AnswerOnceMaskedNode(AnswerMaskedNode):
    """`nodeans`'s control: hide the answer's **first** occurrence only.

    `nodeans` hides every node carrying the answer, which is right — leaving one
    visible turns the curriculum's question into a copy exercise — and which
    also means the pointer head cannot answer it at all, because a pointer emits
    the label of a *visible* node and there is none. A zero from a pointer on
    `nodeans` is therefore a fact about the task's design, not about the
    pointer.

    This row hides one occurrence, so on the episodes with more than one (about
    44% of the answer-bearing ones, mean 2.03 copies) the copy route is open and
    the same models face the same question with the mechanism they have. Without
    this row the rung-3 null cannot be told apart from the design that produced
    it.
    """

    name = "nodeans1"
    mask_mode = "answer_one"
