"""The data layer: graphs, vocabulary, batches.

These are the tests that matter most, because everything downstream inherits
whatever the encoding got wrong, and a silently mis-encoded graph produces a
training curve that looks fine.
"""

from __future__ import annotations

import numpy as np
import pytest

from symmodels.data.batch import (REL, collate_graph, collate_text,
                                  relation_matrix)
from symmodels.data.curriculum import Episode, generate, resolve_lessons
from symmodels.data.graph import TYPE_TO_ID, Graph, graph_from_json
from symmodels.data.tokenizer import SymbolTokenizer

LESSONS = ["unification", "symbol_grounding", "context_free_language"]


@pytest.fixture(scope="module")
def episodes() -> list[Episode]:
    return list(generate(LESSONS, n=4))


# ---- graphs ---------------------------------------------------------------
def test_graph_is_a_tree_in_preorder(episodes):
    """Every node but the root has a parent that already appeared."""
    for ep in episodes:
        assert ep.graph.parent[0] == -1
        for i, p in enumerate(ep.graph.parent[1:], start=1):
            assert 0 <= p < i, f"{ep.lesson_id}: node {i} has parent {p}"
            assert ep.graph.depth[i] == ep.graph.depth[p] + 1


def test_named_fields_become_labelled_nodes():
    """A record's field names are nodes, so they can be masked and predicted."""
    g = graph_from_json({"t": "record", "fields": {
        "query": {"t": "ident", "v": "x"},
        "scene": {"t": "list", "items": [{"t": "ident", "v": "o1"}]}}})
    fields = {g.labels[i] for i, t in enumerate(g.types) if t == "field"}
    assert fields == {"query", "scene"}


def test_strings_are_exploded_into_symbols():
    """A bracket string is structure, not one opaque leaf."""
    g = graph_from_json({"t": "str", "v": "(())"})
    assert len(g) == 5                       # the str node plus four brackets
    assert [g.labels[i] for i in range(1, 5)] == ["(", "(", ")", ")"]
    assert all(g.types[i] == "char" for i in range(1, 5))


def test_traversal_is_bounded_breadth_first():
    """Hitting max_nodes loses depth, not whole top-level fields.

    Depth-first truncation would keep the first field's entire subtree and drop
    the rest, which changes what the episode is about rather than blurring it.
    """
    deep = {"t": "record", "fields": {
        c: {"t": "list", "items": [{"t": "ident", "v": f"{c}{i}"} for i in range(20)]}
        for c in "abcde"}}
    g = graph_from_json(deep, max_nodes=12)
    assert len(g) == 12
    assert {g.labels[i] for i, t in enumerate(g.types) if t == "field"} == set("abcde")


def test_graph_round_trips_through_json(episodes):
    for ep in episodes:
        assert Graph.from_dict(ep.graph.to_dict()).to_dict() == ep.graph.to_dict()


# ---- relations ------------------------------------------------------------
def test_relation_matrix_records_slots_and_coreference():
    g = Graph()
    root = g.add("f", "pred", -1, 0)
    a = g.add("x", "ident", root, 0)
    b = g.add("x", "ident", root, 1)
    m = relation_matrix(g, 3)

    assert m[root, root] == REL["self"]
    assert m[a, root] == REL["parent_0"], "a is the slot-0 child of the root"
    assert m[b, root] == REL["parent_1"], "b is the slot-1 child"
    assert m[root, a] == REL["child_0"]
    assert m[root, b] == REL["child_1"]
    # Siblings beat coreference: the more specific fact about the pair wins.
    assert m[a, b] == REL["sibling"]


def test_coreference_keys_on_the_label_string():
    """Two nodes with the same invented name are related even out of vocabulary."""
    g = Graph()
    g.add("f", "pred", -1, 0)
    g.add("zz9", "ident", 0, 0)
    g.add("g", "pred", 0, 1)
    g.add("zz9", "ident", 2, 0)
    m = relation_matrix(g, 4)
    assert m[1, 3] == REL["same_label"] and m[3, 1] == REL["same_label"]


def test_unlabelled_nodes_are_never_coreferent():
    g = Graph()
    g.add("", "list", -1, 0)
    g.add("", "list", 0, 0)
    g.add("", "list", 0, 1)
    m = relation_matrix(g, 3)
    assert m[1, 2] == REL["sibling"]
    assert m[0, 0] == REL["self"]


# ---- tokenizer ------------------------------------------------------------
def test_encoding_is_lossless(episodes):
    tok = SymbolTokenizer.build([ep.text for ep in episodes], max_vocab=400)
    for ep in episodes:
        assert tok.decode(tok.encode(ep.text)) == ep.text


def test_byte_fallback_covers_unseen_scripts():
    """A vocabulary built on English still round-trips other languages."""
    tok = SymbolTokenizer.build(["hello world"], max_vocab=300)
    for text in ["这是一个测试", "çalışkan öğrenci", "🙂 emoji"]:
        assert tok.decode(tok.encode(text)) == text


