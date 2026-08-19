"""Insensitivity where detection is impossible -- and it is the monotone half.

`owns` is multi-valued, so no arity constraint and no companion sentence checks
it, and detection fires 0.000. The other response is to prove the verdict does
not depend on the claim. It works, exactly, on the arm nothing else could touch:
the uncued divested-filer distractor gives 0.485 accuracy with 103 silent errors,
and the certificate turns that into 0.485 coverage with **zero**.

Two things are pinned beside that, because both are the finding:

- it is **one-sided** -- dropping a member can only lower the sum, so "below
  threshold" is free (fires on 1.000 of false verdicts) and "above" is not
  (0.000 of true ones);
- it is **blind across channels**, and gets *more* confident as the corruption
  grows: add a spurious filing and coverage rises 0.485 -> 0.935 while accuracy
  among the certified falls to 0.481.
"""

from __future__ import annotations

from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency import surface as S
from symbolic_ai_generators.solvency.certificate import (
    certifies_membership_insensitive)
from symbolic_ai_generators.solvency.read_surface import (
    decide_reading, read_signature, read_signature_consolidated)

SEEDS = 60


def _rows(hard=False, cue="cued", reader=read_signature):
    for s in range(SEEDS):
        case = generate(s)
        text = S.render_observation(case, variants=4, hard_distractors=hard,
                                    cue=cue).text
        r = reader(text)
        yield (decide(case, as_of=case.decision_date)[0], decide_reading(r),
               certifies_membership_insensitive(r))


def test_it_is_the_monotone_half():
    rows = list(_rows())
    assert all(c for _, v, c in rows if v is False), (
        "a false verdict survives every member deletion by construction")
    assert not any(c for _, v, c in rows if v is True), (
        "a true verdict should almost never certify: removing a member lowers "
        "the sum, so it needs a margin no single filing covers")


def test_it_rescues_the_arm_detection_cannot_see():
    """`owns` is multi-valued and the uncued phrasing carries no cue, so nothing
    else built today moves this arm off 0.485 with 103 silent errors."""
    rows = list(_rows(hard="owns", cue="uncued",
                      reader=read_signature_consolidated))
    certified = [(w, g) for w, g, c in rows if c]
    assert len(certified) > SEEDS * 0.2, f"coverage {len(certified)}/{SEEDS}"
    assert all(w == g for w, g in certified), "certified a wrong answer"


def test_it_is_blind_across_channels_and_grows_confident():
    """Add a spurious FILING -- a channel the membership hypothesis does not
    cover -- and coverage RISES while soundness collapses. Asserted so the
    conditional in the docstring cannot be read as a safety property."""
    one = [c for _, _, c in _rows(hard="owns", cue="uncued",
                                  reader=read_signature_consolidated)]
    both = list(_rows(hard=True, cue="uncued",
                      reader=read_signature_consolidated))
    assert sum(c for _, _, c in both) > sum(one), (
        "coverage should RISE when the corruption grows -- the spurious filing "
        "pushes the sum clear of the threshold, so no member deletion flips it")
    assert any(w != g for w, g, c in both if c), (
        "the certificate should now admit wrong answers; if it does not, the "
        "filing channel has gone and this scope note is stale")
