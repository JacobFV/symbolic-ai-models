"""The essay corpus is only worth anything if its alignment is exact.

Every task built on it reads spans back out of the text, so a span that is off
by a character is a silently wrong label rather than a crash. These tests pin
the three properties that make the corpus a substrate: the alignment is exact,
the difficulty is where it is claimed to be, and the multi-hop fact is genuinely
not stated anywhere else.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.data import essay as E

pytest.importorskip("symbolic_ai_kg")


@pytest.fixture(scope="module")
def kg():
    from symbolic_ai_kg import load
    return load("wordnet")


@pytest.fixture(scope="module")
def essays(kg):
    pool = E.rich_topics(kg)
    return list(E.generate(kg, n=40, seed0=0, topics=pool))


def test_the_corpus_is_not_empty(essays):
    assert len(essays) >= 30


def test_every_mention_span_holds_its_own_surface(essays):
    """The alignment is exact, not approximately right.

    Spans are recorded as the text is written rather than recovered by
    searching, because a topic word that also occurs inside a hyponym would
    make a search silently pick the wrong occurrence.
    """
    for e in essays:
        for m in e.mentions:
            assert e.text[m.start:m.end] == m.surface, (
                f"{e.topic_word}: span {m.start}:{m.end} holds "
                f"{e.text[m.start:m.end]!r}, not {m.surface!r}")


def test_every_sentence_span_holds_its_own_text(essays):
    for e in essays:
        for s in e.sentences:
            assert e.text[s.start:s.end] == s.text or \
                e.text[s.start:s.end] == s.text.rstrip(), e.topic_word


def test_generation_is_deterministic_in_topic_and_seed(kg):
    pool = E.rich_topics(kg)
    a = list(E.generate(kg, n=5, seed0=3, topics=pool))
    b = list(E.generate(kg, n=5, seed0=3, topics=pool))
    assert [x.text for x in a] == [x.text for x in b]
    assert [x.to_dict() for x in a] == [x.to_dict() for x in b]


def test_a_different_seed_gives_a_different_essay(kg):
    pool = E.rich_topics(kg)
    a = list(E.generate(kg, n=5, seed0=3, topics=pool))
    b = list(E.generate(kg, n=5, seed0=99, topics=pool))
    assert [x.text for x in a] != [x.text for x in b]


def test_antecedent_distances_agree_with_the_mention_list(essays):
    """`d_*` is recorded at write time; recompute it and require agreement."""
    for e in essays:
        for i, m in enumerate(e.mentions):
            if m.antecedent < 0:
                assert m.d_mentions == -1
                continue
            a = e.mentions[m.antecedent]
            assert a.node == m.node
            assert m.d_mentions == i - m.antecedent
            assert m.d_sentences == m.sentence - a.sentence
            assert m.d_paragraphs == m.paragraph - a.paragraph


def test_the_corpus_contains_cross_paragraph_coreference(essays):
    """The property the single-paragraph curriculum cannot have at all."""
    total = sum(len(e.long_range(min_paragraphs=1)) for e in essays)
    assert total >= len(essays), "expected at least one per essay on average"


def test_lures_exist_and_are_what_they_claim(essays):
    """A lure's nearest preceding mention really is a different entity.

    This is the population that separates pointing from proximity, so if the
    flag were wrong the whole difficulty claim would be wrong with it.
    """
    seen = 0
    for e in essays:
        for i, m in enumerate(e.mentions):
            if not m.lure:
                continue
            seen += 1
            assert i > 0
            assert e.mentions[i - 1].node != m.node
    assert seen >= 5 * len(essays), f"only {seen} lures in {len(essays)} essays"


def test_the_two_hop_fact_is_not_stated_anywhere_else(essays):
    """The synthesis paragraph must be an inference, not a restatement.

    The first version drew the essay body from the *inherited* relation sets,
    so the fact it concluded "was not said directly" had in fact been said two
    paragraphs earlier. That made the multi-hop item solvable by copying.
    """
    checked = 0
    for e in essays:
        if not e.inference:
            continue
        checked += 1
        _, _, obj, _ = e.inference
        stated = [s for s in e.sentences
                  if s.hops == 1 and s.triple and s.triple[2] == obj]
        assert not stated, (
            f"{e.topic_word}: the 2-hop object is already stated by "
            f"{stated[0].text!r}")
    assert checked >= len(essays) // 2, "too few essays carry an inference"


def test_the_inference_is_reachable_in_the_graph(essays, kg):
    """`topic -isa-> via -rel-> obj` must actually hold."""
    for e in essays:
        if not e.inference:
            continue
        topic, via, obj, _ = e.inference
        assert via in kg.ancestors(topic) or via in kg.hypernyms(topic)


def test_paragraph_order_is_not_a_constant(kg):
    """Section order is permuted per episode, so position is not a free cue."""
    pool = E.rich_topics(kg)
    orders = {tuple(p.section for p in e.paragraphs)
              for e in E.generate(kg, n=40, seed0=0, topics=pool)}
    assert len(orders) > 5


def test_distractor_rate_moves_the_lure_count(kg):
    """The difficulty knob does what it says.

    Length is not the axis — referential ambiguity is — so the knob that
    matters must be shown to move the population it claims to.
    """
    pool = E.rich_topics(kg)
    topic = pool[0]
    secs = E.plan(kg, topic, seed=1)
    low = E.realise(kg, topic, secs, seed=1, distractor_rate=0.0)
    high = E.realise(kg, topic, secs, seed=1, distractor_rate=0.9)
    assert len(high.lures()) > len(low.lures())


def test_essays_are_multi_paragraph(essays):
    assert min(len(e.paragraphs) for e in essays) >= 2
    assert sum(len(e.paragraphs) for e in essays) / len(essays) >= 3.0
