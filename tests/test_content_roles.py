"""The reader that reads content for the residual and nothing else.

`read_content_roles` is the first arm here invariant to both phrasing and
arrangement. Its declared external knowledge is `ROLE_ANCHORS`, so the tests
that matter are the ones that make the knowledge earn its place: emptying it
must damage the reading, and the parts of the reading it does not touch must not
move.
"""

from __future__ import annotations

import pytest

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (ROLE_ANCHORS,
                                                       read_content_roles,
                                                       read_signature_roles)
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate


def _text(seed: int, V: int, interleaved: bool) -> str:
    obs = render_observation(generate(seed), variants=V)
    if not interleaved:
        return unsaturate(obs).text
    return interleave(unsaturate(obs, drop_headings=True, shuffle=False)).text


def _acc(anchors, V, interleaved, n=20) -> float:
    ok = []
    for seed in range(n):
        case = generate(seed)
        want = solve(case.world)[0]
        if not want:
            continue
        try:
            got = solve(read_content_roles(_text(seed, V, interleaved),
                                           anchors=anchors))[0]
        except Exception:
            got = ()
        ok.append(got == want)
    return sum(ok) / len(ok)


@pytest.mark.parametrize("V", [1, 4])
@pytest.mark.parametrize("interleaved", [False, True])
def test_holds_every_cell_of_the_grid(V: int, interleaved: bool) -> None:
    """The claim the arm exists to make: invariant to phrasing AND arrangement."""
    assert _acc(ROLE_ANCHORS, V, interleaved) == 1.0


def test_the_anchors_are_load_bearing() -> None:
    """The control that must fail. If emptying the declared knowledge costs
    nothing, the arm is reading something undeclared."""
    empty = {k: () for k in ROLE_ANCHORS}
    assert _acc(empty, 4, True) < _acc(ROLE_ANCHORS, 4, True) - 0.15


def test_the_flooded_vocabulary_is_the_one_that_matters() -> None:
    """Not all three carry equal weight, and the arm should not pretend so.

    `needs` is redundant with adjacency, which pins it at 1.000 claim recall
    with no content at all.
    """
    without = {k: (() if k == "flooded" else v) for k, v in ROLE_ANCHORS.items()}
    assert _acc(without, 4, True) < 1.0
    no_needs = {k: (() if k == "needs" else v) for k, v in ROLE_ANCHORS.items()}
    assert _acc(no_needs, 4, True) == 1.0


def test_it_beats_the_content_free_arm_where_that_arm_dies() -> None:
    for seed in range(12):
        case = generate(seed)
        want = solve(case.world)[0]
        if not want:
            continue
        text = _text(seed, 4, True)
        assert solve(read_content_roles(text))[0] == want, seed
    # and the content-free arm does not
    died = sum(solve(read_signature_roles(_text(s, 4, True)))[0]
               != solve(generate(s).world)[0]
               for s in range(12) if solve(generate(s).world)[0])
    assert died >= 5, died


def test_an_unresolved_region_is_never_marked_flooded_blindly() -> None:
    """Marking a region impassable CUTS THE NETWORK; leaving it unassigned only
    fails to help. The first version defaulted to flooded and scored 0.000."""
    empty = {k: () for k in ROLE_ANCHORS}
    for seed in range(12):
        case = generate(seed)
        world = read_content_roles(_text(seed, 4, True), anchors=empty)
        got = {c.roles["where"].id for c in world.claims
               if c.predicate == "flooded"}
        lone = {c.roles["where"].id for c in case.world.claims
                if c.predicate in ("depot", "flooded", "needs")}
        assert got <= lone, seed
        assert len(got) < len(lone), seed


def test_only_the_residual_is_read_lexically() -> None:
    """Everything the signature determines must still be content-free.

    Emptying the anchors may cost depot/flooded, and must cost nothing else.
    """
    empty = {k: () for k in ROLE_ANCHORS}
    for seed in range(10):
        case = generate(seed)
        text = _text(seed, 4, True)
        full = read_content_roles(text)
        none = read_content_roles(text, anchors=empty)
        for pred in ("link", "mass", "capacity", "load_limit", "bridge_on"):
            a = {(c.predicate, tuple(sorted(c.entities()))) for c in full.claims
                 if c.predicate == pred}
            b = {(c.predicate, tuple(sorted(c.entities()))) for c in none.claims
                 if c.predicate == pred}
            assert a == b, (seed, pred)
