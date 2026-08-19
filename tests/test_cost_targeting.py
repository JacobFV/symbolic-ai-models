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


class TestTheTargetingColumnsHaveTheirOwnPerverseRegime:
    """`scripts/what_soundness_costs.py` measured a sound margin at 16.1x aim
    and a relaxed, UNSOUND one at 76.8x while serving 0.62% of answers wrong.
    aim x rises with unsoundness because the flagged share falls faster than the
    quality does, so the column can be gamed and the table must say so."""

    @staticmethod
    def _row(name: str, flagged: float, rate: float, base: float = 0.9924):
        from symbolic_ai_core.cost import Targeting
        blind = base + flagged * (1.0 - base)
        return ledger(
            System(name=name, components=(cpu_component("r", 1e7,
                                                        source="t"),)),
            Capability(unit="answer", rate=rate, floor=base, n=5000,
                       tokens_per_attempt=1.0, source="t"),
            targeting=Targeting(escalated=flagged, rate_base=base,
                                rate_targeted=rate, rate_blind=blind,
                                escalated_usd_per_attempt=1e-12))

    def test_aim_really_does_prefer_the_unsound_arm(self):
        sound = self._row("sound", 0.0622, 1.0)
        unsound = self._row("relaxed", 0.0024, 0.9938)
        assert unsound.targeting_lift > sound.targeting_lift
        assert unsound.rate < sound.rate

    def test_the_table_names_the_pair_rather_than_letting_it_pass(self):
        from symbolic_ai_core.cost import ledger_table
        out = ledger_table([self._row("sound", 0.0622, 1.0),
                            self._row("relaxed", 0.0024, 0.9938)])
        assert "TARGETING REGIME" in out
        assert "aiming better by answering worse" in out
        assert "SAME rate" in out

    def test_no_warning_when_the_aim_winner_is_also_the_most_accurate(self):
        from symbolic_ai_core.cost import ledger_table, targeting_regime
        rows = [self._row("oracle", 0.0076, 1.0),
                self._row("margin", 0.0622, 1.0)]
        assert targeting_regime(rows) is None
        assert "TARGETING REGIME" not in ledger_table(rows)

    def test_a_single_targeting_row_cannot_be_a_regime(self):
        from symbolic_ai_core.cost import targeting_regime
        assert targeting_regime([self._row("only", 0.0622, 1.0)]) is None

    def test_rows_without_a_targeting_claim_are_ignored_by_the_check(self):
        from symbolic_ai_core.cost import targeting_regime
        plain = ledger(
            System(name="plain", components=(cpu_component("r", 1e7,
                                                           source="t"),)),
            Capability(unit="answer", rate=1.0, floor=0.5, n=10,
                       tokens_per_attempt=1.0, source="t"))
        assert targeting_regime([plain, self._row("aimed", 0.0622, 1.0)]) is None


class TestThePairwiseInversionTheGlobalCheckMissed:
    """Measured on the structural back-off: `ilp-001` with the back-off off aims
    1.41x against on's 1.37x while answering 0.291 against 0.312 -- and the
    first version of `targeting_regime` missed it, because `ruleinduce-001` off
    held both the best aim and the best rate."""

    @staticmethod
    def _row(name: str, aim_rate: tuple[float, float]):
        from symbolic_ai_core.cost import Targeting
        rate, flagged = aim_rate[0], 0.2
        base = rate
        # choose a_abstained so that aim comes out where we want it
        aim = aim_rate[1]
        a_abst = 1.0 - aim * (1.0 - base)
        targeted = base + flagged * (1.0 - a_abst)
        blind = base + flagged * (1.0 - base)
        return ledger(
            System(name=name, components=(cpu_component("r", 1e7,
                                                        source="t"),)),
            Capability(unit="label", rate=rate, floor=0.143, n=5233,
                       tokens_per_attempt=1.0, source="t"),
            targeting=Targeting(escalated=flagged, rate_base=base,
                                rate_targeted=targeted, rate_blind=blind,
                                escalated_usd_per_attempt=1e-9))

    def _table(self):
        return [self._row("ruleinduce-off", (0.329, 1.49)),
                self._row("ruleinduce-on", (0.329, 1.45)),
                self._row("ilp-on", (0.312, 1.37)),
                self._row("ilp-off", (0.291, 1.41))]

    def test_the_inversion_is_found_even_when_a_third_row_tops_both_columns(self):
        from symbolic_ai_core.cost import targeting_regime
        rows = self._table()
        top_aim = max(rows, key=lambda r: r.targeting_lift)
        top_rate = max(rows, key=lambda r: r.rate)
        assert top_aim.system == top_rate.system   # the global check sees nothing
        pair = targeting_regime(rows)
        assert pair is not None
        w, b = pair
        assert w.targeting_lift > b.targeting_lift and w.rate < b.rate

    def test_the_table_warns_on_the_real_shape(self):
        from symbolic_ai_core.cost import ledger_table
        out = ledger_table(self._table())
        assert "TARGETING REGIME" in out
        assert "aiming better by answering worse" in out

    def test_a_concordant_table_still_says_nothing(self):
        from symbolic_ai_core.cost import ledger_table, targeting_regime
        rows = [self._row("good", (0.900, 3.0)), self._row("worse", (0.500, 1.2))]
        assert targeting_regime(rows) is None
        assert "TARGETING REGIME" not in ledger_table(rows)
