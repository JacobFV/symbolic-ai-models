"""The capability-cost ledger, and the four claims it exists to refuse.

Each test here corresponds to a way the old throughput headline could be — and
was — misread. They are written as refusals rather than as behaviours, because
the module's value is entirely in what it will not let you say.
"""

from __future__ import annotations

import json
import math

import pytest

from symbolic_ai_core.cost import (Capability, Price, System, api_component,
                                   capability_from_summary, cpu_component,
                                   ledger, ledger_from_run, ledger_table)


def _cap(rate: float, floor: float, tokens: float = 320.0) -> Capability:
    return Capability(unit="answer", rate=rate, floor=floor, n=1000,
                      tokens_per_attempt=tokens)


def test_throughput_alone_cannot_produce_a_cost_per_answer():
    """A fast system that answers nothing costs infinity per answer.

    This is the whole point. `usd_per_btok_in` for this system is tiny; the
    column that matters is `inf`, and no arrangement of the inputs makes it
    finite while the rate sits at the floor.
    """
    fast = System("fast", (cpu_component("core", 200_000.0),))
    row = ledger(fast, _cap(rate=0.21, floor=0.21))
    assert row.usd_per_btok_in < 0.05                  # genuinely cheap
    assert row.usd_per_solved_above_floor == math.inf  # and bought nothing
    assert any("does not beat its floor" in n for n in row.notes)


def test_a_system_is_priced_by_the_sum_not_by_its_cheapest_part():
    """Adding the parser this repo does not have dominates the bill.

    The misreading being blocked: "our symbolic core is 15-30x past the cost
    target". A system that reached usefulness through a neural parser is priced
    by the parser, and there is no accessor that reports otherwise.
    """
    core = cpu_component("symbolic", 200_000.0)
    alone = System("alone", (core,))
    hybrid = System("hybrid", (core, api_component("parser", 0.30)))
    price = Price()

    assert alone.usd_per_btok_in(price) < 0.05
    assert hybrid.usd_per_btok_in(price) == pytest.approx(
        alone.usd_per_btok_in(price) + 300.0)
    # And the ledger names who is paying, because a total hides it.
    assert hybrid.dominant(price).name == "parser"


def test_latency_is_a_separate_axis_from_money():
    """Cheap per token and unusable per action is a real and common cell."""
    slow = System("slow", (cpu_component("core", 800.0),))
    row = ledger(slow, _cap(rate=0.60, floor=0.21))
    assert row.usd_per_solved_above_floor < 1e-3        # trivially cheap
    assert row.ms_per_action is not None and row.ms_per_action > 100.0
    assert any("exceeds the" in n for n in row.notes)


def test_an_api_component_has_no_derivable_latency():
    """A round trip is not derivable from a price, so it is not invented."""
    hybrid = System("h", (cpu_component("core", 200_000.0),
                          api_component("parser", 0.30)))
    row = ledger(hybrid, _cap(rate=0.60, floor=0.21))
    assert row.ms_per_action is None
    assert any("round trip" in n for n in row.notes)


def test_a_cost_per_answer_needs_tokens_per_answer():
    """Refuses the ratio of two unrelated numbers rather than printing it."""
    system = System("s", (cpu_component("core", 1000.0),))
    with pytest.raises(ValueError, match="tokens_per_attempt"):
        ledger(system, Capability(unit="answer", rate=0.5, floor=0.1,
                                  tokens_per_attempt=0.0))


def test_a_component_without_its_measurement_is_refused():
    with pytest.raises(ValueError, match="tokens_per_sec"):
        cpu_component("core", 0.0)
    with pytest.raises(ValueError, match="usd_per_mtok_in"):
        api_component("parser", None)                          # type: ignore[arg-type]


def test_capability_carries_its_floor_and_cannot_default_it():
    """`floor` has no default: a rate without one cannot make an honest row."""
    with pytest.raises(TypeError):
        Capability(unit="answer", rate=0.5)                    # type: ignore[call-arg]


def test_fit_plus_eval_time_is_marked_not_quotable(tmp_path):
    """A run with no timing record still produces a row — flagged, not silent.

    The alternative designs are both worse: refusing to print anything hides
    the shape of the table, and printing without the flag is how a fit time
    becomes an inference rate in someone's write-up three weeks later.
    """
    run = tmp_path / "run"
    run.mkdir()
    (run / "summary.json").write_text(json.dumps({
        "model": "toy", "seconds": 10.0, "n_eval": 100, "parameters": 1000,
        "n_train": 500, "config": {"max_len": 320},
        "final": {"lm": {"answer_acc": 0.40, "answer_floor": 0.21,
                         "answer_n": 100}},
    }))
    row = ledger_from_run(run, "answer")
    assert row is not None
    assert row.basis == "fit+eval"
    assert row.quotable is False
    assert "NOT QUOTABLE" in ledger_table([row])


