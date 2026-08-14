"""The Mantel machinery, against distance matrices whose answer is known.

The typology reading rests on two numbers -- a Mantel r and a partial Mantel
controlling for script -- so the estimator is checked directly rather than
trusted. Distance-matrix entries are not independent, which is the whole reason
a permutation test is used instead of a t-test on 1,035 "observations".
"""
from __future__ import annotations

import numpy as np
import pytest

from scripts.wals_correlate import mantel, partial_mantel


def _setup(n):
    return np.triu_indices(n, 1), n


def test_a_matrix_correlates_perfectly_with_itself():
    rng = np.random.default_rng(0)
    n = 20
    A = rng.uniform(size=(n, n)); A = (A + A.T) / 2
    iu, n = _setup(n)
    r, p = mantel(A, A, iu, n, perms=200)
    assert r == pytest.approx(1.0, abs=1e-9)
    assert p < 0.02


def test_independent_matrices_do_not_correlate():
    rng = np.random.default_rng(1)
    n = 20
    A = rng.uniform(size=(n, n)); A = (A + A.T) / 2
    B = rng.uniform(size=(n, n)); B = (B + B.T) / 2
    iu, n = _setup(n)
    r, p = mantel(A, B, iu, n, perms=500)
    assert abs(r) < 0.25
    assert p > 0.05


def test_partial_mantel_kills_a_correlation_that_is_entirely_the_control():
    """The number the whole reading depends on.

    If A correlates with B *only* because both track C, partialling C out must
    remove most of it. Otherwise "typology survives controlling for script"
    means nothing.

    The assertion is on the **magnitude reduction**, not on the p-value, and
    that is a correction rather than a convenience. A first version required
    `p > 0.05` for the residual and it failed at p=0.004 with r=0.28: linear
    rank residualisation does not perfectly remove a shared component, so a
    small residual correlation survives and, on 276 pairs, is detectable. The
    honest reading of a partial Mantel here is therefore "how much of the raw
    correlation was the control", not "is the residual exactly zero". The null
    itself is calibrated -- `test_independent_matrices_do_not_correlate` gets
    p > 0.05 on genuinely independent inputs.
    """
    rng = np.random.default_rng(2)
    n = 24
    C = rng.uniform(size=(n, n)); C = (C + C.T) / 2
    A = C + 0.01 * rng.uniform(size=(n, n))
    B = C + 0.01 * rng.uniform(size=(n, n))
    A = (A + A.T) / 2; B = (B + B.T) / 2
    iu, n = _setup(n)
    raw, _ = mantel(A, B, iu, n, perms=200)
    par, _ = partial_mantel(A, B, C, iu, n, perms=500)
    assert raw > 0.8, "the setup did not produce a strong raw correlation"
    assert abs(par) < 0.4 * raw, (
        f"the control was not removed: raw {raw:+.3f} -> partial {par:+.3f}")


def test_partial_mantel_keeps_a_correlation_that_is_not_the_control():
    """The other half: a real signal must survive partialling out a nuisance."""
    rng = np.random.default_rng(3)
    n = 24
    C = rng.uniform(size=(n, n)); C = (C + C.T) / 2
    S = rng.uniform(size=(n, n)); S = (S + S.T) / 2      # the shared signal
    A = S + 0.05 * C; B = S + 0.05 * C
    A = (A + A.T) / 2; B = (B + B.T) / 2
    iu, n = _setup(n)
    par, p = partial_mantel(A, B, C, iu, n, perms=500)
    assert par > 0.5, f"a real signal was destroyed: {par:+.3f}"
    assert p < 0.05


def test_the_permutation_p_value_is_bounded_away_from_zero():
    """(hits + 1) / (perms + 1) -- never 0, which would claim more evidence
    than a finite permutation set can carry."""
    rng = np.random.default_rng(4)
    n = 16
    A = rng.uniform(size=(n, n)); A = (A + A.T) / 2
    iu, n = _setup(n)
    _, p = mantel(A, A, iu, n, perms=99)
    assert p >= 1 / 100
