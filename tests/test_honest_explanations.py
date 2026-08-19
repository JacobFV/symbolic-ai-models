"""A correct answer with a fabricated justification.

Inspectability had only been checked on the easy surface. `ungrounded` certifies
consistency with the world **as read**, not truth, so on the honest surface an
explanation can cite a claim that is false and pass every check here.

Measured over 300 seeds: the template renderer never fabricates on a correct
answer, on either surface; the *complete* renderer -- the one built to omit
nothing material -- fabricates on **7.6%** of correct answers and **37.8%** of all
explanations, at **15.5x** the per-citation rate. `ungrounded` flags none of it.
"""

from __future__ import annotations

from dataclasses import replace

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import read_content_roles
from symbolic_ai_generators.flood.render import (render_answer,
                                                 render_complete, ungrounded)
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

SEEDS = 120


def _key(claim):
    roles = []
    for name in sorted(claim.roles):
        r = claim.roles[name]
        roles.append((name, r.id if hasattr(r, "id")
                      else (float(r.value) if hasattr(r, "value") else str(r))))
    return (claim.predicate, tuple(roles))


def _rows(renderer, hard):
    for s in range(SEEDS):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        obs = render_observation(case, variants=4, hard_distractors=hard)
        text = interleave(unsaturate(obs, drop_headings=True,
                                     shuffle=False)).text
        try:
            world = read_content_roles(text)
            got, outputs, _ = solve(world)
        except Exception:
            continue
        shim = replace(case, world=world)
        answer = renderer(shim, got, outputs)
        true_keys = {_key(c) for c in case.world.claims}
        false_cites = 0
        for c in answer.citations:
            if not c.source.startswith("claim:"):
                continue
            ref = c.source.split(":", 1)[1]
            if ref.isdigit() and 0 <= int(ref) < len(world.claims):
                if _key(world.claims[int(ref)]) not in true_keys:
                    false_cites += 1
            elif ref in ("needs", "flooded"):
                where = answer.text[c.start:c.end]
                if (ref, (("where", where),)) not in true_keys:
                    false_cites += 1
        yield got == want, false_cites, bool(ungrounded(answer, shim, outputs))


def test_the_template_renderer_never_lies_on_a_correct_answer():
    """Two citations, the demand and the site, and the reader gets both right
    whatever the distractors do. Its honesty is surface-independent."""
    for hard in (False, True):
        bad = [f for ok, f, _ in _rows(render_answer, hard) if ok and f]
        assert bad == [], (hard, bad)


def test_the_complete_renderer_does():
    """The renderer built to omit nothing material cites the load-bearing set
    computed from the READ world -- which is exactly where a phantom link is."""
    rows = list(_rows(render_complete, True))
    fabricated = [f for ok, f, _ in rows if ok and f]
    assert fabricated, "no correct answer had a false citation"


def test_ungrounded_is_blind_to_all_of_it():
    """The scope note with a measurement on it: it certifies consistency with
    the world as read, so it cannot see a claim the reader invented."""
    for renderer in (render_answer, render_complete):
        flags = [u for _, _, u in _rows(renderer, True)]
        assert not any(flags), renderer.__name__


def test_the_marker_catches_every_fabrication_in_a_small_slice():
    """The renderer cannot be made honest -- nothing here checks a link -- but it
    can say where it is not. Measured over 300 seeds: 88 of 88 false citations
    flagged, in 7.5% of all citations."""
    from symbolic_ai_generators.flood.read_surface import (
        read_content_roles_checked)
    from symbolic_ai_generators.flood.render import uncorroborated

    total = false = flagged = caught = 0
    for s in range(SEEDS):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        obs = render_observation(case, variants=4, hard_distractors=True)
        text = interleave(unsaturate(obs, drop_headings=True,
                                     shuffle=False)).text
        try:
            world, forced = read_content_roles_checked(text)
            got, outputs, _ = solve(world)
        except Exception:
            continue
        answer = render_complete(replace(case, world=world), got, outputs)
        true_keys = {_key(c) for c in case.world.claims}
        marks = set(uncorroborated(answer, world, forced=forced))
        for c in answer.citations:
            if not c.source.startswith("claim:"):
                continue
            ref = c.source.split(":", 1)[1]
            cited = answer.text[c.start:c.end]
            if ref.isdigit() and 0 <= int(ref) < len(world.claims):
                bad = _key(world.claims[int(ref)]) not in true_keys
            elif ref in ("needs", "flooded"):
                bad = (ref, (("where", cited),)) not in true_keys
            else:
                continue
            total += 1
            flagged += cited in marks
            if bad:
                false += 1
                caught += cited in marks
    assert false > 0, "no fabrication to catch"
    assert caught == false, f"{caught}/{false} false citations flagged"
    assert flagged / total < 0.2, flagged / total


def test_a_value_error_silences_rather_than_fabricates():
    """The limit stated on the marker, tested. Overlapping the value registry --
    every capacity also a possible mass -- takes accuracy 0.673 -> 0.189 and
    produces NO mass or capacity falsehood: a mis-slotted value disqualifies a
    vehicle, so nothing is cited about it. Citations fall with it."""
    from symbolic_ai_generators.flood.read_surface import (
        VALUE_REGISTRY, read_content_roles_checked)

    noisy = {"mass": frozenset(VALUE_REGISTRY["mass"]
                               | VALUE_REGISTRY["capacity"]),
             "capacity": VALUE_REGISTRY["capacity"],
             "demand": VALUE_REGISTRY["demand"]}
    cites = {"clean": 0, "noisy": 0}
    value_false = 0
    for s in range(SEEDS):
        case = generate(s)
        if not solve(case.world)[0]:
            continue
        obs = render_observation(case, variants=4, hard_distractors=True)
        text = interleave(unsaturate(obs, drop_headings=True,
                                     shuffle=False)).text
        true_keys = {_key(c) for c in case.world.claims}
        for label, reg in (("clean", None), ("noisy", noisy)):
            try:
                world, _ = read_content_roles_checked(text, registry=reg)
                got, outputs, _ = solve(world)
            except Exception:
                continue
            answer = render_complete(replace(case, world=world), got, outputs)
            for c in answer.citations:
                if not c.source.startswith("claim:"):
                    continue
                ref = c.source.split(":", 1)[1]
                if not ref.isdigit() or not (0 <= int(ref) < len(world.claims)):
                    continue
                cites[label] += 1
                claim = world.claims[int(ref)]
                if (label == "noisy" and claim.predicate in ("mass", "capacity")
                        and _key(claim) not in true_keys):
                    value_false += 1
    assert cites["noisy"] < cites["clean"], cites
    assert value_false == 0, f"{value_false} value fabrications appeared"
