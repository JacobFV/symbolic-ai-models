"""The two certificates, and the difference between them.

`certifies_insensitive` reads the roles to build its graph, so it inherits their
errors. `certifies_role_independent` consumes no guessed role: every candidate
assignment must certify and they must agree.
"""

from __future__ import annotations

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.certificate import (
    certifies_insensitive, certifies_role_independent)
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import read_content_roles_checked
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate

HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")


def _text(seed: int) -> str:
    obs = render_observation(generate(seed), variants=4, hard_distractors=True)
    return interleave(unsaturate(obs, headings=HEADINGS, shuffle=False)).text


def test_role_independent_is_sound() -> None:
    """0 wrong over the answers it certifies. The bound is 3/n, not zero."""
    answered = wrong = 0
    for seed in range(200):
        case = generate(seed)
        want = solve(case.world)[0]
        if not want:
            continue
        text = _text(seed)
        if not certifies_role_independent(text, solve):
            continue
        answered += 1
        world, _ = read_content_roles_checked(text)
        wrong += solve(world)[0] != want
    assert answered > 40, answered
    assert wrong == 0, wrong


def test_it_refuses_where_the_collapsed_form_is_misled() -> None:
    """Seed 83: the two wrong-depot candidates certify and the TRUE one does
    not, so requiring all of them refuses a case the collapsed form admits.

    Asserting the gap EXISTS keeps the distinction honest -- if this ever passes
    with both agreeing, the collapsed form has been strengthened and the
    role-independent one is redundant.
    """
    text = _text(83)
    world, _ = read_content_roles_checked(text)
    assert certifies_insensitive(world), "collapsed form should be misled here"
    assert not certifies_role_independent(text, solve)

    case = generate(83)
    assert solve(world)[0] != solve(case.world)[0], "and the answer is wrong"


def test_the_collapsed_form_reads_the_roles() -> None:
    """The property that makes it need a precondition, asserted directly:
    change only the depot and the verdict can change."""
    from dataclasses import replace

    from symbolic_ai_core.world import Claim, EntityRef

    moved = 0
    for seed in range(60):
        case = generate(seed)
        roles = [c for c in case.world.claims
                 if c.predicate in ("depot", "flooded")]
        if len(roles) < 2:
            continue
        keep = tuple(c for c in case.world.claims
                     if c.predicate not in ("depot", "flooded"))
        swapped = []
        for c in roles:
            other = "flooded" if c.predicate == "depot" else "depot"
            swapped.append(Claim(other, {"where": EntityRef(c.roles["where"].id)}))
        a = certifies_insensitive(case.world)
        b = certifies_insensitive(replace(case.world,
                                          claims=keep + tuple(swapped)))
        moved += a != b
    assert moved > 0, "swapping roles never changed the verdict"
