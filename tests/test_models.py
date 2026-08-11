"""Every architecture, against the contract the harness assumes of all of them.

These are parameterised over the registry, so a new model — neural or symbolic —
is covered the moment it is registered and cannot be added without answering
both questions, emitting a real distribution, and passing the two leak tests.

The leak tests are the "no cheating" rules, and they are checked empirically
rather than promised in a docstring:

* :func:`test_causal_task_cannot_see_the_future` — perturbing later tokens must
  leave earlier predictions bit-identical.
* :func:`test_the_hidden_answer_never_reaches_the_model` — changing the label a
  model is being asked to predict must not change what it predicts.

A model that fails either is reading its own answer, and its numbers would be
worthless whether it was fitted or trained.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest
import torch

from symbolic_ai_models.data.batch import collate_graph, collate_text
from symbolic_ai_models.data.curriculum import generate
from symbolic_ai_models.data.tokenizer import SymbolTokenizer
from symbolic_ai_models.models import ModelConfig, RuleBasedModel, build, model_names
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import TrainConfig, build_tokenizer

LESSONS = ["unification", "symbol_grounding", "center_embedding"]
NEURAL = [n for n in model_names() if not issubclass(
    __import__("symbolic_ai_models.models", fromlist=["REGISTRY"]).REGISTRY[n], RuleBasedModel)]
RULE_BASED = [n for n in model_names() if n not in NEURAL]

#: The neural half is opt-in (`SYMBOLIC_AI_MODELS_NEURAL=1`), so its tests skip
#: rather than fail when it is not registered. They still run, and still have to
#: pass, on a machine where the comparison is the point.
needs_neural = pytest.mark.skipif(not NEURAL, reason="neural models not registered")


@pytest.fixture(scope="module")
def fixtures():
    episodes = list(generate(LESSONS, n=4))
    tok = build_tokenizer(TrainConfig(vocab_size=600), episodes)
    return episodes, tok


@pytest.fixture(scope="module")
def cfg(fixtures):
    _, tok = fixtures
    return ModelConfig(vocab_size=len(tok), d_model=32, n_layers=2, n_heads=4,
                       d_ff=64, dropout=0.0)


def make(name: str, fixtures, cfg):
    """Build a model and bring it to its usable state, whichever family it is."""
    episodes, tok = fixtures
    model = build(name, cfg)
    if isinstance(model, RuleBasedModel):
        model.fit_on(episodes, tok)
    return model.eval()


# ---------------------------------------------------------------------------
# the shared contract
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", model_names())
def test_answers_both_questions(name, fixtures, cfg):
    """One model, both tasks, both heads, shapes that line up with the targets."""
    episodes, tok = fixtures
    model = make(name, fixtures, cfg)
    for batch in (collate_text(episodes, tok),
                  collate_graph(episodes, tok, rng=np.random.default_rng(0))):
        out = model(batch)
        assert out.symbol_logits.shape == (*batch.tokens.shape, cfg.vocab_size)
        assert out.type_logits.shape[:2] == batch.tokens.shape
        assert torch.isfinite(out.symbol_logits).all()


@pytest.mark.parametrize("name", RULE_BASED)
def test_rule_based_output_is_a_proper_distribution(name, fixtures, cfg):
    """No rule-based model may assign zero probability to the answer.

    A symbolic model that voted for three symbols and left the rest at zero
    would score infinite loss the first time it was wrong, which would say
    nothing about the method. The mixture with the back-off is what makes the
    comparison meaningful, and this is the test that it is really happening.

    Networks are exempt because they emit unnormalised logits and the loss
    softmaxes them; a rule-based model emits the log of an already-proper
    distribution, so for it normalisation is a claim that can be checked.
    """
    episodes, tok = fixtures
    model = make(name, fixtures, cfg)
    batch = collate_graph(episodes, tok, rng=np.random.default_rng(0))
    logits = model(batch).symbol_logits
    assert torch.isfinite(logits).all()
    assert (logits < 0).all(), "log-probabilities must be negative"
    mass = logits.exp().sum(-1)
    assert torch.allclose(mass, torch.ones_like(mass), atol=1e-3), \
        f"{name}: probabilities sum to {mass.min():.4f}..{mass.max():.4f}"


@pytest.mark.parametrize("name", model_names())
def test_the_loss_is_finite_for_every_model(name, fixtures, cfg):
    """Whatever the family, both objectives must produce a usable number."""
    episodes, tok = fixtures
    model = make(name, fixtures, cfg)
    for task_name, kw in (("lm", {"max_len": 256}), ("node", {"max_nodes": 64})):
        task = make_task(task_name, **kw)
        batch = task.collate(episodes, tok)
        loss = task.compute(model(batch), batch).loss
        assert torch.isfinite(loss), f"{name}/{task_name} loss is {loss}"


@pytest.mark.parametrize("name", model_names())
def test_causal_task_cannot_see_the_future(name, fixtures, cfg):
    """Changing a later token must not change an earlier prediction.

    The single most consequential thing to get wrong: a leak here makes
    next-token numbers look excellent and means nothing was learned. It applies
    with equal force to the rule-based models, whose text side is handed the
    whole sequence for speed and is therefore only causal by discipline — this
    is what checks the discipline held.
    """
    episodes, tok = fixtures
    model = make(name, fixtures, cfg)
    batch = collate_text(episodes[:2], tok)
    with torch.no_grad():
        before = model(batch).symbol_logits.clone()
        cut = batch.tokens.shape[1] // 2
        batch.tokens[:, cut:] = (batch.tokens[:, cut:] + 3) % cfg.vocab_size
        after = model(batch).symbol_logits
    assert torch.allclose(before[:, :cut], after[:, :cut], atol=1e-4), \
        f"{name} leaks information backwards from position {cut}"


@pytest.mark.parametrize("name", model_names())
def test_the_hidden_answer_never_reaches_the_model(name, fixtures, cfg):
    """Rewriting a masked node's true label must not move the prediction.

    With every node masked, no label is visible and no coreference edge
    survives, so the input is identical whatever the labels were. A model whose
    output moves is reading the answer out of the batch through some channel
    that was not supposed to carry it.
    """
    episodes, tok = fixtures
    model = make(name, fixtures, cfg)
    original = episodes[0]
    rewritten = copy.deepcopy(original)
    rewritten.graph.labels = [f"zz{i}" for i in range(len(rewritten.graph))]

    with torch.no_grad():
        a = model(collate_graph([original], tok, mask_all=True)).symbol_logits
        b = model(collate_graph([rewritten], tok, mask_all=True)).symbol_logits
    assert torch.allclose(a, b, atol=1e-4), f"{name}: the hidden answer leaked"


@pytest.mark.parametrize("name", model_names())
def test_handles_a_single_short_episode(name, fixtures, cfg):
    """Batch of one, graph of a handful of nodes — the degenerate shapes."""
    episodes, tok = fixtures
    model = make(name, fixtures, cfg)
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
    model = make(name, fixtures, cfg)
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


# ---------------------------------------------------------------------------
# neural only
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", NEURAL)
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


@needs_neural
def test_the_symbol_head_is_shared_between_tasks(cfg):
    """The claim the whole comparison rests on: one head, one vocabulary."""
    model = build("transformer", cfg)
    assert model.symbol_head.weight is model.symbol_emb.weight
    assert model.symbol_head.out_features == cfg.vocab_size


@needs_neural
def test_ndr_steps_can_be_raised_after_construction(cfg):
    """The extrapolation probe: more computation without more parameters."""
    model = build("ndr", cfg)
    n_before = model.n_parameters()
    model.set_steps(cfg.n_layers * 3)
    assert model.encoder.n_steps == cfg.n_layers * 3
    assert model.n_parameters() == n_before


# ---------------------------------------------------------------------------
# rule-based only
# ---------------------------------------------------------------------------
def test_the_rule_based_family_is_populated():
    """The subject of the repo. The neural half is opt-in; see `needs_neural`."""
    assert len(RULE_BASED) >= 10


@needs_neural
def test_both_families_are_populated_when_neural_is_on():
    assert len(NEURAL) >= 5 and len(RULE_BASED) >= 10


@pytest.mark.parametrize("name", RULE_BASED)
def test_refuses_to_predict_before_being_fitted(name, fixtures, cfg):
    """Predicting from an unfitted model would silently score the back-off."""
    episodes, tok = fixtures
    model = build(name, cfg)
    with pytest.raises(RuntimeError, match="fit"):
        model(collate_text(episodes[:1], tok))


@pytest.mark.parametrize("name", RULE_BASED)
def test_runs_on_cpu_without_touching_autograd(name, fixtures, cfg):
    """These are Python, not tensors: nothing here should build a graph."""
    episodes, tok = fixtures
    model = make(name, fixtures, cfg)
    out = model(collate_graph(episodes[:2], tok, rng=np.random.default_rng(0)))
    assert not out.symbol_logits.requires_grad
    assert out.symbol_logits.device.type == "cpu"


@pytest.mark.parametrize("name", RULE_BASED)
def test_fitting_is_deterministic(name, fixtures, cfg):
    """Two fits on the same episodes must give the same model."""
    episodes, tok = fixtures
    batch = collate_graph(episodes[:2], tok, rng=np.random.default_rng(3))
    outs = []
    for _ in range(2):
        model = build(name, cfg)
        model.fit_on(episodes, tok)
        outs.append(model.eval()(batch).symbol_logits)
    assert torch.allclose(outs[0], outs[1], atol=1e-6)


def test_abstention_lands_exactly_on_the_backoff(fixtures, cfg):
    """The contract for "I don't know": no vote, no penalty beyond the prior."""
    from symbolic_ai_models.models.symbolic import ABSTAIN, RuleBasedModel as RBM
    from symbolic_ai_models.models.base import ModelOutput

    class _Silent(RBM):
        name = "silent"

    episodes, tok = fixtures
    model = _Silent(cfg)
    model.fit_on(episodes, tok)
    out = model(collate_text(episodes[:2], tok))
    expected = model.symbol_backoff
    assert torch.allclose(out.symbol_logits[0, 0], expected, atol=1e-5)


def test_a_decision_list_can_be_read(fixtures, cfg):
    """The artifact of a symbolic run is text you can argue with."""
    model = make("ruleinduce", fixtures, cfg)
    rendered = model.render()
    assert "label" in rendered and "type" in rendered
    assert isinstance(model.n_symbolic_parameters(), int)


@pytest.mark.parametrize("name", RULE_BASED)
def test_fitting_is_stable_across_processes(name, fixtures, cfg, tmp_path):
    """Two fits in *separate interpreters* must agree, not just two in one.

    `test_fitting_is_deterministic` runs both fits in one process and would miss
    the classic failure: iterating a `set` or `frozenset` of strings gives an
    order that depends on hash randomisation, which is fixed within a process
    and differs between them. Every model here builds sets somewhere, so a
    tie-break that silently depended on iteration order would flap every number
    between runs while looking perfectly reproducible in the test suite.
    """
    import subprocess
    import sys

    script = tmp_path / "fit.py"
    script.write_text(
        "import hashlib, torch\n"
        "from symbolic_ai_models.data.curriculum import generate\n"
        "from symbolic_ai_models.data.batch import collate_graph\n"
        "from symbolic_ai_models.train import TrainConfig, build_tokenizer\n"
        "from symbolic_ai_models.models import build, ModelConfig\n"
        "eps = list(generate(['unification', 'symbol_grounding'], n=4))\n"
        "tok = build_tokenizer(TrainConfig(vocab_size=600), eps)\n"
        f"m = build({name!r}, ModelConfig(vocab_size=len(tok), d_model=32,\n"
        "          n_layers=2, n_heads=4, d_ff=64, dropout=0.0))\n"
        "m.fit_on(eps, tok); m.eval()\n"
        "b = collate_graph(eps, tok, mask_all=True)\n"
        "with torch.no_grad():\n"
        "    x = m(b).symbol_logits\n"
        "print(hashlib.sha1(x.numpy().tobytes()).hexdigest())\n")

    def run(seed: str) -> str:
        # No GPU: this test is about hash order, and letting several
        # subprocesses initialise CUDA at once made the suite flaky under load.
        env = {"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": seed,
               "HOME": str(tmp_path), "CUDA_VISIBLE_DEVICES": ""}
        out = subprocess.run([sys.executable, str(script)], capture_output=True,
                             text=True, env=env, timeout=600)
        assert out.returncode == 0, out.stderr[-2000:]
        return out.stdout.strip().splitlines()[-1]

    assert run("1") == run("999"), f"{name}: output depends on hash seed"


@pytest.mark.parametrize("name", RULE_BASED)
def test_rule_based_survives_a_non_cpu_buffer(name, fixtures, cfg):
    """A rule-based model must work wherever its buffers were loaded to.

    These models compute in Python on the CPU, but `load_run` puts their
    buffers on whatever device was asked for, so on a machine with a GPU the
    back-off sat on cuda while the confidences were built on cpu. Every
    `eval --curriculum` on a rule-based run died on that mismatch. Simulated
    here with a dtype change rather than a device — the failure was a mixed
    `to()` on the back-off buffer, and this reproduces that shape on any host.
    """
    episodes, tok = fixtures
    model = make(name, fixtures, cfg)
    model.symbol_backoff = model.symbol_backoff.to(torch.float64)
    model.type_backoff = model.type_backoff.to(torch.float64)
    out = model(collate_text(episodes[:2], tok))
    assert torch.isfinite(out.symbol_logits).all()


def test_a_model_with_a_pointer_is_scored_on_copying(fixtures, cfg):
    """`evidence` states a binding; models without a pointer stay unscored.

    The pointer must be additive: exposing the retrieval as a node must not
    disturb the symbol head it was already feeding.
    """
    import numpy as np

    from symbolic_ai_models.data.batch import collate_graph
    from symbolic_ai_models.tasks import make_task

    episodes, tok = fixtures
    task = make_task("node", max_nodes=64)
    batch = collate_graph(episodes, tok, max_nodes=64, mask_rate=0.15,
                          rng=np.random.default_rng(5))
    B, L = batch.tokens.shape

    pointed = make("evidence", fixtures, cfg)
    out = pointed(batch)
    assert out.source_logits is not None, "evidence should state bindings"
    assert out.source_logits.shape == (B, L, L)
    assert task.compute(out, batch).counts.get("copy_n", 0) > 0

    # A model with no pointer is left unscored rather than scored as zero.
    plain = make("syllogism", fixtures, cfg)
    assert plain(batch).source_logits is None
    assert "copy_n" not in task.compute(plain(batch), batch).counts


# ---- versioned identity ---------------------------------------------------
def test_a_bare_name_resolves_to_a_version_and_a_pinned_name_does_not_move():
    """Model names pin what produced a number; bare names stay convenient.

    This repo's output is a table of numbers attached to model names, and those
    numbers only mean something if the name pins the model. It has already been
    bitten twice: `corefer`'s type head went 0.174 -> 0.612 in one commit and
    `workspace` moved from eighth to joint first when a cap was raised. Both
    improvements, both silently redefining what an earlier row meant.
    """
    from symbolic_ai_models.models import model_names
    from symbolic_ai_models.models.registry import base_name, get

    names = model_names()
    assert names, "no models registered"
    for n in names:
        assert base_name(n) != n, f"{n} carries no version"

    # A bare name resolves to the highest version registered under it.
    assert get("corefer").name == "corefer-001"
    assert get("ilp").name == "ilp-001"
    # A pinned name resolves to exactly itself.
    assert get("corefer-001").name == "corefer-001"

    with pytest.raises(KeyError):
        get("no-such-model")


def test_selecting_models_by_bare_name_yields_versioned_run_names():
    """`--models corefer` must write `runs/.../corefer-001`, not `corefer`."""
    from symbolic_ai_models.cli import _select_models

    assert _select_models("corefer,ilp") == ["corefer-001", "ilp-001"]
    assert _select_models("corefer-001") == ["corefer-001"]
    assert all(base_name_has_version(n) for n in _select_models("symbolic"))


def base_name_has_version(name: str) -> bool:
    from symbolic_ai_models.models.registry import base_name
    return base_name(name) != name
