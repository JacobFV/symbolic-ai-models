"""A capability whose value is targeting, and the floor that keeps it honest.

`notes/findings/2026-08-18-determinacy-is-not-accuracy-...md` ran a federated
resolver through `symbolic_ai_core.cost` and it scored **inf** -- it did not beat
a floor holding its own candidate sets. The same system's determinacy signal
separated **95.8%** accuracy from **40.4%**, and aiming a fixed escalation budget
with it bought **4.69x** more quality than spending that budget at random.

Both facts are true at once, and no column in the ledger could show the second.
These tests pin the denominator that can.
"""

from __future__ import annotations

import math

import pytest

from symbolic_ai_core.cost import (Capability, Price, System, Targeting,
                                   api_component, cpu_component, ledger,
                                   ledger_table)

#: `notes/findings/2026-08-18-the-million-fold-advantage-is-8x-...md`, table 1.
#: Quality with no escalation, and with each tier escalated to a perfect model.
OPENALEX_BASE = 0.526
OPENALEX_SILENT_SHARE, OPENALEX_SILENT_QUALITY = 0.123, 0.650
OPENALEX_AMBIG_SHARE, OPENALEX_AMBIG_QUALITY = 0.383, 0.712


def _sys() -> System:
    return System(name="resolver", components=(
        cpu_component("symbolic", 1e7, source="test"),))


def _cap(rate: float = 0.873, floor: float = 0.874) -> Capability:
    return Capability(unit="answer", rate=rate, floor=floor, n=1015,
                      tokens_per_attempt=41.0, source="test")


def _blind(base: float, share: float) -> float:
    """Quality from escalating `share` at random to a perfect tier."""
    return base + share * (1.0 - base)


class TestTargetingRefusesWhatCapabilityRefuses:
    def test_a_targeted_rate_cannot_be_carried_without_its_blind_floor(self):
        with pytest.raises(TypeError):
            Targeting(escalated=0.154, rate_base=0.873,      # type: ignore[call-arg]
                      rate_targeted=0.965,
                      escalated_usd_per_attempt=6.15e-4)

    def test_a_targeting_claim_with_no_budget_is_not_a_claim(self):
        for bad in (0.0, -0.1, 1.5):
            with pytest.raises(ValueError, match="escalated"):
                Targeting(escalated=bad, rate_base=0.5, rate_targeted=0.6,
                          rate_blind=0.55, escalated_usd_per_attempt=1e-3)

    def test_a_rate_outside_zero_one_is_refused(self):
        with pytest.raises(ValueError, match="rate_targeted"):
            Targeting(escalated=0.2, rate_base=0.5, rate_targeted=1.4,
                      rate_blind=0.6, escalated_usd_per_attempt=1e-3)


class TestItReproducesTheTwoDomainsAlreadyMeasured:
    """The numbers below were computed by hand and recorded in
    `notes/autonomy/predictions.jsonl` BEFORE the implementation existed, so the
    implementation could not be fitted to whatever it happened to produce."""

    def test_silence_is_worth_routing_on(self):
        t = Targeting(
            escalated=OPENALEX_SILENT_SHARE, rate_base=OPENALEX_BASE,
            rate_targeted=OPENALEX_SILENT_QUALITY,
            rate_blind=_blind(OPENALEX_BASE, OPENALEX_SILENT_SHARE),
            escalated_usd_per_attempt=4.535e-3)
        row = ledger(_sys(), _cap(), targeting=t)
        assert row.targeting_lift == pytest.approx(2.13, abs=0.01)

    def test_ambiguity_is_worth_nothing_and_the_row_says_so(self):
        """The escalation-frontier finding called this signal weak. Priced, it
        is worth 1.02x -- which is to say, nothing over spending at random."""
        t = Targeting(
            escalated=OPENALEX_AMBIG_SHARE, rate_base=OPENALEX_BASE,
            rate_targeted=OPENALEX_AMBIG_QUALITY,
            rate_blind=_blind(OPENALEX_BASE, OPENALEX_AMBIG_SHARE),
            escalated_usd_per_attempt=4.535e-3)
        row = ledger(_sys(), _cap(), targeting=t)
        assert row.targeting_lift == pytest.approx(1.02, abs=0.01)
        assert any("not worth routing on" in n for n in row.notes)

    def test_the_two_signals_are_ranked_the_way_the_finding_ranked_them(self):
        rows = []
        for share, quality in ((OPENALEX_SILENT_SHARE, OPENALEX_SILENT_QUALITY),
                               (OPENALEX_AMBIG_SHARE, OPENALEX_AMBIG_QUALITY)):
            rows.append(ledger(_sys(), _cap(), targeting=Targeting(
                escalated=share, rate_base=OPENALEX_BASE,
                rate_targeted=quality,
                rate_blind=_blind(OPENALEX_BASE, share),
                escalated_usd_per_attempt=4.535e-3)))
        silent, ambiguous = rows
        assert silent.targeting_lift > ambiguous.targeting_lift
        # and the price of a quality point says the same thing more sharply
        assert silent.usd_per_quality_point < ambiguous.usd_per_quality_point


