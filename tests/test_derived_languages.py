"""Turning the derived languages on must not move the seven shipped packs.

`symbolic_ai_core/data/langdb.py` makes several dozen more languages
renderable. The hazard it is written around is not hypothetical:
`grammar/grammars/vocab.py::Vocabulary.database` gives a *hand-written* pack an
imported vocabulary the moment `LanguageDB.exists()` becomes true, so the
obvious way to install the database — at `store.DB_PATH`, or via the
`LANGCURRICULUM_DB` environment variable it documents — would re-render
English, Spanish, Chinese, Turkish and Swahili and silently re-define every
number in `RESEARCH_LOG.md`.

`tests/test_curriculum_fingerprint.py` would catch that, but only on a machine
where the cache happens to exist. These tests catch it everywhere the database
is available, and skip cleanly where it is not.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.data import curriculum as C
from symbolic_ai_core.data import fingerprint as F
from symbolic_ai_core.data import langdb

pytestmark = pytest.mark.skipif(
    langdb.ensure() is None,
    reason="no language database on this machine; the derived path is inert")

#: A handful of lessons, not all 179: this file is about whether *enabling*
#: moves the shipped packs, and the full grid is already drawn by
#: `test_curriculum_fingerprint.py`. Chosen by sorted order rather than picked,
#: so nobody can have chosen the ones that agree.
_LESSONS = sorted(C.lesson_ids())[:12]


def _shipped_digest():
    import symbolic_ai_data as lc
    return F.curriculum_fingerprint(lessons=_LESSONS,
                                    languages=sorted(lc.language_codes()))


def test_the_shipped_packs_render_identically_once_derived_is_enabled():
    """The invariant. Same twelve lessons, before and after."""
    before = _shipped_digest()
    codes = langdb.enable()
    assert codes, "the database is present but no codes came out of it"
    after = _shipped_digest()
    assert F.compare(before, after) == []
    assert before["global"] == after["global"]


def test_enabling_does_not_install_the_database_where_the_packs_look():
    """The mechanism, pinned separately from its consequence.

    A future edit that "simplifies" `enable` into setting `LANGCURRICULUM_DB`
    would still pass the digest test on a machine whose hand-written packs
    happen to have every word they need. This asserts the thing that actually
    keeps them apart.
    """
    from symbolic_ai_data.grammar.grammars import GRAMMARS
    from symbolic_ai_data.grammar.store import DB_PATH

    langdb.enable()
    assert not DB_PATH.exists(), (
        f"{DB_PATH} exists, so Vocabulary.database will import words into the "
        f"hand-written packs and the fingerprint is no longer a constant")
    for code, grammar in GRAMMARS.items():
        vocab = getattr(grammar, "lexicon", None) or getattr(grammar, "vocab", None)
        if vocab is not None and hasattr(vocab, "database"):
            assert vocab.database is None, f"{code} picked up a database"


def test_the_registry_gained_languages_and_the_declaration_did_not():
    """`language_codes()` is what the fingerprint grid iterates.

    Derived languages are cached in `symbolic_ai_data.languages._DERIVED` and
    must never reach `LANGUAGES`; if they did, the grid would widen and the
    global digest would move for a reason that has nothing to do with
    generation.
    """
    import symbolic_ai_data as lc

    before = list(lc.language_codes())
    codes = langdb.enable()
    assert len(codes) > 40
    C.generate(["symbol_grounding"], n=1, seed0=0, language="fra")
    list(C.generate(["symbol_grounding"], n=1, seed0=0, language="fra"))
    assert list(lc.language_codes()) == before


def test_a_derived_language_actually_renders_in_its_own_script():
    """Cheap smoke test with teeth: a Japanese episode has to contain kana or
    kanji, or the "42 languages" claim is 42 copies of English."""
    langdb.enable()
    jpn = list(C.generate(["symbol_grounding"], n=1, seed0=0, language="jpn"))[0]
    assert any("぀" <= ch <= "ヿ" or "一" <= ch <= "鿿"
               for ch in jpn.prompt)
    heb = list(C.generate(["symbol_grounding"], n=1, seed0=0, language="heb"))[0]
    assert any("֐" <= ch <= "׿" for ch in heb.prompt)


def test_the_oracle_tables_are_the_ones_the_analysis_expects():
    """The correlations rest on these columns existing and being populated."""
    rows = langdb.language_rows()
    typ = langdb.typology_rows()
    assert len(rows) >= 58
    coded = [c for c, t in typ.items() if t]
    assert len(coded) >= 46, f"only {len(coded)} languages carry WALS features"
    for code in ("fra", "jpn", "heb"):
        assert rows[code]["family"] and rows[code]["macroarea"]
        assert rows[code]["script"]
    # The split the whole reading depends on: features the renderer consumes
    # versus features it never sees. Both halves must be non-empty in the data.
    read = {p for t in typ.values() for p in t if p in langdb.RENDERED_WALS_FEATURES}
    held = {p for t in typ.values() for p in t if p in langdb.HELDOUT_WALS_FEATURES}
    assert len(read) >= 10 and len(held) >= 4
