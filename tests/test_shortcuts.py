"""The shortcut audit: what an unthinking rule gets, and what that means.

Two uses, and the tests cover both. As a **floor**, a shortcut stops a model
being credited for something a cheat already achieves. As an **audit**, a
shortcut that solves a lesson outright is evidence about the lesson — the
distractors leak — and that is a fact about the generator, not the model.
"""

from __future__ import annotations

import pytest

from symbolic_ai_models.agent import ChoiceResult, CurriculumReport
from symbolic_ai_models.data.curriculum import generate
from symbolic_ai_models.shortcuts import (SHORTCUTS, best_shortcut,
                                          shortcut_scores, shortcut_table)


@pytest.fixture(scope="module")
def episodes():
    return [e for e in generate(["symbol_grounding", "unification"], n=8,
                                seed0=1_000_000) if e.choices]


def test_every_shortcut_picks_an_offered_option(episodes):
    """A cheat that invents an answer is not measuring what it claims to."""
    for shortcut in SHORTCUTS:
        for ep in episodes:
            assert shortcut.pick(ep.prompt, list(ep.choices)) in ep.choices


def test_shortcuts_are_parameter_free_and_deterministic(episodes):
    """Nothing is fitted, so there is no train/eval split to respect."""
    assert shortcut_scores(episodes) == shortcut_scores(episodes)
    assert shortcut_scores(list(reversed(episodes))) == shortcut_scores(episodes)


def test_a_leaked_answer_set_is_caught():
    """The audit must fire on a set built so the answer is always longest.

    And *only* that cheat should fire: two shortcuts agreeing has to mean they
    found the same thing, not that they broke a tie the same way.
    """
    # The answer is longest but neither first, last, nor lexicographically
    # extreme, so exactly one cheat should fire. An earlier version of this
    # fixture put the answer last *and* largest, and five unrelated shortcuts
    # scored 1.0 on it — which is how the tie-breaking flaw was found.
    rigged = [ChoiceResult(lesson_id="rigged", instance_id=str(i), answer="mmmmmm",
                           predicted="", correct=False, n_choices=3,
                           prompt="which one?", choices=("a", "mmmmmm", "zz"))
              for i in range(10)]
    scores = shortcut_scores(rigged)
    assert scores["longest"] == 1.0
    assert [n for n, v in scores.items() if v == 1.0] == ["longest"]
    assert best_shortcut(rigged) == ("longest", 1.0)


def test_the_floor_absorbs_the_best_cheat():
    """A model beating chance but losing to a shortcut must not show a lift."""
    rigged = [ChoiceResult(lesson_id="rigged", instance_id=str(i), answer="mmmmmm",
                           predicted="mmmmmm" if i < 6 else "a",
                           correct=i < 6, n_choices=3, prompt="which one?",
                           choices=("a", "mmmmmm", "zz"))
              for i in range(10)]
    report = CurriculumReport(rigged)
    assert report.accuracy == 0.6
    # uniform would be 0.333 and would have called this a real gain
    assert report.floor == 1.0
    assert report.lift <= 0.0


def test_shortcut_scores_survive_an_empty_answer_set():
    assert all(v != v for v in shortcut_scores([]).values())


def test_the_table_names_what_each_cheat_exploits(episodes):
    """Which cheat works says what leaked, so the table prints all of them."""
    text = shortcut_table(episodes)
    for shortcut in SHORTCUTS:
        assert shortcut.name in text
    assert "exploits" in text
