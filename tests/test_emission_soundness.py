"""Emission is sound over the channel it enumerates and blind to every other.

`read_content_roles_worlds` emits every role assignment the reader left open.
Where role assignment is the **only** way the read world can differ from the
true one, two things follow structurally rather than empirically:

- all candidates agreeing implies the agreed answer is correct, because the
  true assignment is among them;
- the collapsed answer being wrong implies the candidates disagree, because the
  collapsed assignment is also among them.

So agreement is a sound *and* complete detector of role error -- and neither
direction is a property of this reader. Both are properties of the enumeration
covering the channel.

The control matters more than the theorem: with ``hard_distractors=True`` the
reader also invents **links**, a channel the enumeration does not cover, and the
first direction fails outright (soundness 0.649 at 400 seeds). These tests pin
both, so the distinction cannot silently vanish.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood import surface as S
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (
    read_content_roles, read_content_roles_checked, read_content_roles_worlds)
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from adversarial_variants import ADVERSARIAL  # noqa: E402

SEEDS = 40


@pytest.fixture
def adversarial():
    """Every phrasing written to evade the declared anchors."""
    original = dict(S._VARIANTS)
    for role, forms in ADVERSARIAL.items():
        S._VARIANTS[role] = forms
    try:
        yield
    finally:
        S._VARIANTS.clear()
        S._VARIANTS.update(original)


def _cases(hard: bool):
    for s in range(SEEDS):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        obs = S.render_observation(case, variants=4, hard_distractors=hard)
        flat = unsaturate(obs, drop_headings=True, shuffle=False)
        text = interleave(flat).text
        worlds = read_content_roles_worlds(text)
        answers = {solve(w)[0] for w in worlds}
        yield s, want, solve(read_content_roles(text))[0], answers, text


def test_agreement_implies_correct_when_roles_are_the_only_channel(adversarial):
    decided = [(s, want) for s, want, _, answers, _ in _cases(hard=False)
               if len(answers) == 1 and next(iter(answers)) != want]
    assert decided == [], f"agreement admitted a wrong answer: {decided}"


def test_a_wrong_collapse_always_disagrees(adversarial):
    missed = [s for s, want, got, answers, _ in _cases(hard=False)
              if got != want and len(answers) == 1]
    assert missed == [], f"collapse wrong and candidates agreed: {missed}"


def test_the_detector_has_something_to_detect(adversarial):
    """Both directions above are vacuous unless the collapse actually fails."""
    wrong = [s for s, want, got, _, _ in _cases(hard=False) if got != want]
    assert len(wrong) >= 4, f"only {len(wrong)} collapse failures at {SEEDS} seeds"


def test_a_second_channel_breaks_agreement(adversarial):
    """The theorem's premise is load-bearing: invented links are not enumerated."""
    bad = [s for s, want, _, answers, _ in _cases(hard=True)
           if len(answers) == 1 and next(iter(answers)) != want]
    assert bad, ("hard_distractors admitted no wrong agreement -- if this ever "
                 "passes, the phantom-link channel has gone and the scope note "
                 "on read_content_roles_worlds is stale")


def test_the_role_flag_refuses_everything_at_the_lexical_floor(adversarial):
    """A detector calibrated where the vocabulary works has no discrimination
    where it fails: role_assignment_forced is False on every case here."""
    forced = [s for s, _, _, _, text in _cases(hard=False)
              if read_content_roles_checked(text)[1]]
    assert forced == [], f"expected no forced readings, got {forced}"
