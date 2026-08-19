"""A declared vocabulary is worse than none exactly when it is confidently wrong.

Two things are pinned here, and the first is about an experiment rather than a
reader.

`adversarial_variants._verify_adversarial` asserts that no adversarial phrasing
contains a declared anchor, using the **same predicate** `_anchor_role` computes.
That makes `_anchor_role` silent on every adversarial sentence by construction,
so the arm reduces to the emptied-anchor arm -- they agree **case by case**, not
merely in aggregate. A control that asserts the mechanism cannot fire cannot
measure what happens when it fires.

`misfiring_vocabulary.MISFIRING` is the inversion: phrasings that trip exactly
one anchor set, the wrong one. Those cost 0.290 against the floor in both
arrangements at 400 seeds.
"""

from __future__ import annotations

import sys
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood import surface as S
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import read_content_roles
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from adversarial_variants import ADVERSARIAL  # noqa: E402
from misfiring_vocabulary import (EMPTY, MISFIRING, _hits,  # noqa: E402
                                  _verify_misfires, WRONG)

SEEDS = 60


def _outcomes(*, anchors, variants):
    original = dict(S._VARIANTS)
    if variants is not None:
        for role, forms in variants.items():
            S._VARIANTS[role] = forms
    try:
        out = []
        for s in range(SEEDS):
            case = generate(s)
            want = solve(case.world)[0]
            if not want:
                continue
            obs = S.render_observation(case, variants=4)
            flat = unsaturate(obs, drop_headings=True, shuffle=False)
            text = interleave(flat).text
            try:
                got = solve(read_content_roles(text, anchors=anchors))[0]
            except Exception:
                got = ()
            out.append(got == want)
    finally:
        S._VARIANTS.clear()
        S._VARIANTS.update(original)
    return out


def test_evading_phrasings_reproduce_the_floor_case_by_case():
    """Not 'to three decimals' -- the same computation, so the same cases."""
    floor = _outcomes(anchors=EMPTY, variants=None)
    evade = _outcomes(anchors=None, variants=ADVERSARIAL)
    assert floor == evade, "the evading arm is no longer the emptied arm"


def test_the_misfire_verification_asserts_the_misfire_exists():
    """The honest inversion: it must assert the anchor FIRES, and wrongly."""
    _verify_misfires()
    for role, forms in MISFIRING.items():
        for form in forms:
            assert _hits(form) == {WRONG[role]}


def test_misfiring_is_worse_than_having_no_vocabulary_at_all():
    floor = sum(_outcomes(anchors=EMPTY, variants=None))
    mis = sum(_outcomes(anchors=None, variants=MISFIRING))
    assert mis < floor - 5, (
        f"misfiring scored {mis} against a floor of {floor} over {SEEDS} seeds; "
        "the 0.290 penalty measured at 400 seeds has gone")
