"""The solvency reader, and the guard that would have caught it being broken.

This domain had no committed reader; its published 1.000 came from a script. The
first version here answered ``False`` on all 60 cases and scored **0.583** --
exactly the majority-class floor -- because the parent entity is named ``group``
with no number and the entity pattern required one. Accuracy alone looked like a
plausible weak reader. The output *distribution* gave it away immediately.
"""

from __future__ import annotations

from collections import Counter

import pytest

from symbolic_ai_generators.scramble import interleave, unsaturate
from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency.read_surface import (decide_reading,
                                                          read_signature)
from symbolic_ai_generators.solvency.surface import render_observation

HEADINGS = ("COVENANT REVIEW.", "AS FIRST REPORTED.", "SUBSEQUENT REVISIONS.",
            "THE TEST.")
N = 30


def _text(seed: int, V: int, how: str) -> str:
    obs = render_observation(generate(seed), variants=V)
    if how == "published":
        return obs.text
    if how == "unsaturated":
        return unsaturate(obs, headings=HEADINGS).text
    return interleave(unsaturate(obs, headings=HEADINGS, shuffle=False)).text


def test_the_reader_is_not_answering_a_constant() -> None:
    """The guard. A constant scores the majority-class floor and reads as a
    weak-but-working reader on accuracy alone."""
    got = Counter(decide_reading(read_signature(_text(s, 4, "published")))
                  for s in range(N))
    assert len(got) == 2, f"degenerate output: {dict(got)}"
    assert min(got.values()) >= 5, dict(got)


@pytest.mark.parametrize("V", [1, 4])
@pytest.mark.parametrize("how", ["published", "unsaturated", "interleaved"])
def test_exact_on_every_surface(V: int, how: str) -> None:
    """The audit predicted structure-independence from an ambiguity mass of
    0.000, before this reader existed."""
    for seed in range(N):
        case = generate(seed)
        want = decide(case, as_of=case.decision_date)[0]
        assert decide_reading(read_signature(_text(seed, V, how))) == want, seed


def test_every_filing_is_recovered_including_the_parents() -> None:
    """The bug was invisible in accuracy and obvious here: 78 parent filings
    were being dropped."""
    for seed in range(N):
        case = generate(seed)
        r = read_signature(_text(seed, 4, "published"))
        want = {(e, round(v, 2), k) for e, v, k in case.filings}
        got = {(e, round(v, 2), k) for e, v, k in r.filings}
        assert want <= got, (seed, want - got)
        assert any(e == "group" for e, _, _ in got), seed


def test_both_date_styles_are_read() -> None:
    """Half the corpus renders "1 June 2026" rather than "2026-06-01"."""
    styles = {read_signature(_text(s, 4, "published")).decision_date
              for s in range(N)}
    assert all(d and len(d) == 10 and d[4] == "-" for d in styles), styles


def test_an_unanswerable_reading_returns_none_rather_than_false() -> None:
    """A missing threshold is not a failed covenant. Same distinction the ASP
    kernel draws between unsatisfiable and unfinished."""
    r = read_signature("group owns sub_1 outright.")
    assert r.threshold is None
    assert decide_reading(r) is None
