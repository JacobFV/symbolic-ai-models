"""The models added after the accuracy/bits split was noticed.

`ptrgen`, `omegaclaw_em`, the joint decoders and the ensembles all exist because
the same measurement said the same thing: this repo's rule-based half decides
well and estimates badly, and the two are scored by one column each while only
one of them is ever quoted.

`tests/test_models.py` already holds every registered model to the shared
contract — causality, no peeking, a proper distribution, a state round-trip —
and picks these up automatically. What is here is the claims *these* models
make and no other model does.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from symbolic_ai_models.data.curriculum import generate
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import TrainConfig, build_tokenizer

LESSONS = ["unification", "symbol_grounding", "center_embedding"]


@pytest.fixture(scope="module")
def fixtures():
    train = list(generate(LESSONS, n=25))
    evaluation = list(generate(LESSONS, n=8, seed0=1_000_000))
    tok = build_tokenizer(TrainConfig(vocab_size=1600), train)
    return train, evaluation, tok


@pytest.fixture(scope="module")
def cfg(fixtures):
    _, _, tok = fixtures
    return ModelConfig(vocab_size=len(tok), max_len=160, max_nodes=128)


# ---------------------------------------------------------------------------
# ptrgen: the gate, and what the pointer is trained on
# ---------------------------------------------------------------------------
def test_the_gate_is_a_mixture_weight_not_an_accuracy(fixtures, cfg):
    """`ptrgen-001` and `ptrgen-argmax` differ in one method, by construction."""
    from symbolic_ai_models.models.ptrgen_001.model import (PointerGenerator001,
                                                        PointerGeneratorArgmax)
    assert PointerGeneratorArgmax._fit_gate_map is not \
        PointerGenerator001._fit_gate_map
    for name in ("_pointer", "_label_distribution", "_fit_pointer",
                 "_candidates"):
        assert getattr(PointerGeneratorArgmax, name) is \
            getattr(PointerGenerator001, name), f"{name} differs; the row lies"


def test_the_pointer_credits_every_correct_antecedent(cfg):
    """The objective's whole point: several nodes can carry the right label
    and nothing says which one the generator meant.

    A perceptron picks one and pushes the rest down. Marginal likelihood is
    indifferent between them, so two symmetric correct candidates must end up
    with equal probability rather than one of them winning.
    """
    from symbolic_ai_models.models.ptrgen_001.model import PointerGeneratorModel

    model = PointerGeneratorModel(cfg)
    # Two candidates that are correct and described by disjoint features, plus
    # one wrong candidate. Symmetry is only breakable by an arbitrary choice.
    questions = [([[("f", "a")], [("f", "b")], [("f", "wrong")]],
                  np.array([True, True, False]))] * 200
    model._fit_pointer(questions)
    wa, wb = model.weights[("f", "a")], model.weights[("f", "b")]
    assert wa == pytest.approx(wb, abs=1e-6), "the objective broke a real tie"
    assert wa > model.weights[("f", "wrong")]


def test_the_label_distribution_sums_over_nodes_carrying_one_symbol(fixtures, cfg):
    """Three nodes with one label are three routes to one answer, not a split."""
    from symbolic_ai_models.models.ptrgen_001.model import PointerGeneratorModel

    train, _, tok = fixtures
    model = PointerGeneratorModel(cfg)
    model.fit_on(train, tok)
    for view, targets in model.training_views(train[:6], tok, repeats=1,
                                              max_nodes=128):
        for node in targets:
            pointer = model._pointer(view, node)
            labels, _ = model._label_distribution(view, node)
            if not pointer:
                continue
            assert sum(labels.values()) == pytest.approx(
                sum(pointer.values()), rel=1e-9), "mass was lost or invented"
            # And it really is a many-to-one map on this data.
            assert len(labels) <= len(pointer)
            return
    pytest.skip("no pointer fired on this slice")


# ---------------------------------------------------------------------------
# joint decoding
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["omegaclaw_joint-001", "ptrgen_joint-001"])
def test_joint_decoding_leaves_the_view_as_it_found_it(name, fixtures, cfg):
    """It mutates the caller's graph and must put it back, or the pointer head
    — which builds its own view afterwards — would see invented labels."""
    train, _, tok = fixtures
    model = build(name, cfg)
    model.fit_on(train, tok)
    task = make_task("node", max_nodes=128)
    batch = task.collate(train[:4], tok)
    view = model._view(batch, 0)
    before = (list(view.labels), list(view.types), list(view.hidden))
    model.node_votes(view)
    assert (view.labels, view.types, view.hidden) == before


@pytest.mark.parametrize("name", ["omegaclaw_joint-001", "ptrgen_joint-001"])
def test_joint_decoding_answers_every_masked_node(name, fixtures, cfg):
    """A round schedule that drops a node would silently score it as abstained."""
    train, _, tok = fixtures
    model = build(name, cfg)
    model.fit_on(train, tok)
    task = make_task("node", max_nodes=128)
    batch = task.collate(train[:6], tok)
    for b in range(4):
        view = model._view(batch, b)
        if len(view.hidden) < 2:
            continue
        assert set(model.node_votes(view)) == set(view.hidden)


def test_joint_decoding_actually_changes_something(fixtures, cfg):
    """The first version ran the whole schedule and returned the base model's
    answers, because every node was recorded on the first pass before any
    commitment existed. The scores came out bit-identical and the machinery
    looked like it was working."""
    train, evaluation, tok = fixtures
    task = make_task("node", max_nodes=128)
    batch = task.collate(evaluation, tok)
    outputs = {}
    for name in ("omegaclaw_ctx-001", "omegaclaw_joint-001"):
        model = build(name, cfg)
        model.fit_on(train, tok)
        with torch.no_grad():
            outputs[name] = model(batch).symbol_logits
    assert not torch.allclose(outputs["omegaclaw_ctx-001"],
                              outputs["omegaclaw_joint-001"]), \
        "joint decoding is a no-op"


def test_a_committed_node_is_never_evidence_for_itself(fixtures, cfg):
    """The one way this could become circular, ruled out directly.

    A node's reported distribution is taken in the round it is committed, and
    a commitment is written only after that distribution is recorded. So
    re-running the base model on the graph as it stood *before* that node was
    filled must reproduce the node's answer exactly.
    """
    from symbolic_ai_models.models.joint.model import JointDecoding

    train, _, tok = fixtures
    model = build("omegaclaw_joint-001", cfg)
    model.fit_on(train, tok)
    task = make_task("node", max_nodes=128)
    view = model._view(task.collate(train[:4], tok), 0)
    if len(view.hidden) < 2:
        pytest.skip("nothing masked twice over on this episode")

    seen: list[int] = []
    original = JointDecoding._commit

    def record(v, node, pair):
        # At the moment `node` is committed, it must still be masked itself.
        assert v.labels[node] is None, f"node {node} was filled before deciding"
        seen.append(node)
        return original(v, node, pair)

    JointDecoding._commit = staticmethod(record)
    try:
        model.node_votes(view)
    finally:
        JointDecoding._commit = staticmethod(original)
    assert seen, "nothing was committed"
    assert len(seen) == len(set(seen)), "a node was committed twice"


# ---------------------------------------------------------------------------
# the ensemble's algebra
# ---------------------------------------------------------------------------
def test_the_product_is_exact_against_a_dense_reference():
    """The sparse construction claims to reproduce a normalised product over
    8,192 symbols while touching only the union support. On a small vocabulary
    the dense version is computable, so the claim is checked rather than
    argued."""
    from symbolic_ai_models.models.ensemble_001.model import EnsembleModel

    vocab = 40
    model = EnsembleModel.__new__(EnsembleModel)     # no members needed
    torch.manual_seed(0)
    backoff = torch.softmax(torch.randn(vocab), 0)
    model.symbol_backoff = backoff.log()
    base = backoff.numpy()

    rng = np.random.default_rng(0)
    worst = 0.0
    for _ in range(200):
        c_a, c_b = rng.uniform(0, 0.95), rng.uniform(0, 0.95)
        table_a = {int(v): float(rng.uniform(0.1, 1))
                   for v in rng.choice(vocab, 4, replace=False)}
        table_b = {int(v): float(rng.uniform(0.1, 1))
                   for v in rng.choice(vocab, 5, replace=False)}
        w = float(rng.uniform(0, 1))
        votes, c = model._combine((table_a, c_a), (table_b, c_b), w, 0.0, -1)

        p_a = (1 - c_a) * base + c_a * np.array(
            [table_a.get(v, 0) / sum(table_a.values()) for v in range(vocab)])
        p_b = (1 - c_b) * base + c_b * np.array(
            [table_b.get(v, 0) / sum(table_b.values()) for v in range(vocab)])
        reference = p_a ** w * p_b ** (1 - w)
        reference /= reference.sum()

        total = sum(votes.values()) or 1.0
        got = np.array([(1 - c) * base[v] + c * votes.get(v, 0.0) / total
                        for v in range(vocab)])
        worst = max(worst, float(np.abs(got - reference).max()))
    assert worst < 1e-6, f"the sparse product is not the product ({worst:.2e})"


def test_the_ensemble_weight_can_reach_the_endpoints():
    """"One member is carrying this entirely" has to be a reportable answer."""
    from symbolic_ai_models.models.ensemble_001.model import GRID

    assert GRID[0] == 0.0 and GRID[-1] == 1.0


def test_the_two_ensembles_differ_only_in_which_pair(fixtures, cfg):
    from symbolic_ai_models.models.ensemble_001.model import (EnsembleModel,
                                                          MixedEnsemble,
                                                          PointerEnsemble)
    assert MixedEnsemble.members != PointerEnsemble.members
    for name in ("_combine", "_fit_weight", "node_votes", "learn"):
        assert getattr(MixedEnsemble, name) is getattr(EnsembleModel, name)
        assert getattr(PointerEnsemble, name) is getattr(EnsembleModel, name)
