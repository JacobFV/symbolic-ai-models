"""The shared surface scrambles, on a domain other than the one they were
written for.

`symbolic_ai_generators.scramble` works by duck typing: each domain declares its
own ``Observation``/``Span``, structurally identical and separately defined. If
the rebuild picked the wrong class or dropped a field, every cross-domain number
measured with it would be scored against corrupted ground truth.
"""

from __future__ import annotations

from symbolic_ai_generators.scheduling import generate
from symbolic_ai_generators.scheduling.surface import (Observation,
                                                       render_observation)
from symbolic_ai_generators.scramble import interleave, unsaturate

HEADINGS = ("WORKS ORDER.",)


def _pair(seed: int):
    obs = render_observation(generate(seed), variants=4)
    return obs, interleave(unsaturate(obs, headings=HEADINGS, shuffle=False))


def test_rebuilds_the_domains_own_class() -> None:
    """Not flood's. The transform must not smuggle another domain's type in."""
    obs, out = _pair(0)
    assert isinstance(out, Observation)
    assert type(out) is type(obs)
    assert type(out.spans[0]) is type(obs.spans[0])


def test_every_claim_span_still_quotes_its_own_text() -> None:
    for seed in range(12):
        obs, out = _pair(seed)
        old = {s.claim: obs.text[s.start:s.end]
               for s in obs.spans if s.claim is not None}
        new = {s.claim: out.text[s.start:s.end]
               for s in out.spans if s.claim is not None}
        assert old == new, seed


def test_no_claim_is_lost() -> None:
    for seed in range(12):
        obs, out = _pair(seed)
        old = {s.claim for s in obs.spans if s.claim is not None}
        new = {s.claim for s in out.spans if s.claim is not None}
        assert old == new, seed


def test_headings_go_and_grouping_goes() -> None:
    for seed in range(8):
        _, out = _pair(seed)
        assert "WORKS ORDER." not in out.text, seed
        assert len(out.paragraphs) == 1, seed


def test_a_domain_without_a_reference_field_still_works() -> None:
    """Scheduling's Span has no ``reference``; the atom rule must not require
    one. It has no pronouns to strand, which is why it is safe here."""
    obs, _ = _pair(1)
    assert not hasattr(obs.spans[0], "reference")
    assert interleave(obs).text  # would raise if the getattr default were wrong


def test_it_is_deterministic() -> None:
    obs = render_observation(generate(3), variants=4)
    assert interleave(obs).text == interleave(obs).text
    assert unsaturate(obs, headings=HEADINGS).text == \
        unsaturate(obs, headings=HEADINGS).text
