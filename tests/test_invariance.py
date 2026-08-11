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
#: `ilp` and `evidence` have since been removed too, for the same reason: the
#: structural fallback in `RuleBasedModel` answers an abstention with a
#: memorised label, which is worth a great deal of accuracy (`ilp` 0.186 ->
#: 0.349) and costs the guarantee. `routes` opts out and remains the subject.
#:
#: `analogy` was on this list and has been removed on purpose. It gained a
#: memorising fallback for the contexts where route transfer finds nothing,
#: which took it from 0.221 to 0.337 and above the label floor for the first
#: time. Memorisation and equivariance are genuinely incompatible, and on this
#: curriculum — where every scored label recurs in training — the accuracy is
#: worth more. `routes` remains the model that keeps the guarantee, so the
#: property is still demonstrated by something.
STRUCTURE_ONLY = ["routes"]


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


def test_the_sweep_reports_renaming_for_every_node_run():
    """The table could not show the difference it most needs to show.

    `corefer` and `workspace` tie at 0.357 label accuracy and are -0.003 and
    -0.130 under renaming -- one is answering from structure and the other
    substantially from vocabulary, and nothing in the printed table said so.
    Renaming was a manual probe run once, by hand, on four models.
    """
    from pathlib import Path

    from symbolic_ai_models.train import TrainConfig, train

    out = Path("/tmp/claude-renaming-check")
    summary = train(TrainConfig(
        model="ilp", tasks=("node",), task_weights={"node": 1.0},
        lessons=["unification", "symbol_grounding"], n_train=8, n_eval=4,
        steps=0, vocab_size=400, max_nodes=64, max_len=192, batch_size=4,
        device="cpu", amp=False, out=str(out)))

    got = summary["renaming"]
    assert 0.0 <= got["label_acc"] <= 1.0
    assert 0.0 <= got["renamed_label_acc"] <= 1.0
    assert got["drop"] == got["label_acc"] - got["renamed_label_acc"]
    assert got["symbols"] >= 2, "a renaming of fewer than two symbols is not one"


def test_renaming_is_not_reported_for_a_run_without_the_node_task():
    """It is a property of the masked-node answer; there is nothing to permute
    the answer of when only next-token prediction was scored."""
    from pathlib import Path

    from symbolic_ai_models.train import TrainConfig, train

    summary = train(TrainConfig(
        model="ngram", tasks=("lm",), task_weights={"lm": 1.0},
        lessons=["unification"], n_train=6, n_eval=2, steps=0,
        vocab_size=400, max_nodes=64, max_len=192, batch_size=4,
        device="cpu", amp=False, out="/tmp/claude-renaming-lm"))
    assert "renaming" not in summary
