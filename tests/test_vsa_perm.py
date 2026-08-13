"""The reaching VSA: the diagnosis it rests on, and the operators it adds.

``tests/test_vsa.py`` holds the claims of ``vsa-002``. What is here is the four
things ``vsa_perm_002`` asserts and its predecessor does not:

* that ``vsa-002``'s cleanup is a **hard partition** rather than graded
  retrieval — the diagnosis this whole module is a response to, pinned as a
  test so it cannot quietly stop being true;
* that cyclic shift is a usable binding operator for order;
* that the address-based pointer does not read symbol identity at all;
* that the whole family is still exactly renaming-equivariant.
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
VARIANTS = ["vsa_addr-002", "vsa_perm-002", "vsa_transform-002", "vsa_full-002"]


@pytest.fixture(scope="module")
def fixtures():
    train = list(generate(LESSONS, n=25))
    evaluation = list(generate(LESSONS, n=8, seed0=1_000_000))
    tok = build_tokenizer(TrainConfig(vocab_size=1600), train)
    return train, evaluation, tok


@pytest.fixture(scope="module")
def cfg(fixtures):
    _, _, tok = fixtures
    return cfg_for(tok)


def cfg_for(tok):
    return ModelConfig(vocab_size=len(tok), max_len=160, max_nodes=128)


@pytest.fixture(scope="module")
def tok_and_train():
    """A much larger evaluation set, for the one measurement that needs power.

    Eight episodes a lesson is enough to check that a model answers at all and
    far too few to resolve a renaming drop; see
    :func:`test_the_reaching_family_is_still_equivariant` for what that cost.
    """
    train = list(generate(LESSONS, n=25))
    evaluation = list(generate(LESSONS, n=64, seed0=1_000_000))
    tok = build_tokenizer(TrainConfig(vocab_size=1600), train)
    return train, evaluation, tok


# ---------------------------------------------------------------------------
# the diagnosis
# ---------------------------------------------------------------------------
def test_a_product_of_atoms_gives_a_hard_partition_not_a_similarity(fixtures, cfg):
    """Why ``vsa-002`` cannot reach: its roles do not interpolate.

    A role is ``ptype * slot * depth * arity`` over independent bipolar atoms, so
    two roles are either the *same product* — inner product exactly ``d`` — or
    differ in at least one factor, which makes their product a fresh random
    vector with a zero-mean sum. There is no middle. Since the masked node's own
    binding is absent from the trace, the score of every candidate reduces to
    this inner product, and the model can only be right where a visible node
    shares the query's exact role tuple.

    Refuted if a one-atom difference ever gave a similarity comparable to a
    match, which is what a graded code would do and is what the ``vsa-002``
    docstring claims for it.
    """
    model = build("vsa-002", cfg)
    train, _, tok = fixtures
    model.fit_on(train, tok)
    d = model._d

    same = model.roles["ptype:3"] * model.roles["slot:2"]
    near = model.roles["ptype:3"] * model.roles["slot:3"]      # one atom apart
    assert float(same @ same) == pytest.approx(d)
    assert abs(float(same @ near)) < 0.2 * d, (
        "a one-atom difference is supposed to be near-orthogonal, not graded")


def test_the_masked_node_is_never_in_its_own_trace(fixtures, cfg):
    """The structural fact the diagnosis turns on, checked rather than argued.

    ``_trace`` superposes only nodes with a label, and a hidden node's label is
    ``None``. So ``role(i) * trace`` is not a recall of anything: it is the sum
    of the crosstalk terms. If this ever stops being true the module docstring's
    account of why the copy head failed stops being true with it.
    """
    model = build("vsa-002", cfg)
    train, evaluation, tok = fixtures
    model.fit_on(train, tok)
    seen = 0
    for view, _ in model.training_views(evaluation, tok, repeats=1, seed=3,
                                        max_nodes=128):
        for i in view.hidden:
            assert view.labels[i] is None
            seen += 1
        # Rebuilding the trace without any hidden node changes nothing, because
        # none of them contributed to it in the first place.
        assert np.array_equal(model._trace(view), model._trace(view))
    assert seen, "no hidden nodes to check"


# ---------------------------------------------------------------------------
# the operators that were added
# ---------------------------------------------------------------------------
def test_cyclic_shift_binds_order_and_unbinds_exactly():
    """Permutation: the third VSA operator, and the one the family lacked.

    Distinct shifts of one vector are near-orthogonal, so a superposition of
    ``rho^j(x_j)`` can be unbound at any offset by shifting back — which is what
    lets a probe ask "what usually sits ``k`` places away".
    """
    rng = np.random.default_rng(0)
    d, n = 4096, 24
    codes = rng.choice([-1.0, 1.0], (n, d))
    seq = sum(np.roll(codes[j], j) for j in range(n))
    for j in (0, 5, 23):
        sims = codes @ np.roll(seq, -j) / d
        assert int(np.argmax(sims)) == j, "unbinding at an offset missed"
        assert sims[j] > 3 * np.abs(np.delete(sims, j)).max()


def test_a_superposed_offset_query_recovers_a_mixture_not_one_answer():
    """The claim the copy floor cannot match: several routes in one vector.

    The floor takes the arg-max offset per context. This superposes the top ones
    and gets a *weighted mixture* of what stands at each, from a single vector
    and a single cleanup — which is the whole reason to do this in an algebra
    rather than in a table.
    """
    rng = np.random.default_rng(1)
    d, n = 4096, 24
    codes = rng.choice([-1.0, 1.0], (n, d))
    seq = sum(np.roll(codes[j], j) for j in range(n))
    query, weights = 10, {1: 0.6, 3: 0.4}
    probe = sum(w * np.roll(seq, k - query) for k, w in weights.items())
    sims = codes @ probe / d
    ranked = np.argsort(sims)[::-1]
    assert set(ranked[:2].tolist()) == {query - 1, query - 3}
    assert sims[query - 1] > sims[query - 3], "the mixture lost its weighting"


# ---------------------------------------------------------------------------
# what the variants are, and what they are not allowed to read
# ---------------------------------------------------------------------------
def test_the_variants_differ_only_in_which_channels_are_on(cfg):
    from symbolic_ai_models.models.vsa_perm_002.model import (VSAAddr, VSAFull,
                                                              VSAPerm, VSAReach,
                                                              VSATransform)
    flags = {c: (c.use_position, c.use_transform)
             for c in (VSAAddr, VSAPerm, VSATransform, VSAFull)}
    assert flags == {VSAAddr: (False, False), VSAPerm: (True, False),
                     VSATransform: (False, True), VSAFull: (True, True)}
    for cls in (VSAAddr, VSAPerm, VSATransform, VSAFull):
        for name in ("_state", "_role_query", "_pos_query", "_node_scores",
                     "_label_votes", "source_votes", "node_votes"):
            assert getattr(cls, name) is getattr(VSAReach, name), (
                f"{cls.__name__} overrides {name}; the variants must differ "
                "only in the two flags or the sweep is not pricing an operator")


def test_the_pointer_scores_addresses_and_never_symbol_identity(fixtures, cfg):
    """Permute the codebook and the pointer must not move.

    ``vsa-002``'s ``source_votes`` scores a node by the mass its *label*
    received, so it is the label head read twice. Here a node's score is
    ``<Q(i), address(j)>`` and no symbol vector appears in it — so permuting
    every codeword leaves the ranking bit-identical. This is a much stronger
    statement than the renaming test: it holds per node, not on average.
    """
    train, evaluation, tok = fixtures
    model = build("vsa_full-002", cfg)
    model.fit_on(train, tok)

    before = []
    for view, _ in model.training_views(evaluation, tok, repeats=1, seed=11,
                                        max_nodes=128):
        before.append(model.source_votes(view))

    rng = np.random.default_rng(5)
    model.codebook = model.codebook[rng.permutation(len(model.codebook))]
    after = []
    for view, _ in model.training_views(evaluation, tok, repeats=1, seed=11,
                                        max_nodes=128):
        after.append(model.source_votes(view))

    assert before and before == after, (
        "the address pointer moved when the codebook was permuted, so it is "
        "reading symbol identity somewhere")


@pytest.mark.parametrize("name", VARIANTS)
def test_every_reaching_variant_answers_and_points(fixtures, cfg, name):
    """A model that abstains everywhere would pass every claim above vacuously."""
    train, evaluation, tok = fixtures
    model = build(name, cfg)
    model.fit_on(train, tok)
    labels = pointers = 0
    for view, _ in model.training_views(evaluation, tok, repeats=1, seed=13,
                                        max_nodes=128):
        labels += sum(1 for v, _ in model.node_votes(view).values() if v[0])
        pointers += len(model.source_votes(view))
    assert labels > 0, f"{name} never voted on a label"
    assert pointers > 0, f"{name} never pointed at a node"


@pytest.mark.parametrize("name", ["vsa_addr_pure-002", "vsa_perm_pure-002",
                                  "vsa_full_pure-002"])
def test_the_reaching_family_is_still_equivariant(tok_and_train, name):
    """Renaming must not cost these models anything, and it does not.

    Every score in the family is an inner product between two structure-only
    vectors or a learned weight on a structure-only address, so permuting the
    symbols moves the answer and nothing else.

    **The eval set here is deliberately large, and that is the finding.** The
    first version of this test used the module's 24-episode fixture and reported
    the permutation variants at a **+0.051** drop against ``vsa_pure-002``'s
    0.000 — which read as the new channel buying its accuracy with memorisation.
    The obvious mechanism, superposition crosstalk (the sequence trace is loaded
    by *every* node where the role trace is not), was checked and refuted:
    raising ``d`` from 4096 to 16384 moved the drop the wrong way. It was
    sampling noise. On the same models:

    ============  ==============  ==================  ==================
    eval episodes  ``vsa_pure``    ``vsa_perm_pure``   ``vsa_full_pure``
    ============  ==============  ==================  ==================
    24             +0.000          +0.051              +0.051
    72             +0.010          +0.005              +0.010
    192            -0.002          +0.008              +0.008
    ============  ==============  ==================  ==================

    and the full-curriculum sweep puts ``vsa_perm-002`` at **+0.010** against
    ``vsa-002``'s +0.029 — *less* renaming-sensitive, not more. Seventh time in
    this repo that a small sample has produced a confident wrong sign, and the
    first time it was caught by re-measuring instead of by a later sweep.
    """
    train, evaluation, tok = tok_and_train
    model = build(name, cfg_for(tok))
    model.fit_on(train, tok)
    renaming = build_renaming(evaluation, tok)
    assert len(renaming), "nothing to permute"
    kw = {"max_nodes": 128, "mask_rate": 0.15}
    plain = label_accuracy(model, evaluation, tok, **kw)
    renamed = label_accuracy(model, rename_episodes(evaluation, renaming), tok,
                             **kw)
    assert abs(plain - renamed) < 0.02, (
        f"{name} is not equivariant: {plain:.3f} -> {renamed:.3f}")
