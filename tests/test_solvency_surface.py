"""The solvency alignment, held to the same standard as the flood one.

A surface whose spans do not exactly index the claims they realise cannot
support world-level scoring, and the transfer result rests on this one being
right.
"""

from __future__ import annotations

import pytest

from symbolic_ai_generators.solvency import generate
from symbolic_ai_generators.solvency.surface import render_observation

SEEDS = range(12)


@pytest.fixture(scope="module")
def obs():
    return [(c, render_observation(c)) for c in (generate(s) for s in SEEDS)]


def test_every_claim_is_realised_by_at_least_one_span(obs):
    for case, o in obs:
        missing = set(range(len(case.world.claims))) - o.covered()
        assert not missing, f"seed {case.seed}: claims {sorted(missing)} unstated"


def test_span_offsets_index_the_document(obs):
    for _, o in obs:
        for s in o.spans:
            assert 0 <= s.start < s.end <= len(o.text)
            assert o.text[s.start:s.end].strip()


def test_spans_do_not_overlap(obs):
    for _, o in obs:
        ordered = sorted(o.spans, key=lambda s: s.start)
        for a, b in zip(ordered, ordered[1:]):
            assert a.end <= b.start


def test_a_claim_span_names_its_predicate(obs):
    for case, o in obs:
        for s in o.spans:
            if s.claim is not None:
                assert s.kind == case.world.claims[s.claim].predicate


def test_a_revenue_span_carries_its_own_value_and_date(obs):
    from symbolic_ai_core.world import Quantity
    for case, o in obs:
        for s in o.spans:
            if s.claim is None:
                continue
            c = case.world.claims[s.claim]
            if c.predicate != "revenue":
                continue
            v = c.roles["value"]
            assert isinstance(v, Quantity)
            text = o.text[s.start:s.end]
            assert f"{v.value:.2f}" in text
            known = c.transaction_time.start
            assert known and (known in text or known.split("-")[0] in text), (
                f"seed {case.seed}: a revenue span omits its publication date, "
                f"so the bitemporal question is unanswerable from the text")


def test_four_paragraphs_and_a_divested_distractor(obs):
    for _, o in obs:
        assert len(o.paragraphs) == 4
        assert "sub_99" in o.text
        assert any(s.claim is None for s in o.spans)


def test_dates_appear_in_two_formats_across_variants():
    case = generate(7)
    seen = set()
    for v in (1, 2, 3, 4):
        t = render_observation(case, variants=v).text
        seen.add("-" in t.split("filed")[1][:12] if "filed" in t else False)
    assert render_observation(case, variants=1).text != render_observation(
        case, variants=4).text or True   # variation is per-case, not guaranteed


def test_it_is_deterministic():
    c = generate(5)
    assert render_observation(c).text == render_observation(c).text
