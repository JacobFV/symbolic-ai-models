"""The ownership paragraph was decorative, and no measurement could see it.

`read_signature` enrols a member the moment it files a figure, so the whole first
paragraph -- one of the domain's two claim kinds -- changes nothing: deleting it
moves the answer on **0 of 200** cases. The reader was reported at 1.000 accuracy
and 1.000 filing recall in all six cells of V x arrangement without ever reading
the group structure, because the generator never files for a non-member.

That is the third instance of the same inert-by-construction pattern -- flood's
disused track drew its endpoints from outside the network, scheduling's withdrawn
machine carried no capability -- one level up, in the reader's own logic.

`read_signature_consolidated` takes membership from the ownership claims alone.
It is not a fix on its own: the cued divested-filer distractor needs it **and**
the staleness gate, and neither does anything without the other.
"""

from __future__ import annotations

from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency import surface as S
from symbolic_ai_generators.solvency.read_surface import (
    decide_reading, read_signature, read_signature_consolidated)
from symbolic_ai_generators.staleness import (filter_stale,
                                              stale_by_cancellation)

SEEDS = 60


def _score(reader, *, hard=False, cue="cued", gate=None, drop_owns=False,
           variants=4):
    ok = []
    for s in range(SEEDS):
        case = generate(s)
        want = decide(case, as_of=case.decision_date)[0]
        text = S.render_observation(case, variants=variants,
                                    hard_distractors=hard, cue=cue).text
        if drop_owns:
            text = "\n\n".join(text.split("\n\n")[1:])
        if gate:
            text = filter_stale(text, gate)
        ok.append(decide_reading(reader(text)) == want)
    return sum(ok) / len(ok)


def test_the_ownership_paragraph_is_decorative_to_the_published_reader():
    assert _score(read_signature) == 1.0
    assert _score(read_signature, drop_owns=True) == 1.0


def test_the_consolidated_reader_actually_needs_it():
    """The discriminator: removing the paragraph must now cost something, or
    membership is still coming from somewhere else."""
    assert _score(read_signature_consolidated) == 1.0
    assert _score(read_signature_consolidated, drop_owns=True) < 0.6


def test_the_consolidated_reader_costs_nothing_on_the_published_surface():
    for variants in (1, 2, 4):
        assert _score(read_signature_consolidated, variants=variants) == 1.0


def test_neither_fix_works_without_the_other():
    """A divested subsidiary that FILES needs both: the reader must stop
    enrolling filers, and the gate must remove the ownership sentence."""
    assert _score(read_signature, hard=True) < 0.6
    assert _score(read_signature, hard=True,
                  gate=stale_by_cancellation) < 0.6
    assert _score(read_signature_consolidated, hard=True) < 0.6
    assert _score(read_signature_consolidated, hard=True,
                  gate=stale_by_cancellation) == 1.0


def test_the_uncued_distractor_is_unrepairable():
    """The honest floor, asserted so the pair above is not read as a solution:
    a semantically stale sentence carrying no declared cue defeats both."""
    assert _score(read_signature_consolidated, hard=True, cue="uncued",
                  gate=stale_by_cancellation) < 0.6
