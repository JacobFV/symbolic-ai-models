"""Cancellation, not tense, and it misfires where the predicate IS a negation.

`symbolic_ai_generators/staleness.py` is the first component here meant to be
shared across domains unchanged: a second reading of the **same** sentence, since
the channel that matters is multi-valued and no second source knows it.

Three things are pinned:

- both gates repair the scheduling distractor, so the catch is not the point;
- only the cancellation gate survives real claims phrased in the **past**, which
  is what separates the two signals the generators had confounded;
- the cancellation gate **deletes a true flooding claim**, because
  "it is no longer passable" is a cancellation cue inside a sentence whose whole
  job is to assert that something has been cancelled.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from symbolic_ai_generators.scheduling import generate as sched_generate
from symbolic_ai_generators.scheduling import surface as SS
from symbolic_ai_generators.scheduling.read_surface import read_signature
from symbolic_ai_generators.staleness import (filter_stale,
                                              stale_by_cancellation,
                                              stale_by_tense)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from hard_regime_milestone import solve_world  # noqa: E402
from staleness_gate import PAST_TRUE  # noqa: E402

SEEDS = 60


def _sched(hard, override, gate) -> float:
    original = dict(SS._VARIANTS)
    if override:
        for k, v in override.items():
            SS._VARIANTS[k] = v
    try:
        ok = []
        for s in range(SEEDS):
            case = sched_generate(s)
            text = SS.render_observation(case, variants=4,
                                         hard_distractors=hard).text
            if gate:
                text = filter_stale(text, gate)
            ok.append(solve_world(read_signature(text))[0] == case.feasible)
    finally:
        SS._VARIANTS.clear()
        SS._VARIANTS.update(original)
    return sum(ok) / len(ok)


def test_the_gate_repairs_the_admitted_capability():
    assert _sched("machine", None, None) < 0.95
    assert _sched("machine", None, stale_by_cancellation) == 1.0


def test_only_cancellation_survives_a_true_claim_in_the_past():
    past = PAST_TRUE["scheduling"]
    assert _sched(False, past, stale_by_tense) < 0.8, (
        "the tense gate should destroy real claims phrased in the past")
    assert _sched(False, past, stale_by_cancellation) == 1.0


def test_the_gate_deletes_a_true_flooding_claim():
    """The blind spot, asserted so it cannot vanish quietly: flood's `flooded`
    predicate IS a cancellation, so a cancellation gate cannot tell a sentence
    that withdraws a claim from one asserting something has been withdrawn."""
    real = ("Water rose through region_2 during the night and it is no longer "
            "passable; nothing may be routed through it.")
    assert stale_by_cancellation(real)
    assert filter_stale(real, stale_by_cancellation).strip() == ""


def test_the_flood_distractor_needs_no_tense():
    """`once ran` carries no past auxiliary, so the tense gate misses it."""
    track = "A disused track once ran from region_0 to region_3."
    assert not stale_by_tense(track)
    assert stale_by_cancellation(track)


def test_exactly_one_real_phrasing_trips_the_gate_and_it_is_flooding():
    """No default phrasing is in the past -- which is why the past-tense arm
    exists, the generators having confounded tense with cancellation -- and the
    only one the cancellation gate touches is flood's `flooded`, whose predicate
    IS a cancellation. Enumerated rather than asserted away."""
    from symbolic_ai_generators.flood import surface as FS
    tripped = []
    for mod in (SS, FS):
        for kind, forms in mod._VARIANTS.items():
            for form in forms:
                s = re.sub(r"\{[^}]*\}", "region_0", form)
                assert not stale_by_tense(s), (kind, form)
                if stale_by_cancellation(s):
                    tripped.append(kind)
    assert tripped == ["flooded"], tripped


def test_temporal_ordering_is_not_cancellation():
    """The four cues dropped after 36,223 sentences of real prose. A sentence
    may bound a state in the past without withdrawing it."""
    from symbolic_ai_generators.staleness import CANCELLING_V1
    for s in ("Before the reaction, the sample was weighed.",
              "The present method is better than those previously reported.",
              "Once-weekly dosing was tolerated as well as the comparator.",
              "Measurements continued until the endpoint was reached."):
        assert not stale_by_cancellation(s), s
        assert stale_by_cancellation(s, cues=CANCELLING_V1), (
            f"{s!r} should still fire under the first list, or the record of "
            "what changed is wrong")


def test_used_to_is_two_constructions_and_only_one_cancels():
    """53.5% of every fire on real prose was the PASSIVE OF USE, 439 of 443 as
    the only cue in the sentence. Not a temporal confusion -- two grammars."""
    assert stale_by_cancellation("job_0 used to cut as well.")
    assert stale_by_cancellation("sub_98 used to be part of the group.")
    for s in ("These results are then used to obtain the inequalities.",
              "Funnel plots have been widely used to examine bias.",
              "A survey of styles is used to classify them."):
        assert not stale_by_cancellation(s), s


def test_the_corrections_cost_the_generated_surfaces_nothing():
    """Removals can only reduce firing, so this is a check and not a fit -- and
    it is the evidence that what was removed was noise. Every distractor here
    carries a second, genuinely cancelling cue."""
    for s in ("A disused track once ran from region_0 to region_3.",
              "machine_0 was set up to paint last shift, before the head came "
              "off.",
              "job_0 used to cut as well, until the drawing was revised.",
              "sub_98 is a former subsidiary of group, divested before the "
              "period.",
              "job_90 was cancelled by the customer and has been struck from "
              "the list."):
        assert stale_by_cancellation(s), s


def test_struck_needs_its_particle():
    """Narrative's dominant fire was `struck` at 29.9% -- the verb *strike*,
    where the abstracts corpus fired it twice. Each genre surfaced a different
    dominant false positive and neither was predictable from the other."""
    assert not stale_by_cancellation("The blow struck him on the shoulder.")
    assert not stale_by_cancellation("She was struck by the resemblance.")
    assert stale_by_cancellation("job_90 has been struck from the list.")
    assert stale_by_cancellation("The entry was struck off the register.")


def test_be_used_to_means_accustomed_and_does_not_cancel():
    """The third construction. `be used to` is a state that may well still hold,
    so suppressing it is correct rather than a false negative -- it accounts for
    most of the 21% of narrative `used to` the lookback drops."""
    assert not stale_by_cancellation("He had been used to look in Hertfordshire.")
    assert not stale_by_cancellation("He has been used to her complaints.")


def test_the_lookback_stops_at_the_clause_boundary():
    """Unbounded, it reached across a comma into a different clause and dropped
    a genuine habitual."""
    assert stale_by_cancellation(
        "All during this May that we have been having, I used to run down.")
