"""The multilingual parser family, tested as claims rather than as coverage.

Same rule as ``test_graph_parsers.py``: every assertion is a *relation* — this
splitter separates what that one runs together, this arm transfers where that
arm cannot, this conditioning backs off exactly — and never a measured constant.
A number measured on the fixture below would be a number measured on six
lessons, and this repo has eight recorded instances of a small slice producing a
confident wrong reading. ``scripts/polyglot_lolo.py`` measures; this file checks
that the machinery does what its docstrings say.

The parts that need several *languages* need the derived language database, so
they skip cleanly where it is absent, exactly as ``test_derived_languages.py``
does.
"""

from __future__ import annotations

import math

import pytest

from symbolic_ai_core.data import langdb
from symbolic_ai_core.data.curriculum import generate, resolve_lessons
from symbolic_ai_core.data.tokenizer import split_words
from symbolic_ai_parsers import build, parser_names
from symbolic_ai_parsers.classes import GENERIC, ClassMap
from symbolic_ai_parsers.features import words_of
from symbolic_ai_parsers.segment import words as words_v2
from symbolic_ai_parsers.treebank import Treebank, segments

ARMS = ("polycky-001", "polycky-002", "polycky-crc", "polycky-1class",
        "polycky-literal", "polycky-v1seg", "polycky-hapax")

HAVE_DB = langdb.ensure() is not None
needs_db = pytest.mark.skipif(HAVE_DB is False,
                              reason="no language database; derived path inert")

LESSONS = resolve_lessons(None)[:6]
#: Four scripts, deliberately: one spaceless (Han), one with combining marks
#: that Python does not count as word characters (Tamil), one Latin that
#: reorders (Turkish), and English.
TRAIN_LANGS = ("english", "cmn", "tur", "tam")


@pytest.fixture(scope="module")
def multi():
    if not HAVE_DB:
        pytest.skip("no language database")
    langdb.enable()
    out = []
    for lang in TRAIN_LANGS:
        out.extend(generate(list(LESSONS), n=3, seed0=0, language=lang,
                            max_nodes=128))
    return out


# ---- the splitter, which is the substrate and not the model ---------------

def test_the_shared_splitter_runs_a_latin_argument_into_the_ideographs():
    """The bug the second splitter exists for, pinned as a property of the
    *old* one so that the claim is about the substrate rather than about a
    parser's score."""
    assert "alice和面包" in split_words("alice和面包")
    assert "alice" not in split_words("alice和面包")


def test_the_script_aware_splitter_separates_it():
    got = words_v2("alice和面包")
    assert "alice" in got
    assert all(len(t) == 1 for t in got[1:])


def test_the_script_aware_splitter_keeps_combining_marks_on_their_letter():
    """Tamil vowel signs are category ``Mn``, which is not ``\\w``, so the
    shared splitter shatters every Tamil word into graphemes."""
    word = "நிகழ்ச்சி"
    assert len(split_words(word)) > 1
    assert words_v2(word) == [word]


def test_the_default_segmentation_is_untouched():
    """``segments`` grew a parameter. Every parser that did not ask for the new
    splitter must segment exactly as it did, or this change silently redefines
    ``cky-001``."""
    text = "Facts: alice outranks bob; bob outranks dave.\n  - dave is a person"
    assert segments(text) == segments(text, words_of)
    assert segments(text) != segments(text, words_v2) or "和" not in text


# ---- the induced classes --------------------------------------------------

@needs_db
def test_two_languages_frame_words_land_in_one_class(multi):
    """The whole point of the abstraction: ``outranks`` and its translation are
    one symbol, so one production covers both languages."""
    tb = Treebank.build(multi, words_v2)
    cmap = ClassMap.induce(tb.samples, tb.languages)
    per_head: dict[str, set[str]] = {}
    for tok, sym in cmap.of.items():
        if sym.startswith("C:"):
            per_head.setdefault(sym, set()).add(tok)
    merged = [s for s, toks in per_head.items()
              if s != GENERIC and len(toks) > 1]
    assert merged, "no class merged two surface forms at all"


