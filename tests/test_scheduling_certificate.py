"""Insensitivity on the channel with no arity and no second source.

`has_capability` is multi-valued, so `evidence_conflict` fires 0.000 on it, and
it is the worst channel measured on 2026-08-19 -- one admitted sentence costs
0.210 accuracy with every failure in the unsound direction. The conclusion drawn
that morning, that a multi-valued channel leaves only fixing the reader, was too
strong: insensitivity needs no second source and no arity.

Three things are pinned:

- the monotone half is free and covers every infeasible reading;
- soundness holds where the hypothesis does -- 0 wrong among the certified;
- it is **not** a detector. Coverage among *feasible* readings is 0.056 on the
  clean surface, because at this slack almost every capability is load-bearing.
"""

from __future__ import annotations

import sys
from pathlib import Path

from symbolic_ai_generators.scheduling import generate
from symbolic_ai_generators.scheduling.certificate import (
    certifies_capability_insensitive)
from symbolic_ai_generators.scheduling.read_surface import read_signature
from symbolic_ai_generators.scheduling.surface import render_observation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from hard_regime_milestone import solve_world  # noqa: E402

SEEDS = 60


def _rows(hard):
    for s in range(SEEDS):
        case = generate(s)
        world = read_signature(render_observation(
            case, variants=4, hard_distractors=hard).text)
        got = solve_world(world)[0]
        cert, spent = certifies_capability_insensitive(world, solve_world)
        yield case.feasible, got, cert, spent


def test_an_infeasible_reading_is_certified_for_free():
    """Deleting a capability can only make an instance more infeasible."""
    for _, got, cert, spent in _rows("machine"):
        if got is False:
            assert cert and spent == 1, (got, cert, spent)


def test_no_certified_answer_is_wrong():
    bad = [(t, g) for t, g, c, _ in _rows("machine") if c and g != t]
    assert bad == [], bad


def test_it_refuses_the_unsound_answers_the_distractor_creates():
    """Every false-FEASIBLE case is feasible only through the spurious
    capability, so deleting that one flips it."""
    rows = list(_rows("machine"))
    false_feasible = [(t, g, c) for t, g, c, _ in rows if g and not t]
    assert false_feasible, "the distractor stopped creating unsound answers"
    assert not any(c for _, _, c in false_feasible)


def test_it_is_not_a_detector_and_costs_coverage():
    """Sound, lossy, and the loss is real: on the clean surface a genuinely
    feasible instance almost never survives deleting every capability."""
    feasible = [c for _, g, c, _ in _rows(False) if g is True]
    assert feasible, "no feasible readings at all"
    assert sum(feasible) / len(feasible) < 0.3, (
        "coverage among feasible readings should be small -- at this slack "
        "almost every capability is load-bearing")
