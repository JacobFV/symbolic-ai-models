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


def test_it_discards_only_wrong_answers() -> None:
    """The property that makes the price interpretable.

    On this population the carrying policy answers fewer cases than the
    collapsing reader but gets the SAME number right -- every case it refuses is
    one the collapsing reader would have got wrong. That is why its $/correct
    multiple equals its compute multiple exactly: the numerator does not move.
    """
    collapse_right = decided_right = decided = 0
    for seed in range(N):
        case = generate(seed)
        want = solve(case.world)[0]
        if not want:
            continue
        world = _read(case)
        collapse_right += solve(world)[0] == want
        answers = _answers(world)
        if len(answers) == 1:
            decided += 1
            decided_right += next(iter(answers)) == want
    assert decided_right == collapse_right, (decided_right, collapse_right)
    assert decided < N, "it must refuse something, or there is nothing to price"


def test_early_exit_does_not_change_the_decided_set() -> None:
    """Stopping at the first disagreement is exact, not an approximation."""
    from dataclasses import replace as _replace

    for seed in range(N):
        case = generate(seed)
        world = _read(case)
        full = len(_answers(world)) == 1

        seen = {solve(world)[0]}
        early = True
        for i, c in enumerate(world.claims):
            if c.predicate != "link":
                continue
            seen.add(solve(_replace(world, claims=tuple(
                x for j, x in enumerate(world.claims) if j != i)))[0])
            if len(seen) > 1:
                early = False
                break
        assert early == full, seed


def test_the_certificate_agrees_with_the_enumeration() -> None:
    """Proving insensitivity must match checking it, in both directions.

    Sufficiency is proved: deleting a link is monotone, so a vehicle that cannot
    qualify cannot be made to qualify by removing a road, and a qualifying one
    survives iff its admissible subgraph keeps depot and site connected after any
    single edge removal.

    Necessity is measured -- exact over 95 non-empty cases -- and rests on the
    flow's answer coinciding with the graph condition, which ASP's route cap
    could in principle break. A failure here is information about that gap, not
    a flaky test.
    """
    import sys
    sys.path.insert(0, "scripts")
    from insensitivity_certificate import certifies_insensitive

    for seed in range(N):
        case = generate(seed)
        if not solve(case.world)[0]:
            continue
        world = _read(case)
        decided = len(_answers(world)) == 1
        assert certifies_insensitive(world) == decided, seed


def test_the_certificate_needs_no_flow_solve() -> None:
    """Its whole value is being cheap: claims in, verdict out, no kernel call."""
    import inspect
    import sys
    sys.path.insert(0, "scripts")
    import insensitivity_certificate as ic

    src = inspect.getsource(ic.certifies_insensitive) + \
        inspect.getsource(ic._read_world) + inspect.getsource(ic._connected)
    for forbidden in ("solve(", "get_kernel", "evaluate("):
        assert forbidden not in src, forbidden
