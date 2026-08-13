"""The vector-symbolic models, against the algebra they claim to run.

`tests/test_models.py` holds every registered model to the shared contract. What
is here is the four claims this family makes and no other model does: that
unbinding recovers a bound filler, that superposition degrades gracefully rather
than failing, that a random codebook is *exactly* renaming-equivariant, and that
seeding trades that equivariance for similarity.

The equivariance claim has a proof worth stating, because it is why the number
should be zero rather than small. Predicting node ``i`` from a coreferent node
``j``, the probe is ``role(i) * (role(j) * cb[s])`` and the score of candidate
``s`` is ``cb[s] . role(i) * role(j) * cb[s] = sum(role(i) * role(j))``, since
``cb[s]**2 == 1`` elementwise for bipolar codes. The winning score does not
depend on *which* symbol ``s`` is. Renaming permutes which candidate holds it
and changes nothing else.
"""

from __future__ import annotations

import numpy as np
import pytest

from symbolic_ai_core.data.curriculum import generate
from symbolic_ai_core.invariance import (build_renaming, label_accuracy,
                                           rename_episodes)
from symbolic_ai_models.models import ModelConfig, build
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
# the algebra
# ---------------------------------------------------------------------------
def test_binding_is_its_own_inverse():
    """MAP: multiply to bind, multiply again to unbind. Nothing else works."""
    rng = np.random.default_rng(0)
    a, b = (rng.choice([-1.0, 1.0], 4096) for _ in range(2))
    assert np.allclose(a * (a * b), b)


def test_unbinding_recovers_a_filler_from_a_superposition():
    """The one operation the whole model rests on, at realistic width."""
    rng = np.random.default_rng(1)
    d, k = 4096, 20
    roles = rng.choice([-1.0, 1.0], (k, d))
    fillers = rng.choice([-1.0, 1.0], (k, d))
    trace = (roles * fillers).sum(axis=0)
    for i in (0, 7, 19):
        probe = roles[i] * trace
        sims = fillers @ probe / d
        assert int(np.argmax(sims)) == i, "cleanup picked the wrong filler"
        # And the right one stands clear of the field, not just above it.
        assert sims[i] > 3 * np.abs(np.delete(sims, i)).max()


def test_capacity_degrades_gracefully_rather_than_failing():
    """Superposition is how exponentially many things fit in fixed width.

    The claim is not unlimited capacity, it is a *smooth* signal-to-noise
    tradeoff of about sqrt(d/k) -- so recall falls off progressively instead of
    hitting a cell boundary and breaking. Refuted if recall collapses to chance
    between two adjacent load levels.
    """
    rng = np.random.default_rng(2)
    d = 2048
    recalls = []
    for k in (10, 40, 160, 640):
        roles = rng.choice([-1.0, 1.0], (k, d))
        fillers = rng.choice([-1.0, 1.0], (k, d))
        trace = (roles * fillers).sum(axis=0)
        hits = sum(int(np.argmax(fillers @ (roles[i] * trace))) == i
                   for i in range(k))
        recalls.append(hits / k)
    assert recalls[0] == 1.0
    assert recalls == sorted(recalls, reverse=True), "recall is not monotone"
    # Graceful: still well above chance at 640 items in 2048 dimensions.
    assert recalls[-1] > 5.0 / 640


# ---------------------------------------------------------------------------
# what the codebook buys and costs
# ---------------------------------------------------------------------------
def test_the_two_variants_differ_only_in_the_codebook(cfg):
    from symbolic_ai_models.models.vsa_002.model import (VSAModel, VSARandom,
                                                         VSASeeded)
    assert VSASeeded._build_codebook is not VSARandom._build_codebook
    for name in ("_role", "_trace", "_probe", "_cleanup", "node_votes",
                 "source_votes", "_build_roles"):
        assert getattr(VSASeeded, name) is getattr(VSAModel, name)
        assert getattr(VSARandom, name) is getattr(VSAModel, name)


