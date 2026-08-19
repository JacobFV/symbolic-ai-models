"""WordNet from the archive, and the measured limits of what it can decide.

`symbolic_ai_generators/wordnet.py` reads the distributed archive with the
standard library only. It is the first external standard used here as a given,
and the tests pin both what it supplies and what it does not.
"""

from __future__ import annotations

import pytest

from symbolic_ai_generators.wordnet import (first_sense_supersense,
                                            hypernym_closure, is_verb_lemma,
                                            verb_supersenses, wordnet_path)

pytestmark = pytest.mark.skipif(wordnet_path() is None,
                                reason="WordNet archive not on this machine")


def test_it_reads_the_archive():
    assert is_verb_lemma("own")
    assert is_verb_lemma("owns")          # regular strip
    assert is_verb_lemma("left")          # verb.exc: left -> leave
    assert not is_verb_lemma("zzzz")


def test_supersenses_classify_by_subject_matter_not_by_aspect():
    """The reason a supersense rule cannot separate a verb that ASSERTS a
    relation from one that ENDS it: `cease` is about states and `divest` is
    about possessions, exactly like `own`."""
    assert first_sense_supersense("cease") == "verb.stative"
    assert first_sense_supersense("divest") == "verb.possession"
    assert first_sense_supersense("own") == "verb.possession"
    assert "verb.stative" in verb_supersenses("left")


def test_the_hypernym_closure_does_separate_them():
    deep = {"end", "discontinue", "leave", "exit", "deprive", "remove"}
    for w in ("ceased", "ended", "exited", "departed", "left"):
        assert deep & hypernym_closure(w), w
    for w in ("owns", "holds", "requires", "includes", "connects"):
        assert not (deep & hypernym_closure(w)), w


def test_the_shallow_ancestors_are_the_useless_ones():
    """`change` sits near the root, so ordinary verbs reach it. That is why it
    fires on 41% of real sentences and the deep six fire on 6%."""
    assert "change" in hypernym_closure("increase")
    assert "change" in hypernym_closure("add")
    assert not ({"end", "discontinue", "leave", "exit"} & hypernym_closure("add"))


def test_the_worked_false_positive_is_pinned():
    """One word took solvency's clean surface from 1.000 to 0.650: `dated`, a
    participial modifier whose first WordNet sense is the romantic one."""
    assert "leave" in hypernym_closure("dated")