class TestAnUninformativeSignalCostsInfinity:
    def test_targeting_no_better_than_blind_reads_inf(self):
        t = Targeting(escalated=0.2, rate_base=0.5, rate_targeted=0.60,
                      rate_blind=0.60, escalated_usd_per_attempt=1e-3)
        row = ledger(_sys(), _cap(), targeting=t)
        assert row.usd_per_quality_point == math.inf
        assert any("not informative" in n for n in row.notes)

    def test_targeting_worse_than_blind_also_reads_inf_rather_than_negative(self):
        """A negative cost per point would sort to the top of the table."""
        t = Targeting(escalated=0.2, rate_base=0.5, rate_targeted=0.55,
                      rate_blind=0.60, escalated_usd_per_attempt=1e-3)
        row = ledger(_sys(), _cap(), targeting=t)
        assert row.usd_per_quality_point == math.inf


class TestTheGapThisCloses:
    def test_a_system_at_inf_on_accuracy_can_still_be_worth_paying_for(self):
        """The whole reason this exists: the resolver scores inf above floor and
        is worth 4.69x on targeting, and both are true of the same row."""
        t = Targeting(escalated=0.154, rate_base=0.873, rate_targeted=0.965,
                      rate_blind=_blind(0.873, 0.154),
                      escalated_usd_per_attempt=6.15e-4)
        row = ledger(_sys(), _cap(rate=0.873, floor=0.874), targeting=t)
        assert row.usd_per_solved_above_floor == math.inf
        assert row.targeting_lift == pytest.approx(4.69, abs=0.02)
        assert math.isfinite(row.usd_per_quality_point)


class TestTheTable:
    def test_a_table_of_rows_without_targeting_is_unchanged(self):
        out = ledger_table([ledger(_sys(), _cap(rate=0.9, floor=0.5))])
        assert "aim x" not in out and "$/pt" not in out

    def test_the_columns_appear_when_a_row_carries_a_claim(self):
        t = Targeting(escalated=0.154, rate_base=0.873, rate_targeted=0.965,
                      rate_blind=_blind(0.873, 0.154),
                      escalated_usd_per_attempt=6.15e-4)
        out = ledger_table([ledger(_sys(), _cap(rate=0.9, floor=0.5),
                                   targeting=t)])
        assert "aim x" in out and "$/pt" in out
        assert "blindly" in out

    def test_a_mixed_table_renders_the_row_without_a_claim_as_a_dash(self):
        t = Targeting(escalated=0.154, rate_base=0.873, rate_targeted=0.965,
                      rate_blind=_blind(0.873, 0.154),
                      escalated_usd_per_attempt=6.15e-4)
        api = System(name="model", components=(
            api_component("frontier", 15.0, source="list"),))
        out = ledger_table([ledger(_sys(), _cap(rate=0.9, floor=0.5),
                                   targeting=t),
                            ledger(api, _cap(rate=1.0, floor=0.5),
                                   price=Price())])
        assert "aim x" in out
        assert " -" in out
