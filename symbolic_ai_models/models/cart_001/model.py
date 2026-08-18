"""CART: infill in a chosen order, propagate each fill, backtrack on a contradiction.

Cheng, Dai and Sun, *Constraint-Anchored Reasoning Traces* (arXiv:2607.16727,
2026-07-18). Natural-language reasoning runs normally but periodically emits
machine-checkable assertions; a propagator checks them against the partial state
and a contradiction rolls back to the last consistent checkpoint. They report the
**cascade rate** — given one wrong step, how often the next is wrong — falling
from 0.65 to 0.14.

What this repo does today, and the gap
--------------------------------------

:meth:`RuleBasedModel._forward_graph` calls ``node_votes(view)`` exactly **once**
per episode, on a view in which every hidden node is still hidden. An episode's
ten holes are therefore ten independent questions asked against one identical
context: nothing a fill implies ever reaches the other holes, and nothing is ever
un-filled. There is no decode order because there is no decode.

These three models put one there. They wrap :class:`~symbolic_ai_models.models.frontier_001.model.FrontierModel`
— the strongest label head on ``runs/full179`` — and change the **decoder alone**,
so a difference between any two of these rows and ``frontier-001``'s row is a
property of the decode and not of the reasoning.

This is a harness change and it is arm'd like one
--------------------------------------------------

``notes/lessons/2026-08-13-the-harness-moves-more-than-the-models.md``: harness
decisions in this repo span 0.15 to 2.0 lift where models span 0.1. Letting hole
*j* read hole *i*'s committed fill is a **contract change** — it hands the
reasoner strictly more visible context — and it will move the number whether or
not one line of constraint logic works. So three arms are registered together and
the pre-registration in
``notes/decisions/2026-08-16-cart-preregistration-order-propagation-backtracking.md``
says what each was expected to score before any of them ran:

``cart-001``
    Order, propagation and backtracking. The treatment.
``cart-order``
    The **same** fill order and the same sequential context, with the domains and
    the backtracker removed. Isolates decode order from constraint logic. Without
    it the two are confounded, and ordering alone is known to matter here.
``cart-noop``
    ``cart-001``'s code path exactly — domains computed, assertions checked,
    backtracking armed — with the assertion replaced by one that is **always**
    satisfiable. Predicted to tie ``cart-order``; if it does not, the machinery
    is doing something by itself and the treatment row is unreadable.

The assertions, and why they are learned rather than written
-------------------------------------------------------------

Every constraint is fitted from the training episodes' *unmasked* graphs. A
hand-written list of constraints is a fitted parameter with no error bar, and
``frontier-001``'s own docstring levels that criticism at ``ruleinduce``.

``arity``
    A label may take the arities it has been seen taking. This is
    :func:`symbolic_ai_lean.gate.arity_accepts` moved from a Lean-kernel
    comparison to a decoder, generous in the same direction: a symbol seen with
    two arities is accepted at both. That check beat a Lean kernel; see
    ``notes/findings/`` on the gate.
``type``
    A label may take the node types it has been seen taking.
``slot``
    The propagator proper. Committing a parent's label restricts its children:
    ``slot_domain[(parent label, slot)]`` is the set of labels seen in that slot
    under that parent label in training. Kept only where the evidence is real —
    at least :attr:`CartModel.min_slot_support` observations — and only where the
    domain is *small* enough to constrain anything, because a domain of four
    hundred symbols costs memory and forbids nothing.

Coreference is deliberately **not** propagated.
:func:`symbolic_ai_core.data.batch.relation_matrix` withholds the coreference
edges of hidden nodes, so hidden-to-hidden coreference is not readable from a
``GraphView`` and a propagator that used it would be reading the answer.

The decode
----------

Holes are filled one at a time, most-constrained first. "Most constrained" is
scored from what is available in **every** arm — the number of the hole's tree
neighbours that are still masked, then the wrapped model's own confidence — so
the ordering rule is literally identical across the three and only the fills can
differ.

After each commit the view is rewritten with that label and type visible, so the
next hole's rules read it: ``frontier``'s ``copy:`` and ``map:`` resolvers decline
whenever their path is masked, and a commit turns some of those declines into
answers. That is the mechanism by which decode order alone can move the score, and
it is exactly what ``cart-order`` exists to measure.

When the argmax label is outside the hole's current domain, the highest-weight
in-domain candidate is taken instead. When *no* candidate is in the domain, the
hole is a contradiction: the decoder rolls back the most recent commit, forbids
the label it had chosen there, and re-decides. :attr:`CartModel.max_backtracks`
bounds the search, because an infilling decoder that can spend unbounded time on
one episode is not a model, it is a solver.

What is emitted
---------------

The votes finally returned are the ones each hole was answered with **at the
moment it was committed**, so the reported distribution is the one the decoder
actually acted on. Confidences are the wrapped model's, unmodified: a decoder is
not entitled to become more confident because it ran in a different order, and
this repo has paid for a harness change that quietly moved a calibration four
times over.
"""

