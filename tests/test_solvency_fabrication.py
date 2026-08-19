"""Values that feed the computation fabricate the headline number.

Flood's values **gate**: a mis-slotted mass disqualifies a vehicle, so nothing is
cited about it and the explanation stays honest. Solvency's **feed**: revenue
figures are summed, and the renderer states the consolidated total as its central
sentence.

Measured over 200 seeds with an unofficial figure admitted: the verdict is wrong
on 0.485 of cases and the **stated total on 1.000**, at a mean relative error of
0.398. So more than half of all cases carry the **right verdict justified by a
false number** -- and `ungrounded` flags none of it, because the spurious figure
*is* in the world as read.
"""

from __future__ import annotations

import statistics
from types import SimpleNamespace

from symbolic_ai_core.world import WorldSnapshot
from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency import surface as S
from symbolic_ai_generators.solvency.read_surface import (
    decide_reading, read_signature_accumulating)
from symbolic_ai_generators.solvency.render import render_answer, ungrounded

SEEDS = 80


def _truth_total(case) -> float:
    usable: dict[str, tuple[float, str]] = {}
    for e, v, k in case.filings:
        if e in case.members and k <= case.decision_date:
            if e not in usable or k > usable[e][1]:
                usable[e] = (v, k)
    return round(sum(v for v, _ in usable.values()), 2)


def _rows(hard):
    for s in range(SEEDS):
        case = generate(s)
        want = decide(case, as_of=case.decision_date)[0]
        text = S.render_observation(case, variants=4, hard_distractors=hard,
                                    cue="cued").text
        reading = read_signature_accumulating(text)
        got = decide_reading(reading)
        shim = SimpleNamespace(members=sorted(reading.members),
                               filings=list(reading.filings),
                               threshold=reading.threshold,
                               decision_date=reading.decision_date,
                               world=WorldSnapshot(entities={}, claims=()))
        answer = render_answer(shim, bool(got))
        stated = next((float(answer.text[c.start:c.end])
                       for c in answer.citations
                       if c.source == "derived:sum_of_usable_filings"), None)
        yield (got == want, stated, _truth_total(case),
               bool(ungrounded(answer, shim)))


def test_the_clean_surface_states_the_truth():
    for ok, stated, truth, _ in _rows(False):
        assert ok and stated is not None and abs(stated - truth) < 0.005


def test_the_explanation_is_wrong_more_often_than_the_answer():
    rows = list(_rows("filing"))
    verdict_wrong = statistics.mean(not ok for ok, _, _, _ in rows)
    total_wrong = statistics.mean(abs(s - t) > 0.005
                                  for _, s, t, _ in rows if s is not None)
    assert total_wrong > verdict_wrong, (total_wrong, verdict_wrong)
    assert total_wrong > 0.9


def test_a_right_verdict_with_a_false_number_is_the_common_case():
    rows = [(ok, s, t) for ok, s, t, _ in _rows("filing") if s is not None]
    both = [1 for ok, s, t in rows if ok and abs(s - t) > 0.005]
    assert len(both) / len(rows) > 0.4, len(both) / len(rows)


def test_ungrounded_cannot_see_it():
    """The spurious figure IS in the world as read, so the number it states is
    'supported'. The same scope error, in its worst form."""
    assert not any(u for _, _, _, u in _rows("filing"))
