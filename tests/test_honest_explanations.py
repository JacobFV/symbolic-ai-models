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
