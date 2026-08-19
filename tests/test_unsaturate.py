"""The unsaturated surface must lose the giveaways and nothing else.

If this transform corrupts the alignment, every reader measured on it is being
scored against wrong ground truth -- the failure mode that has already cost this
repo a withdrawn finding. So the invariants are checked hard.
"""

from __future__ import annotations

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.flood.unsaturate import HEADINGS, unsaturate


def _pair(seed: int, **kw):
    obs = render_observation(generate(seed))
    return obs, unsaturate(obs, **kw)


def test_every_claim_span_still_quotes_its_own_text() -> None:
    """The invariant that makes the alignment trustworthy."""
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
        assert obs.covered() == out.covered(), seed


def test_headings_are_gone() -> None:
    for seed in range(12):
        _, out = _pair(seed)
        for h in HEADINGS:
            assert h not in out.text, (seed, h)


def test_order_actually_changes_for_some_seed() -> None:
    """A shuffle that never shuffles would make the whole arm meaningless."""
    moved = 0
    for seed in range(12):
        obs, out = _pair(seed)
        stripped = [p[len(h):].lstrip() if p.startswith(h) else p
                    for p in obs.paragraphs for h in HEADINGS if p.startswith(h)]
        if stripped and list(out.paragraphs) != stripped:
            moved += 1
    assert moved >= 8, moved


def test_paragraph_multiset_is_preserved() -> None:
    """Shuffling must reorder paragraphs, never edit or drop them."""
    for seed in range(12):
        obs, out = _pair(seed)
        want = sorted(p[_cut(p):] for p in obs.paragraphs)
        assert sorted(out.paragraphs) == want, seed


def _cut(para: str) -> int:
    for h in HEADINGS:
        if para.startswith(h):
            c = len(h)
            while c < len(para) and para[c] == " ":
                c += 1
            return c
    return 0


def test_knobs_are_independent() -> None:
    """Headings and order are priced separately, so they must be separable."""
    obs = render_observation(generate(3))
    only_headings = unsaturate(obs, drop_headings=True, shuffle=False)
    only_order = unsaturate(obs, drop_headings=False, shuffle=True)
    assert "ROAD NETWORK." not in only_headings.text
    assert "ROAD NETWORK." in only_order.text
    assert len(only_headings.paragraphs) == len(obs.paragraphs)


def test_distractors_survive() -> None:
    """Removing headings must not quietly remove the distractors with them."""
    for seed in range(8):
        obs, out = _pair(seed)
        # every distractor except the five heading spans themselves
        assert len(out.distractors()) >= len(obs.distractors()) - len(HEADINGS)
        assert len(out.distractors()) > 0


def test_it_is_deterministic() -> None:
    obs = render_observation(generate(5))
    assert unsaturate(obs).text == unsaturate(obs).text
