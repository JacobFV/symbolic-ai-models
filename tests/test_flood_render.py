"""The renderer's paragraph must be checkable, not merely fluent.

`symbolic_ai_generators/flood/render.py` is the last box of
`text -> world IR -> multi-kernel flow -> structured output + text`. Its whole
claim is that an unsupported assertion is detectable **mechanically**, so the
tests that matter are the ones where the checker has to FAIL.
"""

from __future__ import annotations

import pytest

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.render import (Answer, render_answer,
                                                 ungrounded)

pytest.importorskip("clingo")
pytest.importorskip("z3")
SEEDS = range(10)


@pytest.fixture(scope="module")
def rendered():
    out = []
    for s in SEEDS:
        c = generate(s)
        ans, outs, _ = solve(c.world)
        out.append((c, ans, outs, render_answer(c, ans, outs)))
    return out


class TestItIsGrounded:
    def test_nothing_asserted_is_unsupported(self, rendered):
        for c, _, outs, a in rendered:
            assert ungrounded(a, c, outs) == []

    def test_both_polarities_are_rendered_and_explained(self, rendered):
        polarities = {bool(ans) for _, ans, _, _ in rendered}
        assert polarities == {True, False}, "need both answer polarities"
        for c, ans, outs, a in rendered:
            assert ("can make the delivery" in a.text)
            # a refusal has to say WHY, not merely that
            if not ans:
                # a refusal has to give a reason: either a per-vehicle failure
                # or, when nothing is routable at all, the cut in the network
                assert ("binding limit" in a.text or "cannot" in a.text
                        or "No route reaches it" in a.text), a.text

    def test_every_citation_indexes_the_paragraph(self, rendered):
        for _, _, _, a in rendered:
            for cite in a.citations:
                assert 0 <= cite.start < cite.end <= len(a.text)
                assert a.text[cite.start:cite.end].strip()
                assert cite.source


class TestTheCheckerCanFail:
    """A groundedness metric that cannot detect an invented fact measures
    nothing. These are the tests the design exists for."""

    def test_an_invented_quantity_is_caught(self, rendered):
        c, _, outs, a = rendered[0]
        forged = Answer(structured=a.structured,
                        text=a.text + " The limit there is 9999 kg.",
                        citations=a.citations)
        bad = ungrounded(forged, c, outs)
        assert any("9999" in b for b in bad)

    def test_an_invented_entity_is_caught(self, rendered):
        c, _, outs, a = rendered[0]
        forged = Answer(structured=a.structured,
                        text=a.text + " truck_77 also qualifies.",
                        citations=a.citations)
        assert any("truck_77" in b for b in ungrounded(forged, c, outs))

    def test_a_false_route_ORDERING_is_caught(self, rendered):
        """The bug that shipped in the first version: every region real, the
        walk invented. Token grounding passed it; adjacency does not."""
        def regions_of(outs):
            return sorted({r for routes in outs["load_report"].value[
                "per_vehicle"].values() for x in routes
                for e in (x.get("edges") or []) for r in e})

        # a case whose routes touch enough regions to build a false walk from
        # real ones; a two-region route cannot express an invented ordering
        pick = next(((c, outs, a) for c, _, outs, a in rendered
                     if len(regions_of(outs)) >= 3), None)
        assert pick is not None, "no case with a multi-hop route to forge"
        c, outs, a = pick
        regions = regions_of(outs)
        # a chain of real regions that is not a real walk
        fake = " to ".join([regions[0], regions[-1], regions[1]])
        forged = Answer(structured=a.structured,
                        text=a.text + f" It also runs {fake}.",
                        citations=a.citations)
        bad = ungrounded(forged, c, outs)
        assert any("route hop" in b for b in bad), (
            "a false ordering of real regions was not caught")


class TestTheParagraphCannotContradictTheDecision:
    """Token grounding and adjacency both pass a sentence that asserts the
    OPPOSITE of the structured answer using only real tokens on a real route.
    The separation between reasoning and generation is worth nothing if the
    paragraph can disagree with the decision and nothing notices."""

    @staticmethod
    def _case_with_a_refused_vehicle(rendered):
        for c, ans, outs, a in rendered:
            refused = [v for v in outs["load_report"].value["per_vehicle"]
                       if v not in ans]
            if refused and ans:
                return c, ans, outs, a, refused[0]
        return None

    def test_claiming_a_refused_vehicle_runs_is_caught(self, rendered):
        pick = self._case_with_a_refused_vehicle(rendered)
        assert pick is not None, "need a case with both an able and a refused vehicle"
        c, ans, outs, a, refused = pick
        # a real route, real limit, real vehicle -- only the POLARITY is false
        real_path = None
        for r in outs["load_report"].value["per_vehicle"][refused]:
            edges = r.get("edges") or []
            if edges:
                real_path = " to ".join(
                    dict.fromkeys([edges[0][0]] + [e[1] for e in edges]))
                break
        forged = Answer(
            structured=ans,
            text=a.text + f" {refused} runs and clears it.",
            citations=a.citations)
        bad = ungrounded(forged, c, outs)
        assert any(refused in b and "structured answer" in b for b in bad), bad

    def test_denying_an_able_vehicle_is_caught(self, rendered):
        pick = self._case_with_a_refused_vehicle(rendered)
        c, ans, outs, a, _ = pick
        able = ans[0]
        forged = Answer(structured=ans,
                        text=a.text + f" {able} cannot after all.",
                        citations=a.citations)
        bad = ungrounded(forged, c, outs)
        assert any(able in b and "structured answer" in b for b in bad), bad

    def test_the_honest_paragraph_is_not_flagged(self, rendered):
        for c, _, outs, a in rendered:
            assert not [b for b in ungrounded(a, c, outs)
                        if "structured answer" in b]


class TestGenerationCannotContaminateReasoning:
    def test_the_structured_answer_is_exactly_what_the_flow_returned(self,
                                                                     rendered):
        for _, ans, _, a in rendered:
            assert a.structured == ans

    def test_a_wordless_renderer_changes_no_structured_answer(self, rendered):
        for c, ans, outs, _ in rendered:
            empty = Answer(structured=ans, text="", citations=())
            assert empty.structured == ans
            assert ungrounded(empty, c, outs) == []