from __future__ import annotations

import collections
from typing import Any, Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.term_graph import NODE_TYPES, STRUCTURAL, TYPE_TO_ID
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..frontier_001.model import FrontierModel
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, Votes

__all__ = ["CartModel", "CartOrderModel", "CartNoopModel", "commit"]


def commit(view: GraphView, node: int, label: int,
           type_id: int | None) -> GraphView:
    """A copy of ``view`` with ``node`` no longer hidden.

    A copy rather than a mutation because the caller holds the pre-commit view as
    its checkpoint — that is the whole of "backtrack to the last consistent
    state", and it is one object reference rather than an undo log.

    ``type_id`` of ``None`` commits the label and leaves the type unknown, which
    is what the type head abstaining should mean. Filling in a plausible type
    there would be the decoder inventing evidence for itself, and every arm would
    inherit the invention equally — which makes it invisible in the comparison
    rather than harmless.

    ``rel`` is shared and left untouched. The coreference edges of hidden nodes
    were withheld by the collator and this decoder has no way to restore them; a
    commit therefore makes a label visible and does **not** invent an edge. That
    is a real limit on what can propagate here and it is a limit in the honest
    direction.
    """
    out = GraphView(
        labels=list(view.labels), types=list(view.types), parent=view.parent,
        slot=view.slot, depth=view.depth, rel=view.rel,
        hidden=[h for h in view.hidden if h != node], tok=view.tok,
        text=view.text, language=view.language)
    out.labels[node] = int(label)
    out.types[node] = (None if type_id is None or not
                       0 <= int(type_id) < len(NODE_TYPES)
                       else NODE_TYPES[int(type_id)])
    return out


@register("cart-001",
          doc="Constraint-anchored infilling over frontier-001: order, propagation, backtracking.")
