"""The asymptotic observables, against processes whose answer is known.

These measure the corpus rather than a model, so there is no floor to compare
against and the estimator has to be checked directly. Each test below is a
process with a derivable ``I(d)``, which is the only way to know the curve is
reporting the corpus and not the estimator.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from symbolic_ai_core.asymptotics import (effective_rank, mi_curve,
                                            mutual_information)


def test_independent_symbols_have_no_mutual_information():
    rng = np.random.default_rng(0)
    pairs = [(int(a), int(b)) for a, b in
             zip(rng.integers(0, 4, 20_000), rng.integers(0, 4, 20_000))]
    assert mutual_information(pairs) == pytest.approx(0.0, abs=0.01)


def test_a_deterministic_pair_carries_the_full_entropy():
    """y = x over a uniform 4-symbol alphabet is exactly 2 bits."""
    rng = np.random.default_rng(0)
    xs = rng.integers(0, 4, 20_000)
    assert mutual_information([(int(x), int(x)) for x in xs]) == \
        pytest.approx(2.0, abs=0.01)


def test_the_plug_in_estimator_is_biased_upward_on_noise():
    """The reason every curve here carries a shuffled control.

    Independent symbols over a large alphabet at a small sample size read as
    *positive* mutual information. This is the bias that a raw curve reported
    without a control would have been mistaken for structure -- as it nearly
    was.
    """
    rng = np.random.default_rng(0)
    pairs = [(int(a), int(b)) for a, b in
             zip(rng.integers(0, 400, 4_000), rng.integers(0, 400, 4_000))]
    assert mutual_information(pairs) > 0.5, "expected substantial upward bias"


def test_a_markov_chain_decays_exponentially_and_the_control_does_not_move():
    """Known-exponential process: the excess must fall off, the null must not."""
    rng = np.random.default_rng(1)
    # Two states, sticky: correlation decays as (2p-1)^d.
    seqs = []
    for _ in range(200):
        s, out = 0, []
        for _ in range(300):
            if rng.uniform() < 0.1:
                s = 1 - s
            out.append(s)
        seqs.append(out)
    curve = mi_curve(seqs, distances=(1, 4, 32))
    assert curve.order(1) > curve.order(4) > curve.order(32)
    # There is no per-sequence subject here, so the two nulls must agree.
    for d in (1, 4, 32):
        assert abs(curve.latent(d)) < 0.02


def test_a_constant_latent_produces_a_floor_that_does_not_decay():
    """The signature claimed for the curriculum, on a process built to have it.

    Each sequence draws a hidden class and emits from that class's private
    alphabet. Knowing any symbol identifies the class, so I(d) is constant in d
    and does not decay -- and the shuffle cannot reproduce it, because shuffling
    within a sequence leaves the class intact.
    """
    rng = np.random.default_rng(2)
    seqs = []
    for _ in range(300):
        cls = int(rng.integers(0, 4))
        seqs.append([cls * 10 + int(rng.integers(0, 10)) for _ in range(200)])
    curve = mi_curve(seqs, distances=(1, 16, 128))
    # The within-shuffle cannot see it; the global one must.
    assert abs(curve.order(128)) < 0.1, "a latent is not order structure"
    assert curve.latent(128) > 1.5, "the floor vanished"
    assert abs(curve.latent(1) - curve.latent(128)) < 0.3, "it decayed"


def test_shuffling_within_a_sequence_keeps_the_sequences_separate():
    """Pairs must never straddle a boundary, or the curve measures composition."""
    seqs = [[1] * 50, [2] * 50]
    curve = mi_curve(seqs, distances=(1,), min_pairs=10)
    # Every within-sequence pair is (1,1) or (2,2); a straddling pair would
    # introduce (1,2) and change the count.
    assert curve.n_pairs[1] == 98


def test_effective_rank_is_one_for_a_single_repeated_context():
    seqs = [[0, 1] * 100]
    rank, contexts, _ = effective_rank(seqs, vocab=4)
    assert contexts == 2
    assert rank == pytest.approx(2.0, abs=0.5)


def test_effective_rank_grows_with_genuinely_distinct_contexts():
    rng = np.random.default_rng(3)
    # 40 contexts each with its own sharply peaked successor distribution.
    seqs = []
    for _ in range(400):
        out = []
        for _ in range(60):
            a = int(rng.integers(0, 40))
            out.extend([a, (a * 7 + 1) % 40])
        seqs.append(out)
    rank, contexts, _ = effective_rank(seqs, vocab=40)
    assert contexts == 40
    assert rank > 5.0
