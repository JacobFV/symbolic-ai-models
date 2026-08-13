"""Does the graph belong to the text it is handed out with?

``curriculum.generate`` calls the generator twice — ``example(seed, language=)``
for the prose and ``structured(seed)`` for the term — and pairs the results. Its
docstring says the shared ``instance_id`` is what certifies the two describe the
same episode. It is not: ``instance_id`` is ``blake2b(lesson|seed|difficulty)``
and is therefore equal whatever the two calls returned. The guard cannot fail.

Whether that matters is an empirical question, and these tests answer it rather
than argue it. In English it does not — the two builds agree on all 179 lessons.
Outside English it does, for a small named set, because ``example`` sets the
``ACTIVE_LANGUAGE`` context variable that some generators draw material from and
``structured`` does not.

These tests **pin the current behaviour, including the part that is wrong**.
Nothing here is a fix: fixing it would change generation, and generation may not
change without re-recording the fingerprint and re-running everything that
depends on it. The point is that the next person to touch it finds out.
"""

from __future__ import annotations

import json

import pytest

import symbolic_ai_data as D
from symbolic_ai_data.context import GenerationContext
from symbolic_ai_data.generators.extra import ACTIVE_LANGUAGE
from symbolic_ai_data.lesson import to_json

from symbolic_ai_models.data import curriculum as C

#: The languages with hand-written packs, minus English which is the baseline.
OTHER_LANGUAGES = ("chinese", "english_synonym", "spanish", "swahili",
                   "symbols", "turkish")

SEEDS = (0, 1, 7)

#: Measured, not assumed. Every (lesson, language) whose *term* changes when the
#: generator is told which language the episode will be read in.
DIVERGENT = {
    ("center_embedding", "spanish"),
    ("event_semantics", "spanish"),
    ("long_range_agreement", "spanish"),
    ("pronoun_coreference", "chinese"),
    ("pronoun_coreference", "spanish"),
    ("thematic_roles", "spanish"),
}


def _term(lesson, seed, language=None):
    """The term ``build`` produces, with the language in force or not.

    ``Lesson.example`` sets ``ACTIVE_LANGUAGE`` before building and
    ``Lesson.structured`` does not, so these two calls are what the two halves
    of one :class:`Episode` are actually built from.
    """
    L = D.get(lesson)
    token = ACTIVE_LANGUAGE.set(language) if language else None
    try:
        ctx = GenerationContext(language=language) if language else GenerationContext()
        obs, choices, answer, _ = L.build(seed, ctx)
        return json.dumps([to_json(obs), [str(c) for c in choices], str(answer)],
                          sort_keys=True, ensure_ascii=False)
    finally:
        if token is not None:
            ACTIVE_LANGUAGE.reset(token)


def test_in_english_the_graph_is_the_term_the_prose_came_from():
    """The condition every published number depends on. All runs in this repo
    are English, so this is the assertion that says the masked-node task is
    scoring the structure behind the text it was shown."""
    bad = [lid for lid in C.lesson_ids() for s in SEEDS
           if _term(lid, s) != _term(lid, s, "english")]
    assert not bad, sorted(set(bad))


def test_outside_english_a_named_few_diverge_and_the_id_check_cannot_see_it():
    """The pin. Not a wish — a record of what is true today.

    If this fails with *fewer* cells, someone fixed it and must re-record the
    fingerprint. If it fails with more, a change spread the defect.
    """
    found = set()
    for lid in C.lesson_ids():
        for lang in OTHER_LANGUAGES:
            if any(_term(lid, s) != _term(lid, s, lang) for s in SEEDS):
                found.add((lid, lang))
    assert found == DIVERGENT, {
        "unexpectedly divergent": sorted(found - DIVERGENT),
        "no longer divergent": sorted(DIVERGENT - found),
    }


@pytest.mark.parametrize("lesson,language", sorted(DIVERGENT))
def test_the_instance_id_guard_passes_on_a_pair_that_does_not_match(lesson, language):
    """``generate`` raises when the two ``instance_id``s differ. They never do.

    Demonstrated rather than asserted from the source: these are exactly the
    episodes where the two halves were built from different terms, and
    ``generate`` hands them back without complaint.
    """
    lc = D
    L = lc.get(lesson)
    ex = L.example(0, language=language)
    st = L.structured(0)
    assert ex.instance_id == st["instance_id"]          # the guard is satisfied
    assert _term(lesson, 0) != _term(lesson, 0, language)   # and it should not be

    # And it reaches the public surface: an Episode comes back, unflagged.
    (ep,) = list(C.generate([lesson], n=1, seed0=0, language=language))
    assert ep.language == language and len(ep.graph) > 0


def test_the_visible_cost_is_an_answer_the_graph_does_not_contain():
    """The sharpest case, spelled out, because "the terms differ" is abstract.

    ``center_embedding`` in Spanish: the episode's answer is ``saludó`` and the
    graph it ships with was built in English and contains ``greeted``. A
    masked-node model asked for that node is graded against a symbol that does
    not appear in the prompt it was shown.
    """
    (ep,) = list(C.generate(["center_embedding"], n=1, seed0=0, language="spanish"))
    assert ep.answer not in ep.graph.labels
    assert "greeted" in ep.graph.labels and "saludó" in ep.prompt
