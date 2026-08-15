"""The elaborator: does it read the hidden answer, and does it read vocabulary?

Two of these are the controls that killed headlines elsewhere in this repo,
pointed at the kernel before the kernel gets a model:

* **Renaming invariance.** ``ensemble-001``'s 1.14-bit headline went 0.467 ->
  0.038 under a consistent renaming. A filter whose verdicts move when every
  symbol is renamed is reading vocabulary, and its prune rate is memorisation.
* **The hidden answer.** The elaboration is built from visible nodes only. Swap
  every hidden label for something else and not one verdict may move — a
  property no amount of care establishes and only an assertion catches
  (``notes/lessons/2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property.md``).

Plus rollback fidelity, which is what makes checking fifty-five candidates
against one elaboration equal to fifty-five elaborations.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.data.curriculum import generate, lesson_ids
from symbolic_ai_core.data.graph import Graph
from symbolic_ai_lean.elaborate import elaborate
from symbolic_ai_lean.expr import pretty

MODES = ("open", "declared", "closed")


@pytest.fixture(scope="module")
def episodes():
    return list(generate(lesson_ids()[:24], n=1, seed0=500))


def _holes(g: Graph) -> list[int]:
    """A deterministic spread of holes: every seventh symbol-bearing node."""
    cand = [i for i in range(len(g))
            if g.labels[i] and g.types[i] not in ("list", "tuple", "record", "nil")]
    return cand[::7][:12]


def _all_verdicts(g: Graph, hidden, mode):
    e = elaborate(g, hidden, mode=mode)
    return {(i, c): e.verdict(i, c)
            for i in hidden for c in e.candidate_labels(i)}


# ------------------------------------------------------------- the controls
@pytest.mark.parametrize("mode", MODES)
def test_verdicts_are_invariant_under_a_consistent_renaming(episodes, mode):
    for ep in episodes:
        g = ep.graph
        hidden = _holes(g)
        if not hidden:
            continue
        symbols = sorted({l for l in g.labels if l})
        rename = {s: f"sym{k:04d}" for k, s in enumerate(symbols)}
        renamed = Graph(labels=[rename.get(l, l) for l in g.labels],
                        types=list(g.types), parent=list(g.parent),
                        slot=list(g.slot), depth=list(g.depth))
        a = _all_verdicts(g, hidden, mode)
        b = _all_verdicts(renamed, hidden, mode)
        assert {(i, rename.get(c, c)): v for (i, c), v in a.items()} == b, \
            f"{ep.lesson_id} moved under renaming"


@pytest.mark.parametrize("mode", MODES)
def test_no_verdict_depends_on_the_hidden_answer(episodes, mode):
    """The one thing a reader of a masked term may not do."""
    for ep in episodes:
        g = ep.graph
        hidden = _holes(g)
        if not hidden:
            continue
        tampered = Graph(labels=[("ZZZ_tampered" if i in hidden else l)
                                 for i, l in enumerate(g.labels)],
                         types=list(g.types), parent=list(g.parent),
                         slot=list(g.slot), depth=list(g.depth))
        assert _all_verdicts(g, hidden, mode) == _all_verdicts(tampered, hidden, mode)


@pytest.mark.parametrize("mode", MODES)
def test_checking_a_candidate_leaves_the_elaboration_exactly_as_it_was(episodes, mode):
    """Rollback fidelity. Without it, candidate 2 is checked against a state
    candidate 1 modified, and the prune rate depends on candidate order."""
    for ep in episodes[:8]:
        g = ep.graph
        hidden = _holes(g)
        if not hidden:
            continue
        e = elaborate(g, hidden, mode=mode)
        before = [pretty(e.ctx.instantiate(t)) for t in e.T]
        decls = {k: pretty(e.ctx.instantiate(v)) for k, v in e.decl.items()}
        for i in hidden:
            for c in e.candidate_labels(i):
                e.verdict(i, c)
        assert [pretty(e.ctx.instantiate(t)) for t in e.T] == before
        assert {k: pretty(e.ctx.instantiate(v))
                for k, v in e.decl.items()} == decls


@pytest.mark.parametrize("mode", MODES)
def test_candidate_order_does_not_change_any_verdict(episodes, mode):
    for ep in episodes[:8]:
        g = ep.graph
        hidden = _holes(g)
        if not hidden:
            continue
        e = elaborate(g, hidden, mode=mode)
        for i in hidden:
            cands = e.candidate_labels(i)
            forward = {c: e.verdict(i, c) for c in cands}
            backward = {c: e.verdict(i, c) for c in reversed(cands)}
            assert forward == backward


# --------------------------------------------------- what the kernel refuses
def _binary_pred_graph() -> tuple[Graph, int]:
    """``(likes alice bob)`` twice over, with the second ``alice`` masked."""
    g = Graph()
    r = g.add("", "list", -1, 0)
    p1 = g.add("likes", "pred", r, 0)
    g.add("alice", "ident", p1, 0)
    g.add("bob", "ident", p1, 1)
    p2 = g.add("likes", "pred", r, 1)
    hole = g.add("carol", "ident", p2, 0)
    g.add("dave", "ident", p2, 1)
    return g, hole


def test_a_binary_predicate_cannot_fill_a_leaf_hole():
    """Refused by the **occurs check**, not by the saturation rule: the hole's
    type *is* the metavariable standing for ``likes``'s first argument, so
    solving it to ``?a → ?b → Prop`` would need a cyclic type. Worth pinning by
    reason — a filter's prune rate is the sum of several mechanisms and only
    some of them are about types."""
    g, hole = _binary_pred_graph()
    e = elaborate(g, [hole], mode="open")
    assert e.verdict(hole, "likes") == "mismatch"
    assert e.verdict(hole, "alice") == "ok"


def test_a_leaf_cannot_fill_a_two_argument_hole():
    g, _ = _binary_pred_graph()
    hole = 4                                    # the second `likes` head
    e = elaborate(g, [hole], mode="open")
    assert e.verdict(hole, "likes") == "ok"
    assert e.verdict(hole, "alice") == "saturation"


def test_a_numeral_cannot_fill_a_position_pinned_to_a_predicate():
    g = Graph()
    r = g.add("holds", "pred", -1, 0)
    g.add("2", "num", r, 0)
    inner = g.add("p", "pred", r, 1)
    g.add("x", "ident", inner, 0)
    hole = g.add("q", "pred", r, 1)             # same slot, so same type: Prop
    g.add("y", "ident", hole, 0)
    e = elaborate(g, [hole], mode="open")
    assert e.verdict(hole, "2") == "mismatch"       # Nat against Prop, rigidly
    assert e.verdict(hole, "p") == "ok"


def test_a_field_name_cannot_repeat_inside_one_record():
    g = Graph()
    r = g.add("", "record", -1, 0)
    f1 = g.add("query", "field", r, 0)
    g.add("x", "ident", f1, 0)
    hole = g.add("scene", "field", r, 1)
    g.add("y", "ident", hole, 0)
    e = elaborate(g, [hole], mode="open")
    assert e.is_field_hole(hole)
    assert e.verdict(hole, "query") == "duplicate field"
    assert e.verdict(hole, "x") == "ok"


def test_an_undeclared_symbol_is_possible_open_and_an_error_declared():
    g = Graph()
    r = g.add("", "record", -1, 0)
    f = g.add("roster", "field", r, 0)
    hole = g.add("alice", "ident", f, 0)
    e_open = elaborate(g, [hole], mode="open")
    e_decl = elaborate(g, [hole], mode="declared")
    assert e_open.verdict(hole, "roster") == "ok"
    assert e_decl.verdict(hole, "roster") == "undeclared"


def test_a_symbol_the_elaborator_gave_up_on_is_possible_in_every_mode():
    """Demotion means *no information*, and no information may not be a
    rejection. Measured: turning it into one cut 221 of the 232 gold answers
    the `declared` arm lost, which would have read as a fact about the
    curriculum rather than about one branch."""
    g = Graph()
    r = g.add("", "list", -1, 0)
    p = g.add("push", "pred", r, 0)             # `push` as a binary predicate
    g.add("a", "ident", p, 0)
    g.add("b", "ident", p, 1)
    q = g.add("isa", "pred", r, 1)
    g.add("push", "ident", q, 0)                # and as a leaf: incompatible
    hole = g.add("c", "ident", q, 1)
    for mode in MODES:
        e = elaborate(g, [hole], mode=mode)
        assert "push" in e.demoted, mode
        assert e.verdict(hole, "push") == "ok", mode


# ------------------------------------------------------------- health/coverage
def test_the_elaborator_types_almost_everything(episodes):
    """Coverage, reported as coverage. `type_acc` under an elaborator is near
    1.000 by construction and is never quoted as a lift — see the
    pre-registration's named trap."""
    nodes = typed = 0
    for ep in episodes:
        e = elaborate(ep.graph, [], mode="open")
        nodes += len(ep.graph)
        typed += len(ep.graph) - len(e.untyped)
    assert typed / nodes > 0.99


def test_elaboration_is_deterministic(episodes):
    for ep in episodes[:6]:
        a = elaborate(ep.graph, [], mode="closed")
        b = elaborate(ep.graph, [], mode="closed")
        assert [pretty(a.ctx.instantiate(t)) for t in a.T] == \
               [pretty(b.ctx.instantiate(t)) for t in b.T]
