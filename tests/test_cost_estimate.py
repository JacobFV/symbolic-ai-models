"""Cost before you run it, and the two ways an estimate can be wrong.

`KernelManifest.cost_estimator` existed since the ABI was written and appeared
in exactly one place in the repo: its own declaration. No kernel supplied one,
nothing read one, no test touched one -- the same defect as the delta contract
one stage earlier, and surviving for the same reason.
"""

from __future__ import annotations

import math

import pytest

from symbolic_ai_core.runtime.estimate import (Calibration, Observation,
                                               PowerLawCost, fit_power_law)


def _obs(a: float, b: float, sizes) -> list[Observation]:
    return [Observation(n, a * n ** b) for n in sizes]


class TestObservation:
    def test_a_zero_is_refused_rather_than_logged(self):
        """log(0) is -inf and would poison a least-squares fit silently."""
        with pytest.raises(ValueError, match="positive"):
            Observation(0, 1.0)
        with pytest.raises(ValueError, match="positive"):
            Observation(1.0, 0)


class TestFit:
    def test_it_recovers_an_exact_power_law(self):
        m = fit_power_law(_obs(0.5, 1.5, (10, 20, 40, 80)))
        assert m.a == pytest.approx(0.5, rel=1e-6)
        assert m.b == pytest.approx(1.5, rel=1e-6)

    def test_one_observation_is_refused(self):
        with pytest.raises(ValueError, match="at least 2"):
            fit_power_law([Observation(1, 1)])

    def test_all_the_same_size_is_refused(self):
        """An exponent cannot be fitted from one point on the x axis, and
        returning b=0 would look like a constant-time kernel."""
        with pytest.raises(ValueError, match="same size"):
            fit_power_law([Observation(5, 1.0), Observation(5, 2.0)])

    def test_a_linear_cost_fits_exponent_one(self):
        assert fit_power_law(_obs(3.0, 1.0, (2, 4, 8))).b == pytest.approx(1.0)


class TestCalibration:
    def test_a_perfect_fit_has_no_error(self):
        m = fit_power_law(_obs(0.5, 1.5, (10, 20, 40)))
        c = m.calibrate(_obs(0.5, 1.5, (15, 30)))
        assert c.median_rel_error == pytest.approx(0.0, abs=1e-9)
        assert c.ordering == 1.0 and c.bias == pytest.approx(1.0)

    def test_a_uniformly_low_estimate_orders_perfectly(self):
        """The distinction this class exists for. An estimator 3x low is
        useless by relative error and perfect for routing, and reporting one
        number would hide which."""
        m = PowerLawCost(a=1.0, b=1.0)
        held = [Observation(n, 3.0 * n) for n in (1, 2, 4, 8)]
        c = m.calibrate(held)
        assert c.median_rel_error > 0.6
        assert c.ordering == 1.0
        assert c.bias == pytest.approx(1 / 3, rel=1e-6)

    def test_an_unbiased_but_noisy_estimate_orders_badly(self):
        """The reverse case: good bias, useless for routing."""
        m = PowerLawCost(a=1.0, b=1.0)
        held = [Observation(1, 4.0), Observation(2, 3.0),
                Observation(4, 2.0), Observation(8, 1.0)]
        c = m.calibrate(held)
        assert c.ordering == 0.0

    def test_calibration_needs_held_out_points(self):
        with pytest.raises(ValueError, match="held-out"):
            PowerLawCost(1.0, 1.0).calibrate([])

    def test_equal_costs_are_not_counted_as_an_ordering(self):
        """Two runs that cost the same cannot be ordered right or wrong."""
        m = PowerLawCost(a=1.0, b=1.0)
        c = m.calibrate([Observation(1, 5.0), Observation(2, 5.0)])
        assert c.ordering == 1.0

    def test_the_summary_carries_n(self):
        c = Calibration(n=7, median_rel_error=0.2, p90_rel_error=0.4,
                        ordering=0.9, bias=1.1)
        assert "n=7" in c.summary()


