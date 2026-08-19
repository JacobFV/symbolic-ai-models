"""Surface, reader and renderer for the third domain, held to the same bar.

The point of this file is not that scheduling works. It is that the same three
mechanisms -- exact span->claim alignment, type-signature reading, and a grounded
paragraph whose checker can FAIL -- carry to a domain with an NP-hard kernel and
a boolean answer, and that the boolean contradiction check is now *shared code*
with solvency rather than a repeated idea.
"""

from __future__ import annotations

import re

import pytest

from symbolic_ai_core.world import Quantity
from symbolic_ai_generators.scheduling import generate
from symbolic_ai_generators.scheduling.read_surface import read_signature
from symbolic_ai_generators.scheduling.render import (Answer, render_answer,
                                                      ungrounded)
from symbolic_ai_generators.scheduling.surface import render_observation

SEEDS = range(12)


def _key(c):
    parts = [c.predicate]
    for r, v in sorted(c.roles.items()):
        parts.append((r, round(float(v.value), 6) if isinstance(v, Quantity)
                      else (v.id if hasattr(v, "id") else str(v))))
    return tuple(parts)


@pytest.fixture(scope="module")
def cases():
    return [generate(s, slack=0.30) for s in SEEDS]


class TestTheAlignmentIsExact:
    def test_every_claim_is_realised(self, cases):
        for c in cases:
            o = render_observation(c)
            assert set(range(len(c.world.claims))) <= o.covered()

    def test_spans_index_the_document_and_do_not_overlap(self, cases):
        for c in cases:
            o = render_observation(c)
            ordered = sorted(o.spans, key=lambda s: s.start)
            for s in ordered:
                assert 0 <= s.start < s.end <= len(o.text)
            for a, b in zip(ordered, ordered[1:]):
                assert a.end <= b.start

    def test_a_jobs_duration_and_its_requirement_are_in_different_paragraphs(
            self, cases):
        """Distance, as in flood: nothing about one job is recoverable from one
        sentence."""
        for c in cases:
            o = render_observation(c)
            para = {}
            for s in o.spans:
                if s.kind in ("duration", "needs_capability") and s.entities:
                    idx = o.text[:s.start].count("\n\n")
                    para.setdefault(s.kind, {})[s.entities[0]] = idx
            shared = set(para.get("duration", {})) & set(
                para.get("needs_capability", {}))
            assert shared
            assert all(para["duration"][j] != para["needs_capability"][j]
                       for j in shared)


class TestTheReaderRecoversTheWorld:
    @pytest.mark.parametrize("variants", [1, 2, 3, 4])
    def test_exact_recovery_at_every_phrasing_setting(self, cases, variants):
        for c in cases:
            text = render_observation(c, variants=variants).text
            got = {_key(x) for x in read_signature(text).claims}
            gold = {_key(x) for x in c.world.claims}
            assert got == gold, (c.seed, variants, sorted(gold - got)[:2])

    def test_the_distractors_are_not_read_as_claims(self, cases):
        for c in cases:
            text = render_observation(c, variants=4).text
            assert "machine_90" in text and "job_90" in text
            ids = {e for x in read_signature(text).claims for e in x.entities()}
            assert "machine_90" not in ids and "job_90" not in ids


class TestTheParagraphIsGrounded:
    def test_nothing_asserted_is_unsupported(self, cases):
        for c in cases:
            assert ungrounded(render_answer(c, c.feasible), c) == []

    def test_an_infeasible_order_says_which_constraint_failed(self, cases):
        seen = 0
        for c in cases:
            if c.feasible:
                continue
            seen += 1
            text = render_answer(c, False).text
            assert ("No machine is set up for" in text
                    or "the constraint is time" in text), text
        assert seen, "no infeasible case in the fixture"

    def test_a_verdict_that_disagrees_is_caught(self, cases):
        for c in cases:
            a = render_answer(c, c.feasible)
            flipped = render_answer(c, not c.feasible).text
            forged = Answer(structured=c.feasible, text=flipped)
            assert any("structured verdict" in b
                       for b in ungrounded(forged, c))

    def test_an_invented_entity_or_capability_is_caught(self, cases):
        c = cases[0]
        a = render_answer(c, c.feasible)
        assert any("machine_77" in b for b in ungrounded(
            Answer(structured=c.feasible,
                   text=a.text + " machine_77 could take it."), c))


class TestTheBooleanCheckIsSharedWithSolvency:
    def test_it_is_literally_the_same_function(self):
        from symbolic_ai_generators.grounding import boolean_contradiction
        from symbolic_ai_generators.scheduling import render as sched
        from symbolic_ai_generators.solvency import render as solv
        assert sched.boolean_contradiction is boolean_contradiction
        assert solv.boolean_contradiction is boolean_contradiction

    def test_only_the_verdict_wording_differs(self):
        from symbolic_ai_generators.grounding import boolean_contradiction
        assert boolean_contradiction("the covenant was met", False,
                                     yes="covenant was met",
                                     no="covenant was not met")
        assert boolean_contradiction("Every job can be assigned.", False,
                                     yes="Every job can be assigned",
                                     no="cannot all be assigned")
        assert not boolean_contradiction("Every job can be assigned.", True,
                                         yes="Every job can be assigned",
                                         no="cannot all be assigned")
