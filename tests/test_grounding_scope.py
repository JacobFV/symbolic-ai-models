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


def test_grounding_does_not_measure_sufficiency() -> None:
    """The shipped renderer cites 2 of 28.5 claims and is grounded on all of
    them. Grounding checks that nothing false is asserted; it cannot check that
    enough was said.

    Asserting the gap EXISTS is the point -- if a future renderer becomes
    decision-complete this test should be updated, not deleted, because the
    scope claim about `ungrounded` survives the renderer improving.
    """
    from symbolic_ai_generators.flood.render import incomplete

    grounded = complete = n = 0
    for seed in range(30):
        case = generate(seed)
        answer, outs, _ = solve(case.world)
        if not answer:
            continue
        n += 1
        para = render_answer(case, answer, outs)
        grounded += not ungrounded(para, case, outs)
        complete += not incomplete(para, case)
    assert n > 10, n
    assert grounded == n, "the renderer should be fully grounded"
    assert complete == 0, "and it should be decision-complete on none of them"


def test_completeness_is_recoverable_by_citing_everything() -> None:
    """The check must be satisfiable, or it is measuring nothing."""
    from dataclasses import replace

    from symbolic_ai_generators.flood.render import Citation, incomplete

    case = generate(0)
    answer, outs, _ = solve(case.world)
    para = render_answer(case, answer, outs)
    full = replace(para, citations=tuple(
        Citation(0, 0, f"claim:{i}") for i in range(len(case.world.claims))))
    assert incomplete(full, case) == []


def test_the_complete_renderer_omits_nothing_load_bearing() -> None:
    """The achievable objective, met.

    The template cites 9% of the load-bearing set; this cites all of it, stays
    grounded, and costs about 37% more words.
    """
    from symbolic_ai_generators.flood.render import (omits_load_bearing,
                                                     render_complete)

    n = 0
    for seed in range(25):
        case = generate(seed)
        answer, outs, _ = solve(case.world)
        if not answer:
            continue
        n += 1
        para = render_complete(case, answer, outs)
        assert not ungrounded(para, case, outs), seed
        assert not omits_load_bearing(para, case), seed
    assert n > 10, n


def test_the_template_does_not_meet_it() -> None:
    """Asserting the gap exists, so the check cannot quietly become trivial."""
    from symbolic_ai_generators.flood.render import omits_load_bearing

    missed = 0
    for seed in range(25):
        case = generate(seed)
        answer, outs, _ = solve(case.world)
        if not answer:
            continue
        missed += bool(omits_load_bearing(render_answer(case, answer, outs),
                                          case))
    assert missed > 10, missed


def test_completeness_is_bought_with_length_not_magic() -> None:
    """A complete explanation is longer. If it were not, the check would be
    measuring nothing."""
    from symbolic_ai_generators.flood.render import render_complete

    short = long = n = 0
    for seed in range(15):
        case = generate(seed)
        answer, outs, _ = solve(case.world)
        if not answer:
            continue
        n += 1
        short += len(render_answer(case, answer, outs).text.split())
        long += len(render_complete(case, answer, outs).text.split())
    assert long > short, (long, short)
    assert long < short * 3, "a complete explanation should not be a recitation"


def test_omits_load_bearing_is_a_lower_bound() -> None:
    """It tests SINGLE-claim deletion, so a jointly-critical pair is invisible.

    flood has them in 5 of 14 non-empty cases -- most often two parallel links,
    where deleting either leaves the other carrying the traffic. They are
    CONCENTRATED, not spread: most cases have none and the affected ones have
    up to ten, which is why a six-seed scan finds nothing. Asserting they EXIST
    keeps the check's name honest: it reports what it computes, and what it
    computes is a bound.
    """
    import itertools
    from dataclasses import replace

    found = 0
    for seed in range(24):
        case = generate(seed)
        base = solve(case.world)[0]
        if not base:
            continue
        claims = case.world.claims
        single = set()
        for i in range(len(claims)):
            t = replace(case.world, claims=tuple(
                c for j, c in enumerate(claims) if j != i))
            if solve(t)[0] != base:
                single.add(i)
        inert = [i for i in range(len(claims)) if i not in single]
        for a, b in itertools.combinations(inert, 2):
            t = replace(case.world, claims=tuple(
                c for j, c in enumerate(claims) if j not in (a, b)))
            if solve(t)[0] != base:
                found += 1
                break
        if found:
            break
    assert found, ("no jointly-critical pair found; if single-claim "
                   "sensitivity now captures everything, this test should be "
                   "replaced rather than deleted")
