"""``graph_to_expr`` / ``expr_to_graph``, asserted over **every** lesson.

Not over a fixture. ``test_encoding_is_lossless`` existed, passed, and missed a
tokenizer that was deleting underscores, because its fixture happened to draw
episodes containing none —
``notes/lessons/2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property.md``.
So the round trip is checked on all 179 lessons and, separately, on an
*alphabet* of adversarial labels rather than on whatever the curriculum
happened to render.

If this test fails, every number the `006` line produces is a translation
artefact rather than an IR effect, which is one of the refutation conditions in
``notes/decisions/2026-08-14-the-ir-is-a-knob.md``.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.data.curriculum import generate, lesson_ids
from symbolic_ai_core.data.term_graph import NODE_TYPES, TermGraph
from symbolic_ai_lean.expr import Const, Lit, pretty
from symbolic_ai_lean.translate import expr_to_graph, graph_to_expr


@pytest.fixture(scope="module")
def every_lesson_graph():
    return [(ep.lesson_id, ep.graph)
            for ep in generate(lesson_ids(), n=1, seed0=500)]


def test_the_curriculum_is_all_179_lessons(every_lesson_graph):
    """A guard on the guard: if generation quietly returns six lessons, the
    round-trip test below is a fixture again and nobody would notice."""
    assert len({lid for lid, _ in every_lesson_graph}) == 179


def test_round_trip_is_the_identity_on_every_lesson(every_lesson_graph):
    for lesson_id, g in every_lesson_graph:
        back = expr_to_graph(graph_to_expr(g))
        assert back.to_dict() == g.to_dict(), lesson_id


def test_round_trip_is_the_identity_on_a_second_seed():
    """Different seeds draw different *shapes* — lists of other lengths, deeper
    scenes, strings that exploded differently."""
    for ep in generate(lesson_ids(), n=1, seed0=777):
        assert expr_to_graph(graph_to_expr(ep.graph)).to_dict() == ep.graph.to_dict()


#: Labels chosen to break an encoder, not to be typical. The empty string is
#: here because every structural node carries one.
ADVERSARIAL = ["", " ", "_", "__init__", "a_b", "Term.pred", "(", ")", '"',
               "«»", "\\", "\n", "λ", "→", "0", "-1", "3.142", "Sort 0",
               "a" * 200, "ident", "x y z"]


@pytest.mark.parametrize("label", ADVERSARIAL)
def test_a_label_survives_the_round_trip_whatever_it_says(label):
    g = TermGraph()
    root = g.add(label, "pred", -1, 0)
    g.add(label, "ident", root, 0)
    g.add("", "list", root, 1)
    assert expr_to_graph(graph_to_expr(g)).to_dict() == g.to_dict()


@pytest.mark.parametrize("type_", [t for t in NODE_TYPES])
def test_every_node_type_in_the_alphabet_round_trips(type_):
    """On the alphabet of node types, not on the ones a fixture drew."""
    g = TermGraph()
    root = g.add("head", "pred", -1, 0)
    g.add("x", type_, root, 0)
    assert expr_to_graph(graph_to_expr(g)).to_dict() == g.to_dict()


def test_a_structural_node_that_acquired_a_label_still_round_trips():
    """`TermGraph.add` is public and nothing stops a label on a `list`. Emitting the
    label conditionally would make the encoding lossy exactly here."""
    g = TermGraph()
    root = g.add("surprise", "list", -1, 0)
    g.add("x", "ident", root, 0)
    assert expr_to_graph(graph_to_expr(g)).to_dict() == g.to_dict()


def test_a_deep_chain_does_not_recurse_off_the_stack():
    g = TermGraph()
    parent = g.add("root", "pred", -1, 0)
    for _ in range(400):
        parent = g.add("x", "pred", parent, 0)
    assert expr_to_graph(graph_to_expr(g)).to_dict() == g.to_dict()


def test_an_empty_graph_is_refused_rather_than_silently_encoded():
    with pytest.raises(ValueError):
        graph_to_expr(TermGraph())


def test_a_non_term_expression_is_refused():
    with pytest.raises(ValueError):
        expr_to_graph(Const("nope"))


def test_the_encoding_is_readable(every_lesson_graph):
    _, g = every_lesson_graph[0]
    src = pretty(graph_to_expr(g))
    assert src.startswith("(Term.")