class TestExtrapolationIsTheHardCase:
    def test_a_small_scale_fit_underpredicts_a_steepening_cost(self):
        """Measured on the real engine: fitted over 250-4,000 edges the
        exponent came out 1.04 because fixed overhead dominates there, and the
        prediction for 124,460 was 7x low. The shape is reproduced here so the
        property is pinned rather than remembered."""
        small = [Observation(n, 1.0 + 0.001 * n ** 1.6) for n in (10, 20, 40)]
        m = fit_power_law(small)
        big = [Observation(n, 1.0 + 0.001 * n ** 1.6) for n in (400, 800)]
        c = m.calibrate(big)
        assert c.bias < 1.0, "a flat small-scale fit must under-predict"
        assert c.ordering == 1.0, "and must still order correctly"


class TestTheManifestActuallyCarriesOne:
    def test_the_datalog_kernel_supplies_an_estimator(self):
        from symbolic_ai_kernels.datalog.kernel import MANIFEST
        assert MANIFEST.cost_estimator is not None

    def test_it_returns_a_kernel_cost_that_grows(self):
        from symbolic_ai_kernels.datalog.kernel import estimate_cost
        assert estimate_cost(10_000).cpu_ns > estimate_cost(1_000).cpu_ns > 0

    def test_an_empty_world_costs_nothing(self):
        from symbolic_ai_kernels.datalog.kernel import estimate_cost
        assert estimate_cost(0).cpu_ns == 0

    def test_it_is_within_2x_at_the_top_of_its_fitted_range(self):
        """124,460 edges measured at 5,109.8 ms."""
        from symbolic_ai_kernels.datalog.kernel import estimate_cost
        assert 0.5 < estimate_cost(124_460).cpu_ns / 1e9 / 5.1098 < 2.0


class TestOrderability:
    """Whether a router may use an estimate at all, which is not accuracy."""

    def test_a_wildly_inaccurate_but_monotone_estimate_is_orderable(self):
        """Datalog: 71.3% median error, bias 0.30x, ordering 1.000."""
        c = Calibration(n=5, median_rel_error=0.713, p90_rel_error=0.858,
                        ordering=1.0, bias=0.30)
        assert c.orderable

    def test_an_accurate_but_non_monotone_estimate_is_not(self):
        """SMT across the 3-SAT phase transition: unbiased, ordering 0.667."""
        c = Calibration(n=12, median_rel_error=0.30, p90_rel_error=0.67,
                        ordering=0.667, bias=1.0)
        assert not c.orderable
        assert "NOT orderable" in c.summary()

    def test_the_threshold_is_named_rather_than_inlined(self):
        assert Calibration.ORDERABLE == 0.90

    def test_a_perfect_estimate_is_orderable(self):
        m = fit_power_law(_obs(0.5, 1.5, (10, 20, 40)))
        assert m.calibrate(_obs(0.5, 1.5, (15, 30, 60))).orderable


class TestSMTDeclaresItCannotBeEstimatedBySize:
    def test_the_smt_kernel_says_so_explicitly(self):
        """A kernel whose cost is not ordered by size must say so, or a
        planner will read a small instance and conclude a larger one is
        worse. Measured: 2,250 clauses solved >=7,892x faster than 1,491."""
        from symbolic_ai_kernels.smt.kernel import COST_IS_SIZE_ORDERABLE
        assert COST_IS_SIZE_ORDERABLE is False

    def test_it_offers_no_estimator(self):
        """Offering one would be worse than offering none."""
        from symbolic_ai_kernels.smt.kernel import MANIFEST
        assert MANIFEST.cost_estimator is None

    def test_datalog_by_contrast_does_offer_one(self):
        from symbolic_ai_kernels.datalog.kernel import MANIFEST
        assert MANIFEST.cost_estimator is not None