def test_a_timing_record_beside_the_run_is_believed(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "summary.json").write_text(json.dumps({
        "model": "toy", "seconds": 10.0, "n_eval": 100,
        "config": {"max_len": 320},
        "final": {"lm": {"answer_acc": 0.40, "answer_floor": 0.21,
                         "answer_n": 100}},
    }))
    (run / "timing.json").write_text(json.dumps({"tokens_per_sec": 200_000.0}))
    row = ledger_from_run(run, "answer")
    assert row is not None and row.quotable and row.basis == "measured"


def test_units_are_distinct_and_absent_is_not_zero():
    """A run that did not score a unit yields None, not a row of zeros."""
    summary = {
        "config": {"max_len": 320},
        "final": {"node": {"label_acc": 0.5, "label_floor": 0.1,
                           "label_n": 900}},
    }
    assert capability_from_summary(summary, "answer") is None
    prop = capability_from_summary(summary, "proposition")
    assert prop is not None and prop.rate == 0.5 and prop.floor == 0.1


def test_the_table_sorts_on_the_column_that_cannot_be_gamed():
    """Cheapest-per-token must not be able to reach the top of the table."""
    cheap_useless = ledger(System("cheap", (cpu_component("c", 1e6),)),
                           _cap(rate=0.21, floor=0.21))
    dear_useful = ledger(System("dear", (cpu_component("d", 100.0),)),
                         _cap(rate=0.80, floor=0.21))
    assert cheap_useless.usd_per_btok_in < dear_useful.usd_per_btok_in
    table = ledger_table([cheap_useless, dear_useful])
    assert table.index("dear") < table.index("cheap")


# --- the perverse regime the flood routing sweep found --------------------
def _row(name, rate, per_solved, per_attempt, floor=0.440):
    from symbolic_ai_core.cost import Ledger, Price
    return Ledger(system=name, unit="answer", price=Price(), basis="measured",
                  quotable=True, usd_per_btok_in=1.0,
                  usd_per_attempt=per_attempt,
                  usd_per_solved=per_attempt / rate,
                  usd_per_solved_above_floor=per_solved,
                  ms_per_action=None, bytes_per_retained_proposition=None,
                  rate=rate, floor=floor, n=800, dominant_component="cpu")


#: The measured flood-task frontier: a 0.887-accuracy arm outranks a 1.000 one.
FLOOD = [_row("lossless", 1.000, 2.058e-8, 1.152e-8),
         _row("slack-1.4", 0.887, 2.001e-8, 8.954e-9)]


def test_the_ratio_really_does_prefer_the_less_capable_arm():
    """Not hypothetical. These are the measured numbers, and if this assertion
    ever fails the finding it guards has stopped being true."""
    from symbolic_ai_core.cost import perverse_regime

    pair = perverse_regime(FLOOD)
    assert pair is not None
    winner, better = pair
    assert winner.system == "slack-1.4" and better.system == "lossless"
    assert winner.rate < better.rate


def test_the_table_says_so_rather_than_letting_the_reader_take_the_top_row():
    from symbolic_ai_core.cost import ledger_table

    out = ledger_table(FLOOD)
    assert "PERVERSE REGIME" in out
    assert "slack-1.4" in out and "lossless" in out
    assert out.index("slack-1.4") < out.index("lossless"), (
        "the sort should still be by the ratio; the warning is the guard, not "
        "a resort that would hide which column was used")


def test_no_warning_when_the_ratio_winner_is_also_the_most_capable():
    """The case the metric was designed for, and handles correctly."""
    from symbolic_ai_core.cost import ledger_table, perverse_regime

    rows = [_row("good", 1.000, 1.0e-8, 1.0e-8),
            _row("weak", 0.600, 3.0e-8, 4.0e-9)]
    assert perverse_regime(rows) is None
    assert "PERVERSE REGIME" not in ledger_table(rows)


def test_cheapest_above_is_the_question_worth_asking():
    from symbolic_ai_core.cost import cheapest_above

    assert cheapest_above(FLOOD, 0.95).system == "lossless"
    assert cheapest_above(FLOOD, 0.80).system == "slack-1.4"
    assert cheapest_above(FLOOD, 1.01) is None


def test_the_table_reports_the_constrained_winner_and_who_missed_the_bar():
    from symbolic_ai_core.cost import ledger_table

    out = ledger_table(FLOOD, min_rate=0.95)
    assert "cheapest at rate >= 0.950: lossless" in out
    assert "below the bar: slack-1.4" in out


def test_an_unreachable_bar_says_what_the_best_actually_is():
    from symbolic_ai_core.cost import ledger_table

    out = ledger_table(FLOOD, min_rate=1.01)
    assert "no system reaches" in out and "1.000" in out


def test_a_row_at_or_below_its_floor_is_excluded_from_the_check():
    """An infinite ratio is a correct entry, not a candidate for 'winner'."""
    from symbolic_ai_core.cost import perverse_regime

    import math
    rows = FLOOD + [_row("floor-bound", 0.440, math.inf, 1.0e-9)]
    pair = perverse_regime(rows)
    assert pair is not None and pair[0].system == "slack-1.4"