def test_saved_vocabulary_reloads_identically(tmp_path, episodes):
    tok = SymbolTokenizer.build([ep.text for ep in episodes], max_vocab=400)
    tok.save(tmp_path / "v.json")
    assert SymbolTokenizer.load(tmp_path / "v.json").itos == tok.itos


# ---- batches --------------------------------------------------------------
def test_text_batch_targets_are_the_next_token(episodes):
    tok = SymbolTokenizer.build([ep.text for ep in episodes], max_vocab=400)
    b = collate_text(episodes, tok)
    real = b.pad_mask[:, 1:]
    assert (b.target_tokens[:, :-1][real] == b.tokens[:, 1:][real]).all()
    # Nothing is predicted from a padded position.
    assert (b.target_tokens[~b.pad_mask] < 0).all()
    assert b.causal and b.rel is None


def test_masked_nodes_are_hidden_from_the_input(episodes):
    tok = SymbolTokenizer.build([ep.text for ep in episodes], max_vocab=400)
    b = collate_graph(episodes, tok, mask_rate=0.5,
                      rng=np.random.default_rng(0))
    masked = b.target_types >= 0
    assert masked.any()
    # Every masked position carries the mask symbol and the mask type: the
    # answer is not still sitting in the input.
    assert (b.tokens[masked] == tok.mask_id).all()
    assert (b.types[masked] == TYPE_TO_ID["mask"]).all()
    # Every scored label sits at a masked position.
    assert (b.target_tokens[~masked] < 0).all()
    assert not b.causal and b.rel is not None


def test_structural_nodes_are_scored_on_type_only(episodes):
    """A list has no label, so predicting it must not count towards the score."""
    tok = SymbolTokenizer.build([ep.text for ep in episodes], max_vocab=400)
    b = collate_graph(episodes, tok, mask_all=True)
    structural = b.types.new_tensor([TYPE_TO_ID[t] for t in ("list", "tuple", "record")])
    for ep_i, ep in enumerate(episodes):
        for i, t in enumerate(ep.graph.types[:b.length]):
            if TYPE_TO_ID[t] in structural.tolist():
                assert b.target_tokens[ep_i, i] < 0
                assert b.target_types[ep_i, i] >= 0


def test_masking_withholds_the_coreference_edges_of_hidden_nodes():
    """The masked-node task must not be answerable off the relation matrix.

    ``same_label`` is derived from the very string being predicted, so an edge
    saying "this hidden node shares a label with node 3" hands over the answer.
    Structural edges are kept — those are facts about the tree, not about the
    hidden symbol.
    """
    g = Graph()
    g.add("f", "pred", -1, 0)
    g.add("x", "ident", 0, 0)
    g.add("g", "pred", 0, 1)
    g.add("x", "ident", 2, 0)

    open_ = relation_matrix(g, 4)
    assert open_[1, 3] == REL["same_label"], "the edge exists when nothing is hidden"

    hidden = relation_matrix(g, 4, hidden=[3])
    assert hidden[1, 3] == REL["none"] and hidden[3, 1] == REL["none"]
    # ...while the structure around node 3 survives untouched.
    assert hidden[3, 2] == REL["parent_0"]
    assert hidden[2, 3] == REL["child_0"]
    assert hidden[2, 1] == open_[2, 1]


def test_collate_graph_hides_coreference_for_masked_nodes(episodes):
    """The same guarantee, through the collator the trainer actually calls."""
    tok = SymbolTokenizer.build([ep.text for ep in episodes], max_vocab=400)
    b = collate_graph(episodes, tok, mask_all=True)
    # With everything masked, no coreference edge may remain anywhere.
    assert not (b.rel == REL["same_label"]).any()


def test_every_episode_gets_at_least_one_question(episodes):
    tok = SymbolTokenizer.build([ep.text for ep in episodes], max_vocab=400)
    b = collate_graph(episodes, tok, mask_rate=0.0,
                      rng=np.random.default_rng(0))
    assert ((b.target_types >= 0).sum(dim=1) >= 1).all()


# ---- the curriculum contract ---------------------------------------------
def test_train_and_eval_seeds_cannot_overlap():
    train = list(generate(["unification"], n=3, seed0=0))
    evaluation = list(generate(["unification"], n=3, seed0=1_000_000))
    assert not ({e.instance_id for e in train} & {e.instance_id for e in evaluation})


def test_generation_is_a_pure_function_of_the_seed():
    a = list(generate(["unification"], n=2, seed0=7))
    b = list(generate(["unification"], n=2, seed0=7))
    assert [x.to_dict() for x in a] == [x.to_dict() for x in b]


def test_lesson_selectors_resolve():
    assert len(resolve_lessons("all")) >= 170
    assert resolve_lessons("unification") == ["unification"]
    assert set(resolve_lessons("unification,quantification")) == {
        "unification", "quantification"}
    with pytest.raises(ValueError):
        resolve_lessons("no_such_lesson")
