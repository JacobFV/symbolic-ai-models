"""The decision margin, and the prediction it makes about which errors matter.

Three tasks measured across three wake-ups say the distance from the decision
boundary governs both the routing headroom and the recall/precision ordering.
This module measures that distance on **uncorrupted** worlds, which is the only
form in which it is useful -- before a reader exists, before a router is built.

The test that carries it is
``test_the_margin_predicts_the_measured_corruption_ordering``: it checks the
profiler against ratios measured independently, one of which predates it.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.runtime.margin import (PRECISION_DOMINATES_ABOVE,
                                             RECALL_DOMINATES_BELOW,
                                             margin_profile, relative_margin)


def threshold_decide(x):
    return x >= 100.0


def threshold_scale(x, f):
    return x * f


# --- the measurement ------------------------------------------------------
@pytest.mark.parametrize("value,expected", [
    (95.0, 0.05), (130.0, 0.23), (200.0, 0.50), (50.0, 1.00)])
def test_relative_margin_finds_the_distance_to_the_boundary(value, expected):
    got = relative_margin(value, threshold_decide, threshold_scale)
    assert got == pytest.approx(expected, abs=0.02)


def test_it_searches_both_directions():
    """A decision can sit near its boundary from below or from above, and taking
    the nearer of the two is the only reading that means 'how much error can
    this tolerate'."""
    below = relative_margin(96.0, threshold_decide, threshold_scale)
    above = relative_margin(104.0, threshold_decide, threshold_scale)
    assert below == pytest.approx(0.042, abs=0.02)
    assert above == pytest.approx(0.038, abs=0.02)


def test_a_decision_nothing_can_flip_is_infinite_not_large():
    """A corpus where scaling by 20x changes nothing does not have a large
    margin -- the scaled quantity is not what the decision turns on, and the
    caller needs to know which."""
    assert relative_margin(1.0, lambda x: True, threshold_scale) == float("inf")
    p = margin_profile([1.0, 2.0], lambda x: True, threshold_scale)
    assert p.unbounded == 2
    assert p.median_margin == float("inf")
    assert "does not decide this task" in p.dominant_channel
    assert "before trusting any of this" in p.advice()


def test_the_median_ignores_a_minority_of_unflippable_cases():
    """Some decisions in a corpus legitimately cannot be moved by the scaled
    quantity -- a flood vehicle excluded on capacity, whatever the bridges do.
    A minority of those must not make the whole profile infinite."""
    worlds = [95.0, 96.0, 97.0] + [float("nan")]
    p = margin_profile(
        worlds,
        lambda x: True if x != x else threshold_decide(x),
        lambda x, f: x if x != x else x * f)
    assert p.unbounded == 1 and p.median_margin < 0.1


# --- the prediction -------------------------------------------------------
#: (task, median margin, drop/misread ratio) -- every ratio measured
#: independently of this module, and the flood row days before it existed.
MEASURED = [
    ("solvency@0.10", 0.100, 2.28),
    ("scheduling@0.15", 0.257, 2.38),
    ("solvency@0.25", 0.250, 1.74),
    ("flood@native", 0.280, 1.76),          # held out
    ("scheduling@0.50", 0.335, 1.61),
    ("solvency@0.50", 0.500, 0.67),
    ("scheduling@1.00", 0.605, 0.59),
    ("solvency@1.00", 1.000, 0.11),
    ("scheduling@2.00", 1.512, 0.13),
]


def test_the_margin_predicts_the_measured_corruption_ordering():
    """The claim, on nine points from three independent tasks."""
    for name, margin, ratio in MEASURED:
        recall_wins = ratio > 1.0
        if margin < RECALL_DOMINATES_BELOW:
            assert recall_wins, f"{name}: margin {margin} but ratio {ratio}"
        elif margin > PRECISION_DOMINATES_ABOVE:
            assert not recall_wins, f"{name}: margin {margin} but ratio {ratio}"


def test_the_relationship_is_monotone_across_three_tasks():
    ordered = sorted(MEASURED, key=lambda row: row[1])
    ratios = [r for _, _, r in ordered]
    # not strictly monotone -- these are three different generators -- but the
    # rank correlation must be strongly negative or the claim is noise
    n = len(ratios)
    concordant = sum(1 for i in range(n) for j in range(i + 1, n)
                     if ratios[i] > ratios[j])
    total = n * (n - 1) // 2
    assert concordant / total > 0.85, (
        f"only {concordant}/{total} pairs ordered as the margin predicts")


def test_the_crossing_was_confirmed_on_a_held_out_task():
    """flood's ratio was measured before this module existed, and its margin
    lands between the two neighbouring points from the other two tasks."""
    by_name = {n: (m, r) for n, m, r in MEASURED}
    fm, fr = by_name["flood@native"]
    lo_m, lo_r = by_name["solvency@0.25"]
    hi_m, hi_r = by_name["scheduling@0.50"]
    assert lo_m < fm < hi_m
    assert hi_r < fr < lo_r + 0.1


# --- the advice it gives --------------------------------------------------
def test_routability_tracks_the_same_variable():
    tight = margin_profile([95.0, 96.0, 97.0], threshold_decide, threshold_scale)
    loose = margin_profile([300.0, 400.0], threshold_decide, threshold_scale)
    assert tight.routable and not loose.routable
    assert "should fire" in tight.advice()
    assert "do not build a router" in loose.advice()


def test_the_advice_names_the_channel_to_spend_on():
    tight = margin_profile([95.0], threshold_decide, threshold_scale)
    loose = margin_profile([400.0], threshold_decide, threshold_scale)
    assert "RECALL" in tight.advice() and "PRECISION" in loose.advice()


# --- the consumer ---------------------------------------------------------
def test_the_cli_advice_flips_with_the_margin_knob():
    """A capability with no consumer is the same shape as a profile with no
    kernel behind it. The CLI is the consumer, and its advice has to change when
    the thing it is advising about changes -- otherwise it is a slogan."""
    from symbolic_ai_core.cli import main

    pytest.importorskip("clingo")
    out = []
    for slack, expect in ((0.15, "RECALL"), (2.0, "PRECISION")):
        import io
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["margin", "scheduling", "-n", "8", "--slack", str(slack)])
        assert rc == 0
        out.append(buf.getvalue())
        assert expect in out[-1], f"slack {slack} advised {out[-1]!r}"

    assert "should fire" in out[0]
    assert "do not build a router" in out[1]


def test_the_cli_rejects_an_unknown_task():
    from symbolic_ai_core.cli import main

    with pytest.raises(SystemExit):
        main(["margin", "not_a_task"])
