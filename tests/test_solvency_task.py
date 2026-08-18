"""A covenant test over revised filings: the second generated task.

Structurally the opposite of the flood one -- no routing, no discrete search, no
subset answer. One boolean per group per decision date, and the whole difficulty
is that the figures were revised after the decision.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency.world import _day
from symbolic_ai_kernels import KernelRequest, get_kernel

K = get_kernel("economy@1")


def test_generation_is_a_pure_function_of_its_seed():
    a, b = generate(11), generate(11)
    assert a.world.to_dict() == b.world.to_dict()
    assert a.filings == b.filings and a.threshold == b.threshold


def test_the_covenant_bar_does_not_know_which_way_the_revisions_went():
    """Look-ahead in the generator of a task about look-ahead would make the
    whole measurement circular. The bar is drawn from the FIRST-vintage total."""
    for s in range(40):
        c = generate(s)
        lo, hi = c.meta["first_total"] * 0.93, c.meta["first_total"] * 1.07
        assert lo <= c.threshold <= hi


def test_the_task_is_not_degenerate():
    outcomes = {decide(generate(s), as_of=generate(s).decision_date)[0]
                for s in range(60)}
    assert outcomes == {True, False}, "every case decided the same way"


# --- the kernel against an oracle that shares no code with it ------------
def test_the_kernel_agrees_with_the_independent_oracle():
    for s in range(80):
        c = generate(s)
        r = K.run(K.project(c.world, KernelRequest()),
                  KernelRequest(params={"as_of": c.decision_date,
                                        "period": "2026Q1", "of": [c.group]}))
        _, oracle_total, complete = decide(c, as_of=c.decision_date)
        if not r.claims:
            assert not complete
            continue
        assert r.claims[0].roles["value"].value == pytest.approx(oracle_total), c.seed


def test_the_oracle_shares_no_code_with_the_kernel():
    import inspect

    from symbolic_ai_generators.solvency import world as W

    src = inspect.getsource(W.decide)
    for forbidden in ("economy@1", "get_kernel", "project_world", "as_of_value"):
        assert forbidden not in src


# --- the finding, pinned -------------------------------------------------
def test_look_ahead_is_dominated_by_existence_not_by_revision():
    """The result worth keeping: a backtest that carefully uses first-vintage
    figures but ignores publication LAG still gets ~48% of early decisions
    wrong, against ~10% from revision alone."""
    def rate(offset):
        when = _day(offset)
        n = dis = miss = rev = 0
        for s in range(200):
            c = replace(generate(s), decision_date=when)
            a_ok, _, complete = decide(c, as_of=when)
            l_ok, _, _ = decide(c, as_of="2099-01-01")
            n += 1
            if a_ok != l_ok:
                dis += 1
                miss += not complete
                rev += complete
        return dis / n, miss / n, rev / n

    early_dis, early_miss, early_rev = rate(40)
    mid_dis, mid_miss, mid_rev = rate(90)
    late_dis, _, _ = rate(300)

    assert early_dis > 0.35, f"early disagreement only {early_dis}"
    assert early_miss > 5 * max(early_rev, 1e-9), (
        "early bias was not dominated by missing data")
    assert mid_miss == 0.0 and mid_rev > 0.05, (
        "the mid window should isolate revision alone")
    assert early_dis > 3 * mid_dis
    assert late_dis == 0.0, (
        "once every revision has landed, as-of and latest must agree")


def test_a_figure_not_yet_filed_is_absent_rather_than_zero():
    """A zero here would make every early total look like a collapse."""
    c = replace(generate(3), decision_date=_day(10))
    ok, total, complete = decide(c, as_of=c.decision_date)
    assert not complete and total == 0.0 and not ok
    r = K.run(K.project(c.world, KernelRequest()),
              KernelRequest(params={"as_of": c.decision_date,
                                    "period": "2026Q1", "of": [c.group]}))
    assert r.claims == (), "the kernel invented a total from nothing"
    assert r.artifacts["coverage"][0]["reported"] == 0
