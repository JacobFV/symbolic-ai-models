"""Miramax in miniature, so the real-text failure is reproducible here.

On 168 Wikipedia company intros a sentence-level staleness gate answered with a
**former** parent, because one sentence carried a dead owner and a live one and
the gate deleted the wrong half. No generated surface could produce that: each
puts one claim in one sentence.

``stale_clause`` prefixes a **real** member's filing with a former-parent clause
-- *"sub_0, formerly a subsidiary of sub_97, reported 105.87 USD, filed 29 May
2026"*. The clause is irrelevant; the filing is needed.
"""

from __future__ import annotations

import statistics

from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency import surface as S
from symbolic_ai_generators.solvency.read_surface import (
    decide_reading, read_signature as branch,
    read_signature_accumulating as accumulate)
from symbolic_ai_generators.staleness import filter_stale, stale_by_cancellation

SEEDS = 60


def _score(reader, *, stale, unit=None):
    ok = []
    for s in range(SEEDS):
        case = generate(s)
        want = decide(case, as_of=case.decision_date)[0]
        text = S.render_observation(case, variants=4, stale_clause=stale).text
        if unit:
            text = filter_stale(text, stale_by_cancellation, unit=unit)
        ok.append(decide_reading(reader(text)) == want)
    return statistics.mean(ok)


def test_the_clause_puts_a_second_entity_in_the_sentence():
    """With an unmatched name the reader sees one entity and nothing is packed.
    The regression this guards against is the case quietly becoming easy."""
    text = S.render_observation(generate(0), variants=4,
                                stale_clause=True).text
    line = next(x for x in text.split(". ") if "formerly a subsidiary" in x)
    assert "sub_97" in line


def test_the_branching_reader_loses_the_filing():
    assert _score(branch, stale=False) == 1.0
    assert _score(branch, stale=True) < 0.8


def test_accumulation_recovers_most_of_it_but_not_all():
    """The nearest-money binding is wrong for this shape: the parenthetical sits
    closer to the number than the subject does. Most cases survive anyway
    because the verdict is a threshold test and one lost filing rarely crosses
    it -- which is why the residual is small rather than zero."""
    assert _score(accumulate, stale=True) > 0.85
    assert _score(accumulate, stale=True) < 1.0


def test_the_sentence_gate_is_actively_harmful():
    """It takes a reader that was mostly right and makes it worse -- the exact
    Miramax mechanism, reproduced without leaving the repo."""
    without = _score(accumulate, stale=True)
    with_gate = _score(accumulate, stale=True, unit="sentence")
    assert with_gate < without - 0.2, (without, with_gate)


def test_the_clause_gate_fixes_both_readers():
    assert _score(branch, stale=True, unit="clause") == 1.0
    assert _score(accumulate, stale=True, unit="clause") == 1.0


def test_the_clause_gate_keeps_the_live_half():
    kept = filter_stale(
        "sub_0, formerly a subsidiary of sub_97, reported 105.87 USD, "
        "filed 2026-05-29.", stale_by_cancellation, unit="clause")
    assert "105.87" in kept and "sub_0" in kept
    assert "formerly" not in kept
