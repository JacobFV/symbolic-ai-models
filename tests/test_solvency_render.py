"""The grounding contract, on a structurally opposite task.

`tests/test_flood_render.py` established it: the structured answer is canonical,
the paragraph is downstream, and the tests that matter are the ones where the
checker has to FAIL. Solvency's verdict is one boolean and its explanation is
bitemporal, so the contract transfers but the mechanism does not -- which is the
thing this file is really testing.
"""

from __future__ import annotations

import pytest

from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency.render import (Answer, render_answer,
                                                    ungrounded)

SEEDS = range(30)


@pytest.fixture(scope="module")
def rendered():
    out = []
    for s in SEEDS:
        c = generate(s)
        v = decide(c, as_of=c.decision_date)[0]
        out.append((c, v, render_answer(c, v)))
    return out


class TestItIsGrounded:
    def test_nothing_asserted_is_unsupported(self, rendered):
        for c, _, a in rendered:
            assert ungrounded(a, c) == [], a.text

    def test_both_verdicts_occur_and_each_states_its_total(self, rendered):
        assert {v for _, v, _ in rendered} == {True, False}
        for _, _, a in rendered:
            assert "consolidated revenue was" in a.text
            assert "against a requirement of" in a.text

    def test_the_explanation_is_bitemporal_where_a_filing_is_late(self, rendered):
        """A covenant fails because a figure was not KNOWABLE, not because it
        was small. Where a member filed only after the determination, the
        paragraph must say so and cite the date."""
        found = 0
        for c, _, a in rendered:
            late = [m for m in c.members
                    if all(k > c.decision_date
                           for e, _, k in c.filings if e == m)
                    and any(e == m for e, _, _ in c.filings)]
            if late:
                found += 1
                assert "not yet knowable" in a.text
                assert "after the determination" in a.text
                for m in late:
                    assert m in a.text
        assert found, "no case with a filing after the determination"


class TestTheCheckerCanFail:
    def test_a_verdict_that_disagrees_with_the_decision_is_caught(self, rendered):
        for c, v, a in rendered:
            flipped = a.text.replace(
                "covenant was not met", "covenant was met") if not v else \
                a.text.replace("covenant was met", "covenant was not met")
            forged = Answer(structured=v, text=flipped, citations=a.citations)
            bad = ungrounded(forged, c)
            assert any("structured verdict" in b for b in bad), (v, flipped[:80])

    def test_an_invented_date_is_caught(self, rendered):
        c, v, a = rendered[0]
        forged = Answer(structured=v,
                        text=a.text + " A further return is dated 1999-01-01.",
                        citations=a.citations)
        assert any("1999-01-01" in b for b in ungrounded(forged, c))

    def test_an_invented_entity_is_caught(self, rendered):
        c, v, a = rendered[0]
        forged = Answer(structured=v, text=a.text + " sub_77 also filed.",
                        citations=a.citations)
        assert any("sub_77" in b for b in ungrounded(forged, c))

    def test_an_invented_figure_is_caught(self, rendered):
        c, v, a = rendered[0]
        forged = Answer(structured=v,
                        text=a.text + " It also booked 99999.99 USD.",
                        citations=a.citations)
        assert any("99999.99" in b for b in ungrounded(forged, c))


class TestGenerationCannotContaminateReasoning:
    def test_the_verdict_is_exactly_what_the_task_decided(self, rendered):
        for c, v, a in rendered:
            assert a.structured == v == decide(c, as_of=c.decision_date)[0]
