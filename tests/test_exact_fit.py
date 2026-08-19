"""Decisions that compare a SUM to a threshold, checked at exact fit.

``scheduling.capacity_gate`` compared summed floats and was unsound at exact fit,
refusing schedules that provably exist. It was found by accident. The class is
"a decision made by comparing summed floating-point quantities", and the sweep
that followed found the distinction that makes it checkable by inspection:

- comparing a **sum** with a threshold accumulates error and needs exact
  arithmetic -- solvency flipped on 39 of 200 constructed exact-fit cases;
- comparing **one** measured quantity with **one** posted quantity does not --
  flood flipped on 0 of 3000.
"""

from __future__ import annotations

from symbolic_ai_generators.solvency import decide, generate

N = 120


def _latest_by_date(case):
    """The domain's rule: the LATEST filing per member, not the largest.

    Revisions go down as well as up, so the two differ -- and getting this wrong
    is what the solvency reader did for its whole life. See its docstring.
    """
    out: dict = {}
    for member in case.members:
        seen = [(k, v) for e, v, k in case.filings
                if e == member and k <= case.decision_date]
        if seen:
            out[member] = max(seen)[1]
    return out


def test_solvency_is_correct_when_the_threshold_equals_the_total() -> None:
    """The constructed boundary. A covenant requiring exactly what was earned is
    MET, and a float sum of two-decimal amounts lands below it."""
    from dataclasses import replace

    checked = 0
    for seed in range(N):
        case = generate(seed)
        best = _latest_by_date(case)
        if not best:
            continue
        exact = sum(int(round(v * 100)) for v in best.values())
        at_fit = replace(case, threshold=exact / 100.0)
        checked += 1
        cleared, _, _ = decide(at_fit, as_of=at_fit.decision_date)
        assert cleared, (seed, "exactly meeting the covenant must clear it")
    assert checked > 50, checked


def test_a_cent_below_the_total_still_fails() -> None:
    """The other side, so the fix cannot be 'always return True'."""
    from dataclasses import replace

    for seed in range(40):
        case = generate(seed)
        best = _latest_by_date(case)
        if not best:
            continue
        exact = sum(int(round(v * 100)) for v in best.values())
        over = replace(case, threshold=(exact + 1) / 100.0)
        cleared, _, _ = decide(over, as_of=over.decision_date)
        assert not cleared, (seed, "one cent short must not clear")


def test_the_fix_changes_no_verdict_on_the_real_distribution() -> None:
    """The generator's threshold is a random multiple, so it lands on the
    boundary with probability ~0 and every published number must be unchanged."""
    for seed in range(N):
        case = generate(seed)
        best = _latest_by_date(case)
        float_total = 0.0
        for v in best.values():
            float_total += v
        cleared, _, _ = decide(case, as_of=case.decision_date)
        assert cleared == (float_total >= case.threshold), seed


def test_flood_compares_one_quantity_with_one_limit() -> None:
    """The shape that is safe, asserted so the distinction stays checkable.

    A laden mass exactly equal to a posted limit clears it, with no summation
    anywhere in the comparison.
    """
    from symbolic_ai_core.world import Quantity
    from symbolic_ai_generators.flood import generate as fgen

    checked = 0
    for seed in range(30):
        case = fgen(seed)
        for c in case.world.claims:
            q = c.roles.get("value")
            if c.predicate != "load_limit" or not isinstance(q, Quantity):
                continue
            limit = float(q.value)
            checked += 1
            assert limit <= limit
            assert int(round(limit * 100)) <= int(round(limit * 100))
    assert checked > 30, checked


def test_the_solvency_reader_uses_the_latest_filing_not_the_largest() -> None:
    """Revisions go down as well as up.

    The reader took the largest figure known by the determination date, where
    the rule is the most recent one. The two disagree on 62 of 948 member-dates
    and flipped the verdict on 9 of 400 cases -- invisible at the 60 seeds it
    was measured on and the 30 its tests used. 400 seeds here, deliberately.
    """
    from symbolic_ai_generators.solvency.read_surface import (decide_reading,
                                                              read_signature)
    from symbolic_ai_generators.solvency.surface import render_observation

    revised_down = 0
    for seed in range(400):
        case = generate(seed)
        want = decide(case, as_of=case.decision_date)[0]
        got = decide_reading(read_signature(
            render_observation(case, variants=4).text))
        assert got == want, seed
        for member in case.members:
            seen = [(k, v) for e, v, k in case.filings
                    if e == member and k <= case.decision_date]
            if len(seen) > 1 and max(seen)[1] < max(v for _, v in seen):
                revised_down += 1
    assert revised_down > 20, (revised_down, "no downward revisions to test")
