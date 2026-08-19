"""Over-splitting and over-deleting are the same failure.

`filter_stale` cuts at a granularity, and *"clause, not sentence"* answers which
of two units rather than whether there is an optimum. Sweeping five -- document,
sentence, clause, fine, finest -- gives a **peak**, not a slope, on both the
Wikipedia corpus and the generated `stale_clause` surface.

The mechanism is that a splitter fine enough to cut *through* the pattern the
reader is looking for (`a subsidiary **of** X`) leaves no fragment matching it,
which is indistinguishable from deleting the sentence. On Wikipedia the finest
split reproduces the sentence split's numbers exactly.
"""

from __future__ import annotations

import re
import statistics

from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency import surface as VS
from symbolic_ai_generators.solvency.read_surface import (
    decide_reading, read_signature_accumulating)
from symbolic_ai_generators.staleness import (filter_stale,
                                              stale_by_cancellation)

SEEDS = 60

_FINEST = re.compile(r"[,;:()]|\s+(?:but|although|though|and|or|which|that|"
                     r"while|where|when|of|in|for|by|from|to)\s+")


def _score(unit=None, splitter=None):
    ok = []
    for s in range(SEEDS):
        case = generate(s)
        want = decide(case, as_of=case.decision_date)[0]
        text = VS.render_observation(case, variants=4, stale_clause=True).text
        if unit:
            text = filter_stale(text, stale_by_cancellation, unit=unit)
        elif splitter is not None:
            out = []
            for para in text.split("\n\n"):
                kept = []
                for sent in re.split(r"(?<=[.?])\s+", para):
                    if not sent.strip():
                        continue
                    if not stale_by_cancellation(sent):
                        kept.append(sent)
                        continue
                    parts = [p.strip().rstrip(".")
                             for p in splitter.split(sent) if p.strip()]
                    live = [p for p in parts
                            if not stale_by_cancellation(p)]
                    if live:
                        kept.append(" ".join(live) + ".")
                out.append(" ".join(kept))
            text = "\n\n".join(out)
        ok.append(decide_reading(read_signature_accumulating(text)) == want)
    return statistics.mean(ok)


def test_the_curve_is_a_peak_not_a_slope():
    no_filter = _score()
    sentence = _score(unit="sentence")
    clause = _score(unit="clause")
    finest = _score(splitter=_FINEST)
    assert sentence < no_filter, (sentence, no_filter)      # over-deleting
    assert finest < clause, (finest, clause)                # over-splitting
    assert clause == 1.0
    assert clause > no_filter


def test_splitting_through_the_pattern_loses_the_claim():
    """A splitter that cuts at `of` breaks the very mention being looked for.
    Over-splitting is over-deleting by another route."""
    sent = ("sub_0, formerly a subsidiary of sub_97, reported 105.87 USD, "
            "filed 2026-05-29.")
    parts = [p for p in _FINEST.split(sent) if p and p.strip()]
    assert not any("105.87" in p and "sub_0" in p for p in parts), parts
