"""Measured sensitivity, because the predictors were refuted."""

from __future__ import annotations

import pytest

from symbolic_ai_core.runtime.sensitivity import (SensitivityReport,
                                                  input_delta_rate,
                                                  profile_sensitivity)


class TestInputDelta:
    def test_an_unchanged_input_is_not_counted(self):
        assert input_delta_rate({"a": 1}, {"a": 1}) == (0, 1)

    def test_a_deleted_input_counts_as_changed(self):
        """A perturbation that removes an input must not shrink the
        denominator -- that would report a smaller perturbation than happened."""
        assert input_delta_rate({"a": 1, "b": 2}, {"a": 1}) == (1, 2)

    def test_an_invented_input_counts_as_changed(self):
        assert input_delta_rate({"a": 1}, {"a": 1, "b": 2}) == (1, 2)

    def test_a_custom_comparison_can_admit_a_tolerance(self):
        near = lambda a, b: abs(a - b) > 0.01
        assert input_delta_rate({"a": 1.0}, {"a": 1.001}, changed=near) == (0, 1)
        assert input_delta_rate({"a": 1.0}, {"a": 1.5}, changed=near) == (1, 1)


class TestReport:
    def test_amplification_is_output_over_input_rate(self):
        r = SensitivityReport("x", inputs_total=1000, inputs_changed=1,
                              answers_total=1000, answers_changed=10)
        assert r.amplification == pytest.approx(10.0)

    def test_amplification_is_undefined_when_no_input_moved(self):
        """0.0 would read as "this composition is insensitive", which is a
        claim the experiment did not make."""
        r = SensitivityReport("x", inputs_total=10, inputs_changed=0,
                              answers_total=10, answers_changed=0)
        assert r.amplification is None
        assert "undefined" in r.summary()

    def test_an_empty_case_list_does_not_divide_by_zero(self):
        r = SensitivityReport("x", 0, 0, 0, 0)
        assert r.output_rate == 0.0 and r.input_rate == 0.0


class TestProfiling:
    def test_a_pure_passthrough_amplifies_by_one(self):
        a, b = {"k": 1, "j": 1}, {"k": 2, "j": 1}
        r = profile_sensitivity(lambda s, c: s[c], a, b, ["k", "j"],
                                inputs=input_delta_rate(a, b))
        assert r.amplification == pytest.approx(1.0)

    def test_one_moved_input_can_move_many_answers(self):
        """The whole reason this module exists: a shared input reaches
        everything downstream of it."""
        a = {"shared": 0, "x": 1, "y": 2, "z": 3}
        b = dict(a, shared=99)
        r = profile_sensitivity(lambda s, c: s["shared"] + s[c], a, b,
                                ["x", "y", "z"], inputs=input_delta_rate(a, b))
        assert r.answers_changed == 3
        assert r.amplification > 1.0

    def test_an_absent_answer_is_a_value_not_a_gap(self):
        """"unreachable" vs "three hops" is a change, and dropping it would
        discard exactly the cases a perturbation creates."""
        a = {"x": 1}
        b: dict[str, int] = {}
        r = profile_sensitivity(lambda s, c: s.get(c), a, b, ["x"],
                                inputs=input_delta_rate(a, b))
        assert r.answers_changed == 1

    def test_a_perturbation_that_changes_nothing_is_reported_honestly(self):
        a = {"x": 1}
        r = profile_sensitivity(lambda s, c: s[c], a, a, ["x"],
                                inputs=input_delta_rate(a, a))
        assert r.answers_changed == 0 and r.amplification is None
