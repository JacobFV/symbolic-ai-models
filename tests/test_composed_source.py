"""Two knowledge sources behind one accessor set, without merging their identities.

The test that matters most is
``test_an_unaligned_topic_gets_exactly_what_the_primary_gives``. It is the
invariant that caught a real bug: the wrapper did not forward
``inherited=False``, ``essay.gather`` swallowed the resulting ``TypeError`` and
retried without it, and the composed source silently returned the *inherited*
closure where WordNet returns directly stated facts — reading as a 10x
improvement in composition coverage that was entirely fictional.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.data.essay import SECTIONS, gather, rich_topics
from symbolic_ai_core.data.knowledge_source import capabilities_of

kg = pytest.importorskip("symbolic_ai_kg")
from symbolic_ai_kg.composed import (ALIGNMENT_RELATION, ComposedGraph,  # noqa: E402
                                     compose)


@pytest.fixture(scope="module")
def comp():
    return compose()


@pytest.fixture(scope="module")
def wn():
    return kg.load("wordnet")


# --- the invariant that caught the bug -----------------------------------
def test_an_unaligned_topic_gets_exactly_what_the_primary_gives(comp, wn):
    """No alignment means nothing to supplement, so the answers must be equal.

    Any difference is the composition changing the *question* rather than
    enriching the answer.
    """
    topics = [t for t in rich_topics(wn, min_sections=3)
              if t not in comp.alignment]
    assert len(topics) > 100, "too few unaligned topics to check anything"
    for t in topics[:400]:
        assert gather(comp, t) == gather(wn, t), comp.word(t)


def test_the_accessors_forward_their_keywords(comp, wn):
    """`inherited=False` is the difference between a directly stated fact and an
    inherited one, and `essay.gather` relies on it.

    Searches for a node where the two genuinely differ rather than assuming the
    first one does -- most nodes inherit nothing, and asserting on an arbitrary
    one tests the search, not the forwarding.
    """
    node = next((t for t in range(len(wn))
                 if len(wn.parts_of(t)) > len(wn.parts_of(t, inherited=False))),
                None)
    assert node is not None, "no node in this graph inherits any part"
    direct = set(comp.parts_of(node, inherited=False))
    everything = set(comp.parts_of(node))
    assert direct < everything, (
        "inherited=False changed nothing on a node that demonstrably inherits, "
        "so the keyword is not reaching the underlying source")
    assert direct == set(wn.parts_of(node, inherited=False)) | {
        i for i in comp.parts_of(node, inherited=False)}, "sanity"


def test_an_accessor_that_takes_no_such_keyword_is_not_handed_one(comp, wn):
    """`hypernyms(n)` has no `inherited` parameter. Blanket-forwarding raises a
    TypeError, which `essay.gather` swallows by retrying without the keyword --
    and that silent retry is exactly how the original mismatch stayed invisible.
    """
    assert comp.hypernyms(0, inherited=False) == wn.hypernyms(0)
    assert not comp._accepts("hypernyms", "inherited")
    assert comp._accepts("parts_of", "inherited")


# --- what the composition is for -----------------------------------------
def test_it_fills_the_two_sections_wordnet_populates_nowhere(comp, wn):
    from symbolic_ai_core.data.essay import sections_available

    a = sections_available(wn, name="wordnet")
    b = sections_available(comp, name="wordnet+cskg")
    assert a["qualities"] == 0.0 and a["behaviour"] == 0.0
    assert b["qualities"] > 0.0 and b["behaviour"] > 0.0


def test_it_does_not_lose_what_the_primary_had(comp, wn):
    """Supplementing must be monotone: the primary's own answers survive.

    Uses `gather`, which is what actually consumes these accessors and knows
    which of them take `inherited` -- `hypernyms(n)` does not and `parts_of`
    does, and the composed source now forwards exactly what the primary accepts.
    """
    for t in rich_topics(wn, min_sections=3)[:200]:
        own, both = gather(wn, t), gather(comp, t)
        for sec in SECTIONS:
            assert set(own.get(sec, ())) <= set(both.get(sec, ())), (
                f"{comp.word(t)} lost {sec}")


def test_node_ids_stay_in_the_primary_space(comp, wn):
    """A composed source with two id spaces has no way to say which it meant."""
    assert len(comp) == len(wn)
    for i in (0, 5, 100, len(wn) - 1):
        assert comp.word(i) == wn.word(i)


# --- the double-count guard ----------------------------------------------
def test_duplicates_are_dropped_and_counted(comp, wn):
    """CSKG consolidates seven upstreams including WordNet, so an edge in both
    is one observation seen twice."""
    for t in rich_topics(wn, min_sections=3)[:300]:
        for spec in SECTIONS.values():
            getattr(comp, spec["accessor"])(t, inherited=False)
    rate = comp.duplicate_rate()
    assert rate > 0.0, "no duplicate was ever found, so the guard is untested"
    assert rate < 0.5, f"half the composition was double counting ({rate})"
    per = comp.census()["per_accessor"]
    assert any(v["duplicates"] for v in per.values())


def test_the_supplement_never_repeats_a_lemma_the_primary_already_gave(comp, wn):
    """The dedupe is about the *composition*, not about the primary.

    WordNet alone returns repeated lemmas -- distinct synsets share a word, so
    `hyponyms('individual')` yields 135 nodes over 132 lemmas. A composed source
    that silently deduplicated those would be changing the primary's answer,
    which is the one thing it must not do. What it must guarantee is that the
    *added* nodes introduce no lemma the primary already supplied.
    """
    for t in rich_topics(wn, min_sections=3)[:200]:
        for spec in SECTIONS.values():
            acc = spec["accessor"]
            own = getattr(wn, acc)(t)
            both = getattr(comp, acc)(t)
            assert list(both[:len(own)]) == list(own), "the primary's order moved"
            added = [comp.word(i) for i in both[len(own):]]
            assert not (set(added) & {wn.word(i) for i in own}), (
                f"{comp.word(t)} {acc}: the supplement repeated a lemma the "
                f"primary already gave")
            assert len(added) == len(set(added))


# --- identity is a claim, not a merge ------------------------------------
def test_the_join_is_recorded_as_a_possibly_same_alignment(comp):
    aligns = comp.alignments()
    assert aligns
    a = aligns[0]
    assert a.relation == ALIGNMENT_RELATION == "possibly_same"
    assert a.confidence is not None and a.confidence < 1.0, (
        "a lemma join asserted at full strength is a merge wearing a claim's "
        "clothes")
    assert a.left.startswith("wn:") and a.right.startswith("cn:"), (
        "the two namespaces were collapsed")


def test_the_composed_source_still_drives_the_generator(comp):
    from symbolic_ai_core.data.essay import REQUIRED, generate
    from symbolic_ai_core.data.knowledge_source import require_capabilities

    require_capabilities(capabilities_of(comp, name="composed", names=REQUIRED),
                         REQUIRED, who="the essay generator")
    assert list(generate(comp, n=2, source="wordnet+cskg"))