@needs_db
def test_punctuation_stays_literal_and_translated_words_do_not(multi):
    """The two tiers have to actually separate, or the parser has either
    abstracted its one reliable anchor or abstracted nothing."""
    tb = Treebank.build(multi, words_v2)
    cmap = ClassMap.induce(tb.samples, tb.languages)
    for mark in (":", ",", ";"):
        if mark in cmap.of:
            assert cmap.of[mark] == mark, mark
    assert cmap.n_classes() > 0
    assert cmap.n_literal() > 0


@needs_db
def test_the_one_class_control_keeps_the_tiers_but_loses_the_identities(multi):
    """Otherwise it is not a control for class *identity*, it is a control for
    abstraction, and ``polycky-literal`` is already that."""
    tb = Treebank.build(multi, words_v2)
    full = ClassMap.induce(tb.samples, tb.languages)
    one = ClassMap.induce(tb.samples, tb.languages, mode="one")
    assert one.n_classes() == 1
    assert full.n_classes() > 1
    assert one.n_literal() == full.n_literal()


def test_a_monolingual_fit_abstracts_nothing():
    """With one language there is no evidence about what survives translation,
    so every token is 'shared'. The family must degrade to a literal grammar
    rather than inventing classes out of a single rendering."""
    eps = list(generate(list(LESSONS), n=3, seed0=0, max_nodes=128))
    tb = Treebank.build(eps, words_v2)
    cmap = ClassMap.induce(tb.samples, tb.languages)
    assert cmap.n_classes() == 0


# ---- conditioning ---------------------------------------------------------

@needs_db
def test_an_unseen_condition_scores_exactly_the_global_rule_set(multi):
    """The property that makes leave-one-language-out need no special case. If
    it ever stops holding, every held-out number is measuring a backoff bug."""
    p = build("polycky-002")
    p.fit(multi)
    g = p.grammar
    assert g.cond_logp, "nothing was conditioned at all"
    for i in range(min(len(g.rules), 40)):
        assert g.rule_logp(i, "no-such-language") == g.logp[i]
        assert g.rule_logp(i, None) == g.logp[i]


@needs_db
def test_the_nonsense_split_has_the_same_cardinality_as_the_languages(multi):
    """A control that split the data into a different number of buckets would
    be measuring bucket size, which is the thing it is meant to hold fixed."""
    lang = build("polycky-002")
    crc = build("polycky-crc")
    lang.fit(multi)
    crc.fit(multi)
    assert len(crc.grammar.cond_logp) == len(lang.grammar.cond_logp)
    assert len(lang.grammar.cond_logp) == len(TRAIN_LANGS)


@needs_db
def test_conditioning_reads_metadata_and_never_the_graph(multi):
    """``parse_episode`` is handed an ``Episode``, which carries the answer. It
    must use the language and the instance id and nothing else."""
    import dataclasses

    from symbolic_ai_core.data.graph import Graph

    p = build("polycky-002")
    p.fit(multi)
    ep = multi[0]
    blanked = dataclasses.replace(ep, graph=Graph(), answer="", choices=[])
    assert p.parse_episode(ep).to_dict() == p.parse_episode(blanked).to_dict()


# ---- the out-of-vocabulary rate, which is a harness constant --------------

@needs_db
def test_the_unseen_argument_rate_is_lower_for_a_language_never_seen(multi):
    """``cky-001`` estimates ~0.9 from hapaxes, which is right for a
    monolingual corpus of nonce symbols and wrong for a new language, where an
    unseen token is usually that language's frame vocabulary. The two estimates
    must at least order that way, or the correction is not a correction."""
    p = build("polycky-001")
    p.fit(multi)
    assert 0.0 < p.grammar.oov_novel <= p.grammar.oov_known <= 1.0


@needs_db
def test_the_hapax_estimator_inverts_on_a_parallel_corpus(multi):
    """The old estimator does not merely stay put under a mixture — it flips.

    ``Grammar._fit_lexicon`` reads the argument rate among training hapaxes,
    which works monolingually because a token seen once is a nonce symbol and
    nonce symbols are arguments. On a *parallel* corpus the reasoning inverts:
    an argument is copied verbatim into all 46 renderings, so it is never a
    hapax, while a rare translated frame word is one in exactly one language.
    The old estimate therefore comes out near zero and the arm calls every
    unseen token frame material.

    Asserted as a relation — one constant, no case split, and far from the
    held-out estimate — so that this stays a fact about the two estimators
    rather than a number measured on six lessons.
    """
    new, old = build("polycky-001"), build("polycky-hapax")
    new.fit(multi)
    old.fit(multi)
    assert old.grammar.oov_known == old.grammar.oov_novel
    assert abs(old.grammar.oov_known - new.grammar.oov_known) > 0.1


