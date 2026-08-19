"""The alignment has to be exact, or every world-level metric built on it lies.

`symbolic_ai_generators/flood/surface.py` renders a flood case as five aligned
paragraphs. Its whole value is the claim that **every span carries the index of
the claim it realises, and every claim is realised by at least one span** --
without that, entity/relation/claim precision and recall are estimates rather
than measurements, which is the thing the programme is trying to stop doing.
"""

from __future__ import annotations

import pytest

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.surface import render_observation

SEEDS = range(12)


@pytest.fixture(scope="module")
def obs():
    return [(c, render_observation(c)) for c in (generate(s) for s in SEEDS)]


class TestTheAlignmentIsExact:
    def test_every_claim_is_realised_by_at_least_one_span(self, obs):
        for case, o in obs:
            missing = set(range(len(case.world.claims))) - o.covered()
            assert not missing, (
                f"seed {case.seed}: claims {sorted(missing)} appear in the "
                f"world and in no span -- a reader could not recover them from "
                f"this text and would be marked wrong for it")

    def test_span_offsets_index_the_document_they_came_from(self, obs):
        for case, o in obs:
            for s in o.spans:
                assert 0 <= s.start < s.end <= len(o.text)
                assert o.text[s.start:s.end].strip(), "an empty span"

    def test_spans_do_not_overlap(self, obs):
        for case, o in obs:
            ordered = sorted(o.spans, key=lambda s: s.start)
            for a, b in zip(ordered, ordered[1:]):
                assert a.end <= b.start, f"seed {case.seed}: {a} overlaps {b}"

    def test_a_claim_span_names_the_predicate_it_realises(self, obs):
        for case, o in obs:
            for s in o.spans:
                if s.claim is not None:
                    assert s.kind == case.world.claims[s.claim].predicate

    def test_the_numbers_in_a_quantity_span_are_the_claim_s_numbers(self, obs):
        from symbolic_ai_core.world import Quantity
        for case, o in obs:
            for s in o.spans:
                if s.claim is None:
                    continue
                v = case.world.claims[s.claim].roles.get("value")
                if isinstance(v, Quantity):
                    assert f"{v.value:.0f}" in o.text[s.start:s.end], (
                        f"seed {case.seed}: span for claim {s.claim} does not "
                        f"contain its own value {v.value}")


class TestItIsActuallyHard:
    def test_five_paragraphs_in_the_prescribed_shape(self, obs):
        for _, o in obs:
            assert len(o.paragraphs) == 5
            heads = [p.split(".")[0] for p in o.paragraphs]
            assert heads[0].startswith("SITUATION REPORT")
            assert "ROAD NETWORK" in heads[1]
            assert "OVERNIGHT" in heads[2]
            assert "LOADING AND LIMITS" in heads[3]
            assert "TASKING" in heads[4]

    def test_there_are_distractors_and_they_align_to_no_claim(self, obs):
        for _, o in obs:
            assert len(o.distractors()) >= 5
            assert all(s.claim is None for s in o.distractors())

    def test_a_distractor_number_is_not_any_claim_s_number(self, obs):
        """The superseded load limit must not coincide with a real one, or
        'take every number' would be accidentally correct."""
        from symbolic_ai_core.world import Quantity
        for case, o in obs:
            real = {f"{v.value:.0f}" for c in case.world.claims
                    if isinstance(v := c.roles.get("value"), Quantity)}
            for s in o.distractors():
                text = o.text[s.start:s.end]
                if "rated at" in text:
                    nums = {t for t in text.replace(";", " ").split()
                            if t.isdigit()}
                    assert not (nums & real), (
                        f"seed {case.seed}: superseded value collides with a "
                        f"real one in {text!r}")

    def test_one_entity_s_attributes_are_split_across_paragraphs(self, obs):
        """Mass in the roster, capacity in the quantities paragraph. A reader
        that works sentence-locally cannot assemble a vehicle."""
        for case, o in obs:
            def para_of(span):
                return sum(1 for p in o.text[:span.start].split("\n\n")) - 1
            for kind_a, kind_b in (("mass", "capacity"),):
                a = {s.entities[0]: para_of(s) for s in o.spans
                     if s.kind == kind_a}
                b = {s.entities[0]: para_of(s) for s in o.spans
                     if s.kind == kind_b}
                shared = set(a) & set(b)
                assert shared, "no vehicle carries both attributes"
                assert all(a[v] != b[v] for v in shared), (
                    "mass and capacity are in the same paragraph; the surface "
                    "is not exercising distance")

    def test_some_facts_are_stated_through_a_reference(self, obs):
        for _, o in obs:
            refs = {s.reference for s in o.spans if s.claim is not None}
            assert "pronoun" in refs and "definite" in refs


class TestItIsDeterministic:
    def test_the_same_case_renders_identically(self):
        c = generate(5)
        assert render_observation(c).text == render_observation(c).text

    def test_different_cases_render_differently(self):
        assert (render_observation(generate(5)).text
                != render_observation(generate(6)).text)
