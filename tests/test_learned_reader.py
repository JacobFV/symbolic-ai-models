"""The learned reader: what it recovers, and the control that must fail.

Small fits -- 60 documents rather than the 400 the experiments use -- because
these guard the *mechanisms*, not the headline. The headline is
`runs/reader_survives.json` and the note beside it.
"""

from __future__ import annotations

import random

import pytest

from symbolic_ai_core.reader import LearnedSpanReader, ReadResult, supervise
from symbolic_ai_core.reader.learned import Lexicon, segment, shape
from symbolic_ai_core.world import EntityRef

from symbolic_ai_generators import flood, scheduling, solvency
from symbolic_ai_generators.flood.surface import render_observation as f_obs
from symbolic_ai_generators.scheduling.surface import (
    render_observation as sc_obs)
from symbolic_ai_generators.solvency.surface import render_observation as s_obs

from scripts.learned_reader import canonical, key, prf
from scripts.reader_survives import _remap, mapping_for

DOMAINS = {
    "flood": (flood.generate, lambda c: f_obs(c, variants=4,
                                              hard_distractors=True)),
    "solvency": (solvency.generate, lambda c: s_obs(c, variants=4,
                                                    hard_distractors=True)),
    "scheduling": (scheduling.generate, lambda c: sc_obs(c, variants=4,
                                                         hard_distractors=True)),
}


def corpus(name, seeds, *, rename=False, rng_seed=0):
    gen, obs = DOMAINS[name]
    rng = random.Random(rng_seed)
    out = []
    for s in seeds:
        c = gen(s)
        if rename:
            c = _remap(c, mapping_for(c.world, rng))
        out.append((c, obs(c)))
    return out


def fit(data):
    return LearnedSpanReader().fit(
        [supervise(o.text, o.spans, c.world.claims) for c, o in data])


def f1_on(reader, data):
    return sum(prf({key(x) for x in canonical(c.world.claims, o.text)},
                   {key(x) for x in canonical(reader.run(o.text).delta().claims,
                                              o.text)})[2]
               for c, o in data) / len(data)


def test_a_full_stop_inside_a_decimal_does_not_end_a_sentence():
    text = "group reported 184.19 USD, filed 2026-05-02. sub_0 sits inside it."
    assert len(segment(text)) == 2


def test_shape_collapses_runs_so_an_unseen_index_has_a_seen_shape():
    assert shape("region_0") == shape("region_1284") == "a_9"
    assert shape("2026-05-02") == "date"


@pytest.mark.parametrize("name", sorted(DOMAINS))
def test_the_learned_reader_recovers_the_world_it_was_fitted_on(name):
    """No domain lexicon in the source, and the claims come back exactly."""
    train = corpus(name, range(60))
    held = corpus(name, range(1_000_000, 1_000_006))
    assert f1_on(fit(train), held) > 0.98


@pytest.mark.parametrize("name", sorted(DOMAINS))
def test_renaming_destroys_a_reader_fitted_on_one_vocabulary(name):
    """The control that must fail, and does.

    Every entity in the held-out documents is renamed to a form the fit never
    saw. A reader whose F1 survived this would be reading; one that collapses
    memorised the vocabulary -- which is what a fit on a corpus with ten distinct
    names does, and why the augmented fit below exists.
    """
    train = corpus(name, range(60))
    renamed = corpus(name, range(1_000_000, 1_000_006), rename=True, rng_seed=7)
    assert f1_on(fit(train), renamed) < 0.1


@pytest.mark.parametrize("name", sorted(DOMAINS))
def test_renaming_in_training_buys_renaming_at_test_time(name):
    """One augmentation, and the shape becomes productive rather than the form.

    This is the whole cost of identity generalisation here: nothing else in the
    reader keys on which name a name is.
    """
    train = corpus(name, range(60)) + corpus(name, range(60), rename=True,
                                             rng_seed=1)
    renamed = corpus(name, range(1_000_000, 1_000_006), rename=True, rng_seed=7)
    reader = fit(train)
    assert "a_9" in reader.lex.productive
    assert f1_on(reader, renamed) > 0.9


