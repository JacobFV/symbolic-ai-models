"""Pricing soundness, which the north star cannot see.

``usd_per_solved_above_floor`` counts answers, so a certificate that refuses half
of them makes the row worse however sound it is. ``break_even_wrong_cost`` prices
the trade instead of assuming it: what one wrong answer must cost, in units of
one right answer, for refusing to pay.
"""

from __future__ import annotations

import math

import pytest

from symbolic_ai_core.cost import break_even_wrong_cost


def test_a_system_that_is_never_wrong_can_only_lose_by_refusing():
    assert break_even_wrong_cost(1.0, 0.5, 1.0) == math.inf


def test_keeping_every_correct_answer_for_free_is_free():
    """Solvency's membership certificate: coverage equals accuracy at 1x
    compute, because the certified set IS the correct set."""
    assert break_even_wrong_cost(0.485, 0.485, 1.0) == pytest.approx(0.0)


def test_giving_up_correct_answers_is_not_free_even_at_the_same_compute():
    """Flood's certificate keeps 0.488 of 0.679 correct -- 72% of them -- so it
    needs a wrong answer to cost 0.6x a right one before it pays. I had assumed
    a subset-of-correct certificate was unconditionally worth taking."""
    w = break_even_wrong_cost(0.679, 0.488, 1.0)
    assert 0.5 < w < 0.7


def test_compute_raises_the_bar_and_does_so_monotonically():
    a, k = 0.790, 0.525
    cheap = break_even_wrong_cost(a, k, 1.0)
    dear = break_even_wrong_cost(a, k, 3.07)
    assert dear > cheap
    assert dear == pytest.approx(2.95, abs=0.02)


def test_it_refuses_nonsense_inputs():
    for bad in ((1.2, 0.5, 1.0), (0.5, -0.1, 1.0)):
        with pytest.raises(ValueError):
            break_even_wrong_cost(*bad)
    with pytest.raises(ValueError):
        break_even_wrong_cost(0.5, 0.5, 0.0)
