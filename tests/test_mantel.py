"""The statistics in `scripts/language_typology.py`, checked against cases
whose answer is known in advance.

A partial correlation that quietly does not partial anything out would report
"typology survives controlling for script" and nothing downstream would notice
— the whole reading of that experiment is one number produced by
`partial_mantel`. So it gets the same treatment the floors get: a case it must
pass and a case it must fail.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import language_typology as LT                                # noqa: E402


def _sym(rng, n):
    """A random symmetric matrix with a zero diagonal — a distance matrix in
    shape if not in metric properties, which is all Mantel requires."""
    m = rng.normal(size=(n, n))
    m = np.abs(m + m.T)
    np.fill_diagonal(m, 0.0)
    return m


def test_a_matrix_correlates_perfectly_with_itself():
    rng = np.random.default_rng(0)
    A = _sym(rng, 20)
    r, p = LT.mantel(A, A, perms=199, rng=np.random.default_rng(1))
    assert r == pytest.approx(1.0, abs=1e-9)
    assert p <= 0.01


def test_independent_matrices_do_not_correlate():
    rng = np.random.default_rng(2)
    hits = 0
    for k in range(20):
        A, B = _sym(rng, 18), _sym(rng, 18)
        r, p = LT.mantel(A, B, perms=199, rng=np.random.default_rng(100 + k))
        hits += p < 0.05
    # a well-calibrated test rejects about 5% of 20 independent draws
    assert hits <= 3, f"{hits}/20 false positives — the permutation is not null"


def test_the_permutation_moves_rows_and_columns_together():
    """Permuting only the rows would break the matrix's symmetry and make the
    null distribution too wide, which shows up as a test that never rejects.
    A planted signal has to be detected."""
    rng = np.random.default_rng(3)
    n = 22
    truth = rng.normal(size=n)
    A = np.abs(truth[:, None] - truth[None, :])
    B = A + 0.05 * _sym(rng, n)
    np.fill_diagonal(B, 0.0)
    r, p = LT.mantel(A, B, perms=499, rng=np.random.default_rng(4))
    assert r > 0.9 and p <= 0.01


def test_partial_mantel_kills_a_correlation_that_is_entirely_the_control():
    """A and B are independent given C. The marginal correlation is large and
    the partial one must not be."""
    rng = np.random.default_rng(5)
    n = 26
    c = rng.normal(size=n)
    C = np.abs(c[:, None] - c[None, :])
    A = C + 0.15 * _sym(rng, n)
    B = C + 0.15 * _sym(rng, n)
    for m in (A, B):
        np.fill_diagonal(m, 0.0)
    r_partial, p, r_marginal = LT.partial_mantel(
        A, B, C, perms=499, rng=np.random.default_rng(6))
    assert r_marginal > 0.6, "the setup did not produce a marginal correlation"
    assert abs(r_partial) < 0.25, f"partial r {r_partial} did not shrink"
    assert p > 0.01


def test_partial_mantel_keeps_a_correlation_that_is_not_the_control():
    """The other side of the same coin: a real A-B link that C does not explain
    has to survive, or the control would be a machine for producing nulls."""
    rng = np.random.default_rng(7)
    n = 26
    c, t = rng.normal(size=n), rng.normal(size=n)
    C = np.abs(c[:, None] - c[None, :])
    T = np.abs(t[:, None] - t[None, :])
    A = C + T + 0.1 * _sym(rng, n)
    B = C + T + 0.1 * _sym(rng, n)
    for m in (A, B):
        np.fill_diagonal(m, 0.0)
    r_partial, p, _ = LT.partial_mantel(A, B, C, perms=499,
                                        rng=np.random.default_rng(8))
    assert r_partial > 0.4 and p <= 0.01


def test_one_control_matches_the_closed_form():
    """With a single control the least-squares residual correlation must equal
    the textbook three-correlation formula. Residualising was chosen because it
    generalises to two controls; this pins that the generalisation did not
    change the one-control answer."""
    rng = np.random.default_rng(9)
    n = 24
    A, B, C = _sym(rng, n), _sym(rng, n), _sym(rng, n)
    iu = np.triu_indices(n, 1)
    a, b, c = (LT._rank(m[iu]) for m in (A, B, C))
    rab, rac, rbc = (LT._pearson(a, b), LT._pearson(a, c), LT._pearson(b, c))
    closed = (rab - rac * rbc) / math.sqrt((1 - rac ** 2) * (1 - rbc ** 2))
    got, _, marginal = LT.partial_mantel(A, B, C, perms=1,
                                         rng=np.random.default_rng(10))
    assert got == pytest.approx(closed, abs=1e-9)
    assert marginal == pytest.approx(rab, abs=1e-9)


def test_ranks_average_their_ties():
    """`T_heldout` takes five distinct values over 528 pairs, so nearly every
    entry is tied. Breaking ties by array position would invent an ordering and
    make the correlation an artefact of language order."""
    x = np.array([3.0, 1.0, 1.0, 1.0, 2.0])
    assert LT._rank(x).tolist() == [4.0, 1.0, 1.0, 1.0, 3.0]


def test_the_order_representation_reads_order_and_not_vocabulary():
    """A synthetic pair of "languages" that differ only in linearisation must
    come out at opposite ends of a relation, and two that differ only in which
    words they use must not."""
    from symbolic_ai_core.data.graph import Graph

    def episode(prompt, lang):
        g = Graph()
        root = g.add("give", "pred", -1, 0)
        g.add("alpha", "ident", root, 0)
        g.add("beta", "ident", root, 1)
        return type("E", (), {"graph": g, "prompt": prompt, "language": lang})()

    head_first = [episode("give alpha beta", "vo") for _ in range(40)]
    head_last = [episode("alpha beta give", "ov") for _ in range(40)]
    renamed = [episode("GIVE ALPHA BETA", "loud") for _ in range(40)]
    records = LT._order_records(head_first + head_last + renamed)
    langs = ["loud", "ov", "vo"]
    rates, cols = LT.order_vectors(records, langs, records[4], min_support=10)
    keys = [records[3][c] for c in cols]
    pc = keys.index(("pc", "pred", "ident", 0))
    by = dict(zip(langs, rates[:, pc]))
    assert by["vo"] == pytest.approx(1.0)
    assert by["ov"] == pytest.approx(0.0)
    assert by["loud"] == pytest.approx(1.0), "case folding is meant to be free"
