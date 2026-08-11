"""Rename every symbol; see whose score survives.

The claim is **equivariance**, not invariance. Renaming changes the correct
answer too, so predictions should move exactly as the world moved — which makes
accuracy the quantity to compare, and logits the wrong one. Whatever a model
loses here is the share of its score that was riding on vocabulary rather than
on structure.
"""

from __future__ import annotations

import pytest

from symbolic_ai_models.data.curriculum import generate
from symbolic_ai_models.invariance import (build_renaming, label_accuracy,
                                           rename_episodes)
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.train import TrainConfig, build_tokenizer

LESSONS = ["symbol_grounding", "unification", "center_embedding"]

#: Models whose method reads structure only, and which must therefore keep
#: their accuracy exactly. Deliberately short: it is the list of claims that
#: have actually been checked, not the list of models that sound structural.
#: `analogy` earned its place by having its memorising readout removed — it
#: failed this test when it was first written, which is why the test exists.
STRUCTURE_ONLY = ["ilp", "evidence", "analogy"]


@pytest.fixture(scope="module")
def fitted():
    train = list(generate(LESSONS, n=40))
    evaluation = list(generate(LESSONS, n=10, seed0=1_000_000))
    tok = build_tokenizer(TrainConfig(vocab_size=1500), train)
    renaming = build_renaming(train + evaluation, tok)
    return train, evaluation, rename_episodes(evaluation, renaming), tok, renaming


def test_the_renaming_is_a_derangement(fitted):
    """Nothing may map to itself, or a model could pass without being tested."""
    *_, renaming = fitted
    assert len(renaming) > 10
    assert all(k != v for k, v in renaming.mapping.items())
    assert len(set(renaming.mapping.values())) == len(renaming.mapping)


def test_renaming_moves_both_surfaces_together(fitted):
    """Graph and prose must agree afterwards, or the test measures a mismatch."""
    _, evaluation, renamed, _, renaming = fitted
    for before, after in zip(evaluation, renamed):
        assert after.graph.labels == [renaming.apply(l) if l else l
                                      for l in before.graph.labels]
        assert after.answer == renaming.apply(before.answer) or \
            after.answer != before.answer or not renaming.mapping
        assert len(after.graph) == len(before.graph)


def test_renaming_preserves_structure(fitted):
    """Only the names change; the tree must be untouched."""
    _, evaluation, renamed, _, _ = fitted
    for before, after in zip(evaluation, renamed):
        assert after.graph.parent == before.graph.parent
        assert after.graph.types == before.graph.types
        assert after.graph.slot == before.graph.slot


@pytest.mark.parametrize("name", STRUCTURE_ONLY)
def test_a_structure_only_model_keeps_its_accuracy(name, fitted):
    """Fitted on the original episodes, scored on the renamed ones.

    Refitting after the rename would ask whether the method can learn a
    relabelled world, which is easier and not the question.
    """
    train, evaluation, renamed, tok, _ = fitted
    model = build(name, ModelConfig(vocab_size=len(tok), max_len=96))
    model.fit_on(train, tok)
    before = label_accuracy(model, evaluation, tok)
    after = label_accuracy(model, renamed, tok)
    assert after == pytest.approx(before, abs=0.02), (
        f"{name} lost {before - after:.3f} accuracy to a pure renaming, so that "
        f"much of its score was vocabulary rather than structure")


def test_a_counting_model_is_hurt_by_renaming(fitted):
    """The control. If `ngram` did *not* drop, the renaming is not biting."""
    train, evaluation, renamed, tok, _ = fitted
    model = build("ngram", ModelConfig(vocab_size=len(tok), max_len=96))
    model.fit_on(train, tok)
    before = label_accuracy(model, evaluation, tok)
    after = label_accuracy(model, renamed, tok)
    assert before - after > 0.05, "renaming should cost a counting model dearly"
