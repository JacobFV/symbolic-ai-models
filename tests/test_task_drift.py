"""Task drift: a claim kind the reader has no branch for.

Every other check in this repo inspects the READ WORLD. A kind that never enters
the world is invisible to all of them. The text still contains the sentence, and
``unconsumed`` is what notices.
"""

from __future__ import annotations

from symbolic_ai_generators.audit import unconsumed
from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.read_surface import read_content_roles
from symbolic_ai_generators.flood.surface import render_observation

RESTRICTION = "\n\nWEIGHT RESTRICTION. {r} admits vehicles up to 2510 kg only."


def _texts(seed: int):
    case = generate(seed)
    obs = render_observation(case, variants=4)
    region = sorted({e for c in case.world.claims if c.predicate == "link"
                     for e in c.entities()})[0]
    return case, obs.text, obs.text + RESTRICTION.format(r=region)


def test_a_kind_with_no_branch_is_unconsumed() -> None:
    """The signal is an INCREASE over the document's own baseline: clean text
    already contains distractors that consume to nothing."""
    rose = 0
    for seed in range(8):
        _, clean, drifted = _texts(seed)
        if unconsumed(drifted, read_content_roles) > \
                unconsumed(clean, read_content_roles):
            rose += 1
    assert rose >= 6, rose


def test_consumption_is_not_familiarity() -> None:
    """The restricted region is already known from the link claims, so an
    entity-familiarity check sees nothing wrong. That version caught 0 of 22."""
    case, _, drifted = _texts(0)
    world = read_content_roles(drifted)
    known = {e for c in world.claims for e in c.entities()}
    region = sorted({e for c in case.world.claims if c.predicate == "link"
                     for e in c.entities()})[0]
    assert region in known, "the entity is familiar even though the claim is not"


def test_it_is_cheaper_than_solving() -> None:
    import time

    from symbolic_ai_generators.flood.flow import solve

    _, clean, _ = _texts(0)
    case = generate(0)
    t0 = time.perf_counter()
    unconsumed(clean, read_content_roles)
    check = time.perf_counter() - t0
    t0 = time.perf_counter()
    solve(case.world)
    answer = time.perf_counter() - t0
    assert check < answer * 3, (check, answer)