def test_a_random_codebook_is_exactly_renaming_equivariant(fixtures, cfg):
    """Not approximately. See the module docstring for why it is identically so.

    Measured on `vsa_pure-002`, which is the same model with the shared
    structural fallback off, and that qualifier is the finding. With the
    fallback *on* the drop is +0.136 -- because the fallback memorises which
    symbol fills which structural slot and every rule-based model inherits it.
    The algebra is equivariant; the floor underneath it is not, and the repo's
    renaming column has been charging models for a component they share.
    """
    train, evaluation, tok = fixtures
    model = build("vsa_pure-002", cfg)
    model.fit_on(train, tok)
    renaming = build_renaming(evaluation, tok)
    assert len(renaming), "nothing to permute"
    kw = {"max_nodes": 128, "mask_rate": 0.15}
    plain = label_accuracy(model, evaluation, tok, **kw)
    renamed = label_accuracy(model, rename_episodes(evaluation, renaming), tok,
                             **kw)
    assert abs(plain - renamed) < 0.01, (
        f"random VSA is not equivariant: {plain:.3f} -> {renamed:.3f}")


def test_seeding_makes_similar_symbols_similar(fixtures, cfg):
    """The point of the seed, checked on the codebook rather than on a score.

    A random codebook is near-orthogonal everywhere by construction. A seeded
    one must not be, or it is a random codebook with extra steps.
    """
    train, _, tok = fixtures
    random_model = build("vsa-002", cfg)
    random_model.fit_on(train, tok)
    seeded = build("vsa_seeded-002", cfg)
    seeded.fit_on(train, tok)

    def spread(codebook):
        rng = np.random.default_rng(0)
        rows = rng.choice(len(codebook), 300, replace=False)
        block = codebook[rows]
        sims = (block @ block.T) / block.shape[1]
        off = sims[~np.eye(len(rows), dtype=bool)]
        return float(np.abs(off).mean())

    ratio = spread(seeded.codebook) / spread(random_model.codebook)
    assert ratio > 1.5, "the seeded codebook is no less orthogonal than a random one"
    # Recorded rather than merely asserted: the measured ratio is about 2.0, so
    # this seed is *weak*. Sign-quantising a random projection of sparse
    # co-occurrence keeps little of the similarity structure, and a real
    # pretrained table would be far stronger. If that ratio ever climbs, the
    # seed got better and the scores below should move with it.
    assert ratio < 20.0, f"unexpectedly strong seed ({ratio:.1f}x); re-read the results"


# ---------------------------------------------------------------------------
# what the model costs to store, and to state
# ---------------------------------------------------------------------------
def test_a_random_codebook_survives_a_round_trip_bit_identically(fixtures, cfg):
    """It is dropped from the checkpoint and rebuilt from the seed, so it has to
    come back *identical* -- anything else silently moves every published row."""
    train, _, tok = fixtures
    model = build("vsa-002", cfg)
    model.fit_on(train, tok)
    before = model.codebook.copy()

    state = model.symbolic_state()
    assert state["codebook"] is None, "the random codebook was stored anyway"

    restored = build("vsa-002", cfg)
    restored.load_symbolic_state(state, tok)
    assert restored.codebook is not None
    assert np.array_equal(restored.codebook, before), "the codebook moved"


def test_a_seeded_codebook_is_stored_because_it_is_data(fixtures, cfg):
    train, _, tok = fixtures
    model = build("vsa_seeded-002", cfg)
    model.fit_on(train, tok)
    state = model.symbolic_state()
    assert state["codebook"] is not None, "a data-derived codebook was dropped"
    restored = build("vsa_seeded-002", cfg)
    restored.load_symbolic_state(state, tok)
    assert np.array_equal(restored.codebook, model.codebook)


def test_the_two_variants_are_not_counted_the_same_way(fixtures, cfg):
    """A random codebook is a seed; a seeded one is 33.5M measured signs.

    Reporting 8,254 for both let a data-fitted model advertise itself as tiny
    beside one that genuinely is.
    """
    train, _, tok = fixtures
    random_model = build("vsa-002", cfg)
    random_model.fit_on(train, tok)
    seeded = build("vsa_seeded-002", cfg)
    seeded.fit_on(train, tok)

    assert random_model.n_symbolic_parameters() == \
        len(random_model.codebook) + len(random_model.roles)
    assert seeded.n_symbolic_parameters() > 100 * random_model.n_symbolic_parameters()
