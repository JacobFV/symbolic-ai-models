"""What "grounded" does and does not certify.

`ungrounded` is quoted across this repo as the property that makes generating
prose safe. It is -- for the renderer. It says nothing about the reader, and the
distinction is easy to lose because "grounded 1.000" reads like a truth claim.

These tests pin the scope in both directions, so a later session cannot quietly
assume the stronger reading.
"""

from __future__ import annotations

import re

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import read_content_roles
from symbolic_ai_generators.flood.render import render_answer, ungrounded
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate

HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")
_HOPS = re.compile(r"((?:region_\d+)(?: to region_\d+)+)")


def _honest_text(case) -> str:
    obs = render_observation(case, variants=4, hard_distractors=True)
    return interleave(unsaturate(obs, headings=HEADINGS, shuffle=False)).text


def test_grounding_passes_a_paragraph_that_walks_a_road_that_does_not_exist():
    """The scope, demonstrated rather than asserted.

    On the hard-distractor surface the reader invents a link. The flow routes
    over it, the renderer prints the route, and ``ungrounded`` accepts it --
    because its admissible edges come from the routes the flow computed from the
    world it was given, which contains the invented link.
    """
    found = False
    for seed in range(60):
        case = generate(seed)
        want = solve(case.world)[0]
        world = read_content_roles(_honest_text(case))
        answer, outs, _ = solve(world)
        if answer == want:
            continue
        para = render_answer(case, answer, outs)
        if ungrounded(para, case, outs):
            continue                      # caught for some other reason
        true_links = {frozenset(c.entities()) for c in case.world.claims
                      if c.predicate == "link"}
        for m in _HOPS.finditer(para.text):
            hops = m.group(1).split(" to ")
            if any(frozenset((a, b)) not in true_links
                   for a, b in zip(hops, hops[1:])):
                found = True
                break
        if found:
            break
    assert found, ("no grounded paragraph walked a non-existent road; if the "
                   "reader or the check has been strengthened, this test should "
                   "be replaced rather than deleted")


def test_grounding_still_catches_what_it_is_for() -> None:
    """The other half. It must reject a paragraph that contradicts the
    structured answer, or the scope note above would be an excuse."""
    case = generate(0)
    answer, outs, _ = solve(case.world)
    para = render_answer(case, answer, outs)
    assert not ungrounded(para, case, outs)

    from dataclasses import replace
    if answer:
        broken = replace(para, text=para.text.replace(
            f"{answer[0]} runs", f"{answer[0]} cannot", 1))
        assert ungrounded(broken, case, outs), \
            "a paragraph contradicting the structured answer must be rejected"


def test_the_oracle_world_is_where_grounded_means_true() -> None:
    """With the oracle's world there is no reader to invent anything, so the
    internal-consistency guarantee coincides with truth."""
    for seed in range(12):
        case = generate(seed)
        answer, outs, _ = solve(case.world)
        para = render_answer(case, answer, outs)
        assert not ungrounded(para, case, outs), seed
        true_links = {frozenset(c.entities()) for c in case.world.claims
                      if c.predicate == "link"}
        for m in _HOPS.finditer(para.text):
            hops = m.group(1).split(" to ")
            for a, b in zip(hops, hops[1:]):
                assert frozenset((a, b)) in true_links, (seed, a, b)
