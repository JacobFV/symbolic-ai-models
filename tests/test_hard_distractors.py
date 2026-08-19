"""The distractor that was defanged, and the option that arms it.

`audit_surface(prose=True)` flagged that "A disused track once ran from X to Z"
carries exactly the ``link`` signature. The reader admits it in every case. It
was harmless only because the generator drew its endpoints from ``_OUTSIDE`` --
regions appearing nowhere else -- so the phantom edge connected nothing.

That masked a reader defect rather than preventing it. ``hard_distractors=True``
points the sentence at two real, unlinked regions, and the reader falls from
1.000 to about 0.33 on that substitution alone.
"""

from __future__ import annotations

import statistics

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import read_content_roles
from symbolic_ai_generators.flood.surface import render_observation

N = 20


def _acc(hard: bool) -> float:
    ok = []
    for seed in range(N):
        case = generate(seed)
        text = render_observation(case, variants=4,
                                  hard_distractors=hard).text
        ok.append(solve(read_content_roles(text))[0] == solve(case.world)[0])
    return statistics.mean(ok)


def test_the_default_is_unchanged() -> None:
    """Every published number was measured with the easy distractor, so the
    default must keep meaning what it meant."""
    assert _acc(False) == 1.0


def test_the_hard_distractor_actually_breaks_the_reader() -> None:
    """If it did not, the option would be decoration."""
    assert _acc(True) < 0.6


def test_the_phantom_edge_is_real_and_absent() -> None:
    """A distractor that could not change the answer is not a distractor."""
    import re
    track = re.compile(r"A disused track once ran from (region_\d+) to "
                       r"(region_\d+);")
    for seed in range(N):
        case = generate(seed)
        text = render_observation(case, variants=4, hard_distractors=True).text
        m = track.search(text)
        assert m, seed
        a, b = m.group(1), m.group(2)
        links = {frozenset(c.entities()) for c in case.world.claims
                 if c.predicate == "link"}
        regions = {e for pair in links for e in pair}
        assert a in regions and b in regions, (seed, a, b)
        assert frozenset({a, b}) not in links, (seed, a, b)


def test_nothing_but_the_two_ids_changes() -> None:
    """The claims, the answer and the rest of the text are untouched, so the
    drop cannot be attributed to anything else."""
    for seed in range(8):
        case = generate(seed)
        easy = render_observation(case, variants=4, hard_distractors=False)
        hard = render_observation(case, variants=4, hard_distractors=True)
        assert easy.covered() == hard.covered(), seed
        assert {s.claim: easy.text[s.start:s.end] for s in easy.spans
                if s.claim is not None} == \
               {s.claim: hard.text[s.start:s.end] for s in hard.spans
                if s.claim is not None}, seed