# ---- transfer, which is the claim -----------------------------------------

@needs_db
def test_only_the_abstracted_grammar_can_derive_a_clause_in_a_new_language(multi):
    """The mechanism the whole family rests on, isolated from the score.

    A clause whose frame words are all unseen has nothing for a literal grammar
    to match; the class grammar can still match it through the wildcard. If this
    ever fails, the held-out-language numbers are coming from somewhere else and
    the write-up is wrong about why.
    """
    langdb.enable()
    held = list(generate(list(LESSONS), n=1, seed0=0, language="tha",
                         max_nodes=128))
    abstracted, literal = build("polycky-001"), build("polycky-literal")
    abstracted.fit(multi)
    literal.fit(multi)
    a = sum(len(abstracted.parse(ep.prompt)) for ep in held)
    b = sum(len(literal.parse(ep.prompt)) for ep in held)
    assert a > b, (a, b)


# ---- the protocol ---------------------------------------------------------

@needs_db
def test_the_wide_arm_really_widens_the_wildcard_search(multi):
    """``polycky-wide`` exists to try to break the one-class result, so the
    thing it changes has to actually change. The beam caps how many class
    symbols an unknown token is tried as at one trie state; widening it can only
    add candidates, never remove them."""
    narrow, wide = build("polycky-001"), build("polycky-wide")
    narrow.fit(multi)
    wide.fit(multi)
    assert wide.grammar.beam > narrow.grammar.beam

    def widest(g):
        return max((len(n.wild) for n in g._walk(g.root)), default=0)

    assert widest(wide.grammar) >= widest(narrow.grammar)


@needs_db
def test_the_folds_hold_every_language_out_exactly_once():
    from symbolic_ai_parsers.polyglot import WALS46, folds

    fs = folds()
    flat = [c for f in fs for c in f]
    assert sorted(flat) == sorted(WALS46)
    assert len(flat) == len(set(flat))


@needs_db
def test_the_folds_are_stratified_by_script():
    """Twelve of the 46 are the only language in the corpus written in their
    script. Dealt into one fold, that fold would be a novel-script result and
    the other five would be a Latin one."""
    from symbolic_ai_parsers.polyglot import WALS46, folds, scripts

    sc = scripts(WALS46)
    rare = [sum(1 for c in f if sc[c] != "Latn") for f in folds()]
    assert max(rare) - min(rare) <= 1, rare


def test_the_floor_must_not_be_fitted_on_the_multilingual_mixture():
    """Pinned as a hazard rather than described in a comment.

    The graph is identical in every language, so a 46-language training set
    holds each graph 46 times and the floor's disjoint candidate/target halves
    would contain *the same graph*. The floor would be handed a free exact match
    and every lift quoted above it would be wrong in the flattering direction.
    """
    if not HAVE_DB:
        pytest.skip("no language database")
    langdb.enable()
    from symbolic_ai_parsers.floors import fit_floor

    mono = list(generate(list(LESSONS), n=4, seed0=0, max_nodes=128))
    multi_ = mono + list(generate(list(LESSONS), n=4, seed0=0, language="cmn",
                                  max_nodes=128))
    ev = list(generate(list(LESSONS), n=2, seed0=1_000_000, max_nodes=128))
    a = fit_floor(mono, n_candidates=32, n_targets=32).evaluate(ev)
    b = fit_floor(multi_, n_candidates=32, n_targets=32).evaluate(ev)
    assert math.isfinite(a["bracket_f1"]) and math.isfinite(b["bracket_f1"])
    assert b["exact"] >= a["exact"]


# ---- registration ---------------------------------------------------------

def test_every_arm_is_registered_and_the_bare_name_is_the_parser():
    from symbolic_ai_parsers import get

    assert set(ARMS) <= set(parser_names())
    assert get("polycky").name == "polycky-002"
    assert get("polycky").name not in ("polycky-crc", "polycky-1class",
                                       "polycky-literal", "polycky-v1seg",
                                       "polycky-hapax")