def test_an_unnamed_entity_is_minted_from_the_company_it_keeps():
    """flood's bridges appear in no sentence; two sentences must agree on one.

    `bridge_on` introduces the crossing and `load_limit` rates it, in different
    paragraphs, and neither writes an id. The reading is only usable if both
    mint the SAME identity from the regions they name.
    """
    reader = fit(corpus("flood", range(60)))
    c, o = corpus("flood", [1_000_000])[0]
    claims = reader.run(o.text).delta().claims
    vias = {v.roles["via"].id for v in claims if v.predicate == "bridge_on"}
    ofs = {v.roles["of"].id for v in claims if v.predicate == "load_limit"}
    assert vias and ofs <= vias
    assert all(x.startswith("~") for x in vias)


def test_an_unfitted_reader_refuses_rather_than_reading_nothing():
    with pytest.raises(RuntimeError, match="not been fitted"):
        LearnedSpanReader().run("group owns sub_0 outright.")


def test_a_reading_is_a_read_result_with_its_alignments():
    reader = fit(corpus("solvency", range(40)))
    c, o = corpus("solvency", [1_000_000])[0]
    res = reader.run(o.text)
    assert isinstance(res, ReadResult)
    assert len(res.alignments) == len(res.claims)
    for a in res.alignments:
        assert o.text[a.start:a.end].strip()
    assert res.mentions and all(m.entities for m in res.mentions)
    assert res.cost_s > 0


def test_a_common_word_does_not_become_an_entity_by_sharing_a_shape():
    """Productivity needs many distinct fillers AND near-purity.

    Without the purity test every English word would be an entity the moment one
    entity happened to be spelled like one.
    """
    lex = Lexicon(forms={"group"}, productive={"a_9"})
    from symbolic_ai_core.reader.learned import tokenize
    toks = {t.text: t for t in tokenize("the group owns sub_4 outright")}
    assert lex.is_entity(toks["group"])
    assert lex.is_entity(toks["sub_4"])
    assert not lex.is_entity(toks["owns"])


def test_sensitivity_weights_scale_the_update_and_change_the_fit():
    """The weighted objective is wired to the classifier, not decoration.

    It is not asserted to be BETTER -- it measurably is not, see
    `notes/findings/2026-08-19-the-sensitivity-weighted-objective-over-predicts-
    exactly-the-claims-it-protects.md`. What is asserted is that the weights
    reach the fit at all, so the negative result is about the idea rather than
    about a weight that was silently ignored.
    """
    data = corpus("flood", range(6))
    docs = [supervise(o.text, o.spans, c.world.claims) for c, o in data]
    flat = LearnedSpanReader().fit(docs)
    tilted = LearnedSpanReader(weights={"needs": 8.0, "link": 0.1}).fit(docs)
    assert flat.clf.w != tilted.clf.w


def test_an_absent_weight_is_one_and_none_is_the_mean():
    r = LearnedSpanReader(weights={"a": 2.0, "b": 4.0})
    from symbolic_ai_core.reader.learned import NONE
    assert r._weight("a") == 2.0
    assert r._weight("zzz") == 1.0
    assert r._weight(NONE) == 3.0
    assert LearnedSpanReader()._weight("anything") == 1.0


def test_reading_sentence_by_sentence_with_context_equals_reading_the_whole():
    """The persistent-world property: ingest incrementally, get the same world.

    Without context the pronoun sentences lose their antecedent and the claims
    they carry are dropped; with it, the two readings are claim-for-claim
    identical. Earlier text contributes MENTIONS only -- never claims -- which is
    what makes the cheap arm cheap.
    """
    from symbolic_ai_core.reader.learned import segment
    reader = fit(corpus("flood", range(60)))
    c, o = corpus("flood", [1_000_000])[0]
    whole = {key(x) for x in canonical(reader.run(o.text).delta().claims, o.text)}
    sents = [o.text[a:b] for a, b in segment(o.text)]

    blind, ctxd = [], []
    for i, s in enumerate(sents):
        blind.extend(reader.run(s).delta().claims)
        ctxd.extend(reader.run(s, context=tuple(sents[:i])).delta().claims)
    assert {key(x) for x in canonical(tuple(ctxd), o.text)} == whole
    assert {key(x) for x in canonical(tuple(blind), o.text)} != whole
