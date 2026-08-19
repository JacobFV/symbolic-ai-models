"""Refusing to collapse when the suspect claim is a distractor.

No check downstream of a reader can catch an invented claim -- the grounding
scope result. The remaining response is to decline to collapse: the audit says
offline that flood's ``(2 regions, 0 number)`` signature is shared with prose, so
a reader knows the *kind* is suspect even though it cannot tell which sentence is
the distractor.

Bounded hypothesis, matching the generator: **at most one link is spurious**.
"""

from __future__ import annotations

from dataclasses import replace

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import read_content_roles
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate

HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")
N = 30


def _answers(world) -> set:
    out = {solve(world)[0]}
    for i, c in enumerate(world.claims):
        if c.predicate == "link":
            out.add(solve(replace(world, claims=tuple(
                x for j, x in enumerate(world.claims) if j != i)))[0])
    return out


def _read(case):
    obs = render_observation(case, variants=4, hard_distractors=True)
    return read_content_roles(
        interleave(unsaturate(obs, headings=HEADINGS, shuffle=False)).text)


def test_deciding_implies_correct() -> None:
    """The provable half. If every candidate agrees and the true world is among
    them, the common answer is the true one -- so a decision is never wrong."""
    for seed in range(N):
        case = generate(seed)
        answers = _answers(_read(case))
        if len(answers) == 1:
            assert next(iter(answers)) == solve(case.world)[0], seed


def test_the_truth_is_always_among_the_candidates() -> None:
    """Soundness, which is what makes the half above provable rather than lucky."""
    for seed in range(N):
        case = generate(seed)
        assert solve(case.world)[0] in _answers(_read(case)), seed


def test_it_gives_up_no_coverage_here_which_is_the_fragile_half() -> None:
    """Measured, NOT provable. A collapsing reader could be accidentally right
    while the candidates disagree; on this generator it never is.

    If this fails on a future surface the policy is still sound -- it would just
    be paying coverage for that soundness, which is the normal case. Treat a
    failure as information, not as a regression.
    """
    given_up = 0
    for seed in range(N):
        case = generate(seed)
        world = _read(case)
        want = solve(case.world)[0]
        if solve(world)[0] == want and len(_answers(world)) > 1:
            given_up += 1
    assert given_up == 0, f"{given_up}/{N} correct-but-undecided"


def test_collapsing_is_silently_wrong_where_this_abstains() -> None:
    """The point of the policy: the same answers, but you know which to trust."""
    wrong = sum(solve(_read(generate(s)))[0] != solve(generate(s).world)[0]
                for s in range(N))
    assert wrong > N // 4, ("the collapsing reader should be wrong often here; "
                            f"only {wrong}/{N}")
