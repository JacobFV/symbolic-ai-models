"""Every architecture, against the contract the harness assumes of all of them.

The point of these is that they are parameterised over the registry: a new model
is covered the moment it is registered, and cannot be added without answering
both questions, respecting causality, and tolerating a batch of one.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from symmodels.data.batch import collate_graph, collate_text
from symmodels.data.curriculum import generate
from symmodels.data.tokenizer import SymbolTokenizer
from symmodels.models import ModelConfig, build, model_names
from symmodels.tasks import make_task

LESSONS = ["unification", "symbol_grounding", "center_embedding"]


@pytest.fixture(scope="module")
def fixtures():
    episodes = list(generate(LESSONS, n=3))
    tok = SymbolTokenizer.build([e.text for e in episodes], max_vocab=400)
    return episodes, tok


@pytest.fixture(scope="module")
def cfg(fixtures):
    _, tok = fixtures
    return ModelConfig(vocab_size=len(tok), d_model=32, n_layers=2, n_heads=4,
                       d_ff=64, dropout=0.0)


@pytest.mark.parametrize("name", model_names())
def test_answers_both_questions(name, fixtures, cfg):
    """One model, both tasks, both heads, shapes that line up with the targets."""
    episodes, tok = fixtures
    model = build(name, cfg)
    for batch in (collate_text(episodes, tok),
                  collate_graph(episodes, tok, rng=np.random.default_rng(0))):
        out = model(batch)
        assert out.symbol_logits.shape == (*batch.tokens.shape, cfg.vocab_size)
        assert out.type_logits.shape[:2] == batch.tokens.shape
        assert torch.isfinite(out.symbol_logits).all()


@pytest.mark.parametrize("name", model_names())
def test_gradients_reach_every_parameter(name, fixtures, cfg):
    """A parameter with no gradient is a wiring bug, not a design choice."""
    episodes, tok = fixtures
    model = build(name, cfg)
    task = make_task("node", max_nodes=64)
    batch = task.collate(episodes, tok)
    task.compute(model(batch), batch).loss.backward()
    dead = [n for n, p in model.named_parameters()
            if p.requires_grad and (p.grad is None or not p.grad.any())]
    # The sequence half of the relation bias is genuinely unused on a graph
    # batch, and vice versa; nothing else is allowed to be.
    dead = [n for n in dead if "sequence" not in n and "seq_roles" not in n]
    assert not dead, f"{name}: no gradient for {dead}"


@pytest.mark.parametrize("name", model_names())
def test_causal_task_cannot_see_the_future(name, fixtures, cfg):
    """Changing a later token must not change an earlier prediction.

    The single most consequential thing to get wrong: a leak here makes
    next-token numbers look excellent and means nothing was learned.
    """
    episodes, tok = fixtures
    model = build(name, cfg).eval()
    batch = collate_text(episodes[:2], tok)
    with torch.no_grad():
        before = model(batch).symbol_logits.clone()
        cut = batch.tokens.shape[1] // 2
        batch.tokens[:, cut:] = (batch.tokens[:, cut:] + 3) % cfg.vocab_size
        after = model(batch).symbol_logits
    assert torch.allclose(before[:, :cut], after[:, :cut], atol=1e-4), \
        f"{name} leaks information backwards from position {cut}"


@pytest.mark.parametrize("name", model_names())
def test_handles_a_single_short_episode(name, fixtures, cfg):
    """Batch of one, graph of a handful of nodes — the degenerate shapes."""
    episodes, tok = fixtures
    model = build(name, cfg)
    batch = collate_graph(episodes[:1], tok, rng=np.random.default_rng(1))
    assert torch.isfinite(model(batch).symbol_logits).all()


@pytest.mark.parametrize("name", model_names())
def test_padding_does_not_change_a_real_position(name, fixtures, cfg):
    """A short episode batched with a long one must score as it would alone.

    Dynamic padding means the batch length is whatever the longest member
    needed, so any model that lets padded positions contribute would produce
    results that depend on who else was in the batch.
    """
    episodes, tok = fixtures
    model = build(name, cfg).eval()
    short = min(episodes, key=lambda e: len(e.graph))
    long = max(episodes, key=lambda e: len(e.graph))
    if len(short.graph) == len(long.graph):
        pytest.skip("no length difference to test with")

    rng = lambda: np.random.default_rng(5)
    with torch.no_grad():
        alone = model(collate_graph([short], tok, rng=rng(), mask_all=True))
        together = model(collate_graph([short, long], tok, rng=rng(), mask_all=True))
    n = len(short.graph)
    assert torch.allclose(alone.symbol_logits[0, :n],
                          together.symbol_logits[0, :n], atol=1e-4), \
        f"{name}: padding leaks into real positions"


def test_the_symbol_head_is_shared_between_tasks(cfg):
    """The claim the whole comparison rests on: one head, one vocabulary."""
    model = build("transformer", cfg)
    assert model.symbol_head.weight is model.symbol_emb.weight
    assert model.symbol_head.out_features == cfg.vocab_size


def test_registry_rejects_a_duplicate_name():
    from symmodels.models.base import SymbolicModel
    from symmodels.models.registry import register
    with pytest.raises(ValueError):
        @register("transformer")
        class _Clash(SymbolicModel):
            pass


def test_ndr_steps_can_be_raised_after_construction(cfg):
    """The extrapolation probe: more computation without more parameters."""
    model = build("ndr", cfg)
    n_before = model.n_parameters()
    model.set_steps(cfg.n_layers * 3)
    assert model.encoder.n_steps == cfg.n_layers * 3
    assert model.n_parameters() == n_before
