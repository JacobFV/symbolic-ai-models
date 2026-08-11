"""What changes with the rendering language, and what does not.

This matters more than it sounds, because the README used to offer
train-on-one-evaluate-on-another as a structure-versus-surface probe. On the
masked-node task it is not one: `Lesson.structured` takes no language, so the
term graph this repo builds is byte-identical whatever the prose says. A model
scored on Chinese graphs is being scored on the English graphs again.

The probe is real only on the text surface — and there, measured, nothing
transfers, because nothing is above floor in the source language either.
"""

from __future__ import annotations

import pytest

from symbolic_ai_models.data.curriculum import generate

LESSONS = ["symbol_grounding", "unification"]
LANGUAGES = ["english", "chinese", "turkish"]


@pytest.fixture(scope="module")
def renderings():
    return {lang: list(generate(LESSONS, n=3, seed0=1_000_000, language=lang))
            for lang in LANGUAGES}


def test_the_same_seed_is_the_same_episode_in_every_language(renderings):
    """The instance id is what certifies two renderings are one world."""
    english = renderings["english"]
    for lang in LANGUAGES[1:]:
        for a, b in zip(english, renderings[lang]):
            assert a.instance_id == b.instance_id
            assert a.lesson_id == b.lesson_id


def test_the_graph_does_not_change_with_the_language(renderings):
    """So a cross-language *node* experiment measures nothing.

    Pinned deliberately. If `structured` ever grows a language parameter this
    test will fail, and at that point the node task becomes a real probe and
    this file should say so instead.
    """
    english = renderings["english"]
    for lang in LANGUAGES[1:]:
        for a, b in zip(english, renderings[lang]):
            assert a.graph.to_dict() == b.graph.to_dict()


def test_the_text_does_change_with_the_language(renderings):
    """Which is where a cross-language claim would have to be made."""
    english = renderings["english"]
    for lang in LANGUAGES[1:]:
        differing = sum(a.prompt != b.prompt
                        for a, b in zip(english, renderings[lang]))
        assert differing == len(english), f"{lang} renders identically to English"


def test_every_language_round_trips_through_one_vocabulary(renderings):
    """The byte fallback must keep encoding lossless, however costly it is.

    Costly is measured, not hypothetical: an English-fitted vocabulary spends
    about 1.4 bits per token on English and 23 on Chinese. Lossless is the
    property being asserted here; cheap is not claimed.
    """
    from symbolic_ai_models.train import TrainConfig, build_tokenizer

    tok = build_tokenizer(TrainConfig(vocab_size=1200), renderings["english"])
    for lang in LANGUAGES:
        for ep in renderings[lang]:
            assert tok.decode(tok.encode(ep.text)) == ep.text
