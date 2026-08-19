"""The rung a read set cannot reach, derived rather than supplied.

`notes/findings/2026-08-18-over-approximation-is-a-property-of-the-answer-...md`
measured two queries with **byte-identical read sets**, the same inputs and 9 ns
of cost between them, over-approximating **1.1x** and **79.8x**. What a
certificate wastes is a property of the answer's sensitivity, and a mechanism
that records reads cannot see it.

The slack is not hidden, though: `is_widely_held` computes `len(holders) >= 100`
and `|count - 100|` is an intermediate the computation already produced. These
tests pin the derivation, and above all pin **soundness** -- a margin that ever
declares valid for an answer that moved is worse than no margin.
"""

from __future__ import annotations

import math

import pytest

from symbolic_ai_core.runtime.certificate import (Counted, Sensitivity,
                                                  certify, moved_elements,
                                                  revalidate_sensitive)


class TestTheSlackComesFromTheComputation:
    def test_a_threshold_far_above_the_boundary_has_slack_to_spare(self):
        held, s = Counted(140).at_least(100)
        assert held and s.slack == 41.0          # tolerates a fall of 40

    def test_a_threshold_below_the_boundary_measures_the_climb(self):
        held, s = Counted(97).at_least(100)
        assert not held and s.slack == 3.0       # tolerates a rise of 2

    def test_sitting_exactly_on_the_boundary_still_has_one_step(self):
        held, s = Counted(100).at_least(100)
        assert held and s.slack == 1.0

    def test_a_raw_count_has_no_slack_and_that_is_correct(self):
        value, s = Counted(140).raw()
        assert value == 140 and s.slack == 0.0
        assert not s.survives(1)
        assert s.survives(0)


class TestSoundness:
    """The property that matters. A loose margin costs money; an unsound one
    silently serves a wrong answer, and this repo would rather have neither."""

    @pytest.mark.parametrize("count,k", [(140, 100), (97, 100), (100, 100),
                                         (1, 100), (250, 100), (0, 1)])
    @pytest.mark.parametrize("delta", range(-6, 7))
    def test_a_surviving_margin_never_hides_a_flipped_answer(self, count, k,
                                                             delta):
        new_count = max(0, count + delta)
        held, s = Counted(count).at_least(k)
        if s.survives(abs(new_count - count)):
            assert (new_count >= k) == held, (
                f"margin survived while {count}->{new_count} crossed {k}")

    def test_an_unknown_lipschitz_survives_only_a_frozen_input(self):
        s = Sensitivity(slack=1e9, lipschitz=math.inf)
        assert s.survives(0)
        assert not s.survives(1)

    def test_a_negative_slack_is_refused_rather_than_clamped(self):
        with pytest.raises(ValueError, match="slack"):
            Sensitivity(slack=-1.0)


class TestMovedElements:
    def test_a_symmetric_difference_counts_both_directions(self):
        old = {"a": frozenset({1, 2, 3})}
        new = {"a": frozenset({2, 3, 4})}
        assert moved_elements(["a"], old, new) == 2

    def test_it_over_estimates_a_count_and_that_is_the_documented_price(self):
        """One in, one out: the count did not move, the symmetric difference
        says two. The looseness is bounded and measurable, not unknown."""
        old = {"a": frozenset({1, 2, 3})}
        new = {"a": frozenset({1, 2, 4})}
        assert len(old["a"]) == len(new["a"])
        assert moved_elements(["a"], old, new) == 2

    def test_an_absent_key_counts_the_whole_set(self):
        assert moved_elements(["a"], {}, {"a": frozenset({1, 2})}) == 2
        assert moved_elements(["a"], {"a": frozenset({1, 2})}, {}) == 2

    def test_a_non_set_value_that_moved_counts_once(self):
        assert moved_elements(["a"], {"a": 1}, {"a": 2}) == 1
        assert moved_elements(["a"], {"a": 1}, {"a": 1}) == 0


class TestItBeatsTheReadSetOnTheCaseThatMotivatedIt:
    def test_a_threshold_survives_churn_that_invalidates_a_read_set(self):
        old = {("holders", "S"): frozenset(f"f{i}" for i in range(140))}
        new = {("holders", "S"): frozenset(
            [f"f{i}" for i in range(2, 140)] + ["x", "y"])}
        cert = certify(lambda st: len(st[("holders", "S")]) >= 100, old)
        # the read set moved, so an equality-based certificate must invalidate
        assert old[("holders", "S")] != new[("holders", "S")]
        # the answer did not, and the derived margin sees that
        _, sens = Counted(len(old[("holders", "S")])).at_least(100)
        assert revalidate_sensitive(cert, sens, old, new)

    def test_and_it_still_invalidates_when_the_answer_really_moves(self):
        old = {("holders", "S"): frozenset(f"f{i}" for i in range(101))}
        new = {("holders", "S"): frozenset(f"f{i}" for i in range(50))}
        cert = certify(lambda st: len(st[("holders", "S")]) >= 100, old)
        _, sens = Counted(101).at_least(100)
        assert not revalidate_sensitive(cert, sens, old, new)