class CartModel(FrontierModel):
    """Sequential infilling with learned domains and rollback."""

    LEARNED = FrontierModel.LEARNED + (
        "arity_of", "types_of", "slot_domain", "known_labels")

    #: Whether the learned domains restrict anything. ``False`` in ``cart-order``.
    propagates = True
    #: Whether the checking and backtracking machinery runs at all. ``True`` in
    #: ``cart-noop`` as well, where the domains are the whole vocabulary, so that
    #: arm exercises the identical code path with an assertion that cannot fail.
    checks = True

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        #: How many times a ``(parent label, slot)`` pair must be seen before its
        #: domain is believed. A domain fitted from two observations forbids the
        #: rest of the vocabulary on no evidence, which is a constraint that
        #: manufactures contradictions rather than catching them.
        self.min_slot_support = int(cfg.get("cart_min_slot_support", 8))
        #: Domains wider than this are dropped rather than stored. A domain of
        #: several hundred symbols does not constrain a decoder that is choosing
        #: among a handful of voted candidates; it only costs memory.
        self.max_domain = int(cfg.get("cart_max_domain", 64))
        #: Rollbacks allowed per episode. Bounds the decode: a model that can
        #: spend unbounded time on one graph is a solver wearing a model's name.
        self.max_backtracks = int(cfg.get("cart_max_backtracks", 8))
        #: label id -> arities it was seen with.
        self.arity_of: dict[int, set[int]] = {}
        #: label id -> type ids it was seen with.
        self.types_of: dict[int, set[int]] = {}
        #: (parent label id, slot) -> labels seen there.
        self.slot_domain: dict[tuple[int, int], frozenset[int]] = {}
        #: Every label the training graphs contained. A candidate outside this is
        #: unconstrainable rather than forbidden — the curriculum invents
        #: vocabulary per episode, so "never seen" is the common case and
        #: forbidding it would forbid most correct answers.
        self.known_labels: set[int] = set()

    # ---- fitting ------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        super().learn(episodes, tok)
        self._fit_constraints(episodes, tok)

    def _fit_constraints(self, episodes: Sequence[Episode],
                         tok: SymbolTokenizer) -> None:
        """Read the assertions off the training graphs, unmasked.

        Unmasked is the right surface: these are facts about the *language* the
        generator writes in, not about what a particular masking happened to
        reveal, and every one of them is available to a reader of the training
        episodes. Nothing here touches an evaluation seed.
        """
        arity: dict[int, set[int]] = collections.defaultdict(set)
        types: dict[int, set[int]] = collections.defaultdict(set)
        slots: dict[tuple[int, int], collections.Counter] = collections.defaultdict(
            collections.Counter)
        known: set[int] = set()
        for ep in episodes:
            g = ep.graph
            n = len(g)
            kids = [0] * n
            for i in range(n):
                p = g.parent[i]
                if 0 <= p < n:
                    kids[p] += 1
            ids = [tok.label_id(lab) if lab else -1 for lab in g.labels]
            for i in range(n):
                lid = ids[i]
                if lid < 0 or g.types[i] in STRUCTURAL:
                    continue
                known.add(lid)
                arity[lid].add(kids[i])
                types[lid].add(TYPE_TO_ID.get(g.types[i], -1))
                p = g.parent[i]
                if 0 <= p < n and ids[p] >= 0:
                    slots[(ids[p], min(g.slot[i], 8))][lid] += 1
        self.arity_of = {k: set(v) for k, v in arity.items()}
        self.types_of = {k: set(v) for k, v in types.items()}
        self.known_labels = known
        self.slot_domain = {}
        for key, table in slots.items():
            if sum(table.values()) < self.min_slot_support:
                continue
            if len(table) > self.max_domain:
                continue
            self.slot_domain[key] = frozenset(table)

    # ---- the assertions ------------------------------------------------
    def allows(self, view: GraphView, node: int, label: int,
               type_id: int | None) -> bool:
        """Is committing ``label`` at ``node`` consistent with what is visible?

        Three checks, every one of them generous where the training evidence is
        thin: a label the corpus never showed is *allowed*, because the
        curriculum invents vocabulary per episode and a decoder that forbade the
        unseen would forbid most correct answers. The constraint has to be able
        to say "I have no opinion" or it stops being a constraint and becomes a
        vocabulary filter.

        ``cart-noop`` overrides this to ``True``, which is the no-op assertion.
        """
        if not self.propagates:
            return True
        if label not in self.known_labels:
            return True
        want = len(view.children(node))
        seen = self.arity_of.get(label)
        if seen is not None and want not in seen:
            return False
        if type_id is not None:
            ts = self.types_of.get(label)
            if ts is not None and int(type_id) not in ts:
                return False
        p = view.parent[node]
        if 0 <= p < len(view.labels) and view.labels[p] is not None:
            dom = self.slot_domain.get((int(view.labels[p]),
                                        min(view.slot[node], 8)))
            if dom is not None and label not in dom:
                return False
        return True

    # ---- the decode ----------------------------------------------------
    def _priority(self, view: GraphView, node: int, confidence: float) -> tuple:
        """Most-constrained first, scored identically in all three arms.

        Two terms, in order: how many of the hole's tree neighbours are still
        masked (fewer is more constrained), then how sure the wrapped model is.
        Neither term reads a domain, which is what makes the *ordering rule* the
        same object in ``cart-001`` and ``cart-order`` rather than two rules that
        happen to agree on easy episodes.
        """
        neigh = [view.parent[node]] + view.children(node) + view.siblings(node)
        unknown = sum(1 for j in neigh
                      if j < 0 or j >= len(view.labels) or view.labels[j] is None)
        return (unknown, -float(confidence), node)

    def _ask(self, view: GraphView, node: int) -> tuple[Votes, Votes]:
        """The wrapped reasoner's opinion about one hole on the current view."""
        return self._one_node_votes(view, node)

    def _one_node_votes(self, view: GraphView,
                        node: int) -> tuple[Votes, Votes]:
        """``FrontierModel.node_votes`` restricted to a single node.

        The decode re-asks every *remaining* hole once per commit, because a
        commit is exactly what changes which hole is most constrained — so the
        outer loop is quadratic in holes whatever this method does. What
        restricting buys is the inner factor: asking the wrapped model about one
        node instead of about all of them turns O(h³) rule matches into O(h²).
        On ``configs/full179.toml`` the three arms cost 9m31s together against
        frontier's own ~1m, which is the ~10x the ordering is being bought for.

        The votes are identical either way — ``frontier``'s answer at a node
        depends on the view and the node and on nothing about the other holes —
        so this is a cost change and not a behaviour change.
        """
        stash = view.hidden
        view.hidden = [node]
        try:
            got = super().node_votes(view)
        finally:
            view.hidden = stash
        return got.get(node, (ABSTAIN, ABSTAIN))

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        holes = list(view.hidden)
        out: dict[int, tuple[Votes, Votes]] = {}
        current = view
        # `(view before the commit, node, votes, labels already ruled out)` — the
        # checkpoint stack. Rolling back is restoring one reference.
        stack: list[tuple[GraphView, int, tuple[Votes, Votes], set[int]]] = []
        remaining = set(holes)
        budget = self.max_backtracks

        while remaining:
            # Score every remaining hole on the *current* view and take the most
            # constrained. Recomputing each round rather than fixing an order up
            # front is the point: a commit changes which holes are constrained,
            # and an order fixed in advance cannot see that.
            scored = []
            for node in remaining:
                votes = self._ask(current, node)
                conf = votes[0][1] if votes[0] is not ABSTAIN else 0.0
                scored.append((self._priority(current, node, conf), node, votes))
            scored.sort(key=lambda row: row[0])
            _, node, votes = scored[0]
            label_votes, type_votes = votes
            banned = set()
            picked = self._choose(current, node, label_votes, type_votes, banned)

            if picked is None and self.checks and stack and budget > 0:
                # Contradiction. Roll back the most recent commit, forbid the
                # label it took, and let the loop re-decide from there. The hole
                # that was rolled back rejoins `remaining`; this one does too,
                # because a different fill upstream may make it satisfiable.
                budget -= 1
                current, undone, undone_votes, undone_banned = stack.pop()
                prev = out.pop(undone, None)
                if prev is not None:
                    chosen = max(prev[0][0].items(),
                                 key=lambda kv: kv[1])[0] if prev[0][0] else None
                    if chosen is not None:
                        undone_banned.add(int(chosen))
                remaining.add(undone)
                retry = self._choose(current, undone, undone_votes[0],
                                     undone_votes[1], undone_banned)
                if retry is not None:
                    label, type_id, kept = retry
                    out[undone] = (kept, undone_votes[1])
                    stack.append((current, undone, undone_votes, undone_banned))
                    current = commit(current, undone, label, type_id)
                    remaining.discard(undone)
                continue

            remaining.discard(node)
            if picked is None:
                # Nothing satisfiable and nothing left to undo: answer with what
                # the reasoner said and let the back-off price it, which is what
                # every other model in the registry does when it is stuck.
                out[node] = votes
                continue
            label, type_id, kept = picked
            out[node] = (kept, type_votes)
            stack.append((current, node, votes, banned))
            current = commit(current, node, label, type_id)

        return out

    def _choose(self, view: GraphView, node: int, label_votes: Votes,
                type_votes: Votes, banned: set[int]):
        """The best allowed candidate, or ``None`` if the hole is contradictory.

        Returns ``(label, type id, votes to report)``. The reported votes are the
        wrapped model's table with the forbidden entries removed and the
        confidence **unchanged** — a decoder that pruned candidates and then
        renormalised its confidence upward would be claiming certainty it did not
        earn, which is the shape of four calibration failures already in
        ``RESEARCH_LOG.md``.
        """
        table, conf = label_votes
        if not table or conf <= 0.0:
            return None
        type_id = None
        ttable, tconf = type_votes
        if ttable and tconf > 0.0:
            type_id = int(max(ttable.items(), key=lambda kv: kv[1])[0])
        ok = {int(sym): w for sym, w in table.items()
              if int(sym) not in banned
              and self.allows(view, node, int(sym), type_id)}
        if not ok:
            return None
        label = max(ok.items(), key=lambda kv: kv[1])[0]
        return label, type_id, (ok, conf)

    # ---- reporting ----------------------------------------------------
    def render(self) -> str:
        head = (f"cart: propagates={self.propagates} checks={self.checks} "
                f"slot domains={len(self.slot_domain)} "
                f"arity entries={len(self.arity_of)} "
                f"known labels={len(self.known_labels)}")
        return head + "\n" + super().render()


@register("cart-order",
          doc="cart with propagation off: the same fill order and sequential context, no logic.")
class CartOrderModel(CartModel):
    """The ordering arm. Same decode, same commits, no constraint may bite.

    This is the control the parked note asks for, and it is the one that decides
    how to read ``cart-001``. Sequential infilling hands each hole strictly more
    visible context than the current harness does, and that alone is expected to
    move the score. If ``cart-001`` beats ``frontier-001`` by more than it beats
    this row, the gain is decode order and the constraint logic is decoration.
    """

    propagates = False
    checks = False


@register("cart-noop",
          doc="cart with an always-satisfiable assertion: the machinery without the logic.")
class CartNoopModel(CartModel):
    """The no-op-constraint arm: every check runs, no check can fail.

    Identical code path to ``cart-001`` — domains fitted, :meth:`allows` called at
    every candidate, the backtracker armed and the checkpoint stack maintained —
    with the assertion replaced by ``True``. Predicted to tie ``cart-order`` to
    about three decimals. If it does not, something in the machinery is changing
    predictions by itself and every number in the table is unreadable until it is
    found.
    """

    propagates = False
    checks = True

    def allows(self, view: GraphView, node: int, label: int,
               type_id: int | None) -> bool:
        return True
