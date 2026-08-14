"""The language database, wired in without disturbing the seven shipped packs.

``symbolic_ai_data`` advertises "over a thousand" derived grammars and shipped
none of them: ``symbolic_ai_data/_vendor.py`` records that
``grammar/data/site-languages.db.gz`` was deliberately not copied, so
``LanguageDB.exists()`` was ``False`` and the whole derived path was inert.
Every published number in this repo therefore used five hand-written natural
languages, one lexical variant of English and one formal notation — which is
why ``notes/findings/2026-08-13-language-conditioning-recovers-typology-not-genealogy.md``
could only report a genealogy result as a rank among twenty triples.

This module turns the derived path on. It exists as a separate file, rather
than as three lines somewhere convenient, because of one hazard.

The hazard: switching it on changes the *other* languages
---------------------------------------------------------

``grammar/grammars/vocab.py::Vocabulary.database`` reads::

    db = LanguageDB()
    self._database = db if db.exists() else None

and a hand-written pack that finds a database **imports vocabulary out of it**
for any curriculum word its own 321-entry vocabulary lacks. So placing the
database at ``store.DB_PATH`` — or setting ``LANGCURRICULUM_DB``, which is the
documented way to move it — would change how English, Spanish, Chinese, Turkish
and Swahili render. Every number in ``RESEARCH_LOG.md`` is measured on episodes
drawn from those packs, and ``tests/test_curriculum_fingerprint.py`` exists
precisely to make that kind of silent re-definition impossible.

So the database is **never** installed at ``DB_PATH``. :func:`enable` hands a
private :class:`LanguageDB` to the grammar registry, which is the only object
that needs one; ``Vocabulary.database`` keeps constructing ``LanguageDB()``
against the default path, keeps finding nothing, and the seven packs render
byte-for-byte what they always did. ``tests/test_derived_languages.py`` asserts
exactly that by re-running the fingerprint with derived languages enabled.

The two dicts in ``symbolic_ai_data/languages/__init__.py`` do the rest of the
work for us: derived languages are cached in ``_DERIVED`` and never enter
``LANGUAGES``, so ``language_codes()`` — which is what the fingerprint grid
iterates — does not grow.

Where the bytes come from
-------------------------

The database is 102 MB uncompressed and 22 MB gzipped, and neither belongs in
git. :func:`ensure` looks for it in a short list of places on this machine,
decompresses if it found the ``.gz``, and caches the result outside the tree
(``~/.cache/symbolic-ai-models/`` by default, ``SYMBOLIC_AI_LANG_DB`` to
override). Nothing here downloads anything: if no source is present the derived
path stays inert, which is the state every published run was made in.
"""

from __future__ import annotations

import gzip
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence

__all__ = ["CACHE", "SOURCES", "ensure", "enable", "available", "is_enabled",
           "connect", "language_rows", "typology_rows",
           "RENDERED_WALS_FEATURES", "HELDOUT_WALS_FEATURES"]

#: Where the usable copy is kept. Outside the repository on purpose: it is 102
#: MB, it is rebuildable from a source archive, and four git worktrees sharing
#: one cache is the point.
CACHE = Path(os.environ.get(
    "SYMBOLIC_AI_LANG_DB",
    Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    / "symbolic-ai-models" / "site-languages.db")).expanduser()

#: Candidate sources, in preference order. A ``.gz`` is decompressed into
#: :data:`CACHE`; a plain ``.db`` is copied. Every entry is a location this
#: database is known to exist in on the machine the work was done on, and the
#: list is data rather than a hard-coded path so that a missing checkout is a
#: skipped test rather than a failure.
SOURCES: tuple[Path, ...] = (
    Path(__file__).resolve().parents[2]
    / "symbolic_ai_data" / "grammar" / "data" / "site-languages.db.gz",
    Path.home() / "Documents" / "formal-language-cirriculum" / ".build"
    / "site-languages.db",
    Path(__file__).resolve().parents[2] / ".venv" / "lib" / "python3.13"
    / "site-packages" / "langcurriculum" / "grammar" / "data"
    / "site-languages.db.gz",
)

#: The WALS features ``symbolic_ai_data/grammar/typology.py::derive_profile``
#: actually consumes. A derived grammar is a deterministic function of these,
#: so recovering them from its prose is a positive control and **not** evidence
#: that anything linguistic was learned. Read off the source of
#: ``derive_profile``, not off its docstring table, which lists 92A as mapped
#: and the function never touches it.
RENDERED_WALS_FEATURES = ("81A", "87A", "88A", "89A", "85A", "86A", "93A",
                          "98A", "30A", "37A", "38A", "55A", "143A", "51A")

#: Present in the database, never read by the renderer. A correlation here can
#: only have arrived through cross-linguistic covariation among WALS features,
#: which is the honest half of the typology test.
HELDOUT_WALS_FEATURES = ("26A", "33A", "49A", "92A")


# ---------------------------------------------------------------------------
# getting the bytes into place
# ---------------------------------------------------------------------------
def _source() -> Path | None:
    for candidate in SOURCES:
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return None


def ensure(*, cache: Path | None = None) -> Path | None:
    """The usable database, materialising it once. ``None`` if no source.

    Idempotent and cheap on the second call: an existing non-empty cache is
    returned without touching a source.
    """
    target = Path(cache) if cache is not None else CACHE
    if target.exists() and target.stat().st_size > 0:
        return target
    src = _source()
    if src is None:
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".partial")
    if src.suffix == ".gz":
        with gzip.open(src, "rb") as fin, tmp.open("wb") as fout:
            shutil.copyfileobj(fin, fout, length=1 << 22)
    else:
        shutil.copyfile(src, tmp)
    tmp.replace(target)
    return target


# ---------------------------------------------------------------------------
# wiring it to the registry, and only to the registry
# ---------------------------------------------------------------------------
_ENABLED: frozenset[str] | None = None


def enable(*, cache: Path | None = None) -> frozenset[str]:
    """Make derived languages resolvable by ISO 639-3 code. Idempotent.

    Returns every code that can now be built. Empty when no database is
    present, which is not an error: it is the state the published runs were
    made in and the state a fresh clone is in.

    **This deliberately does not touch** ``symbolic_ai_data.grammar.store``'s
    ``DB_PATH``. See the module docstring: doing so would re-render the seven
    hand-written packs and invalidate every published number.
    """
    global _ENABLED
    if _ENABLED is not None:
        return _ENABLED
    path = ensure(cache=cache)
    if path is None:
        _ENABLED = frozenset()
        return _ENABLED
    from symbolic_ai_data.grammar.registry import REGISTRY
    from symbolic_ai_data.grammar.store import LanguageDB

    REGISTRY.db = LanguageDB(path)
    REGISTRY._available = None
    _ENABLED = frozenset(REGISTRY.available)
    return _ENABLED


def is_enabled() -> bool:
    return bool(_ENABLED)


def available(*, cache: Path | None = None) -> frozenset[str]:
    """Every code derivable from the database, enabling it if it is not yet."""
    return enable(cache=cache)


def ensure_for(languages: Iterable[str]) -> None:
    """Turn the derived path on iff something asked for a language we lack.

    This is the hook the training harness calls. A run that names only shipped
    packs never reaches :func:`enable`, so it cannot be affected by whether a
    cache happens to be sitting on the machine — which is the failure mode this
    repo calls "a default with a filename".
    """
    import symbolic_ai_data as lc
    from symbolic_ai_data.languages import LANGUAGE_ALIASES

    shipped = set(lc.language_codes()) | set(LANGUAGE_ALIASES)
    if any(code not in shipped for code in languages):
        enable()


# ---------------------------------------------------------------------------
# reading the oracle directly, for analysis rather than for rendering
# ---------------------------------------------------------------------------
def connect(*, cache: Path | None = None) -> sqlite3.Connection:
    """A read-only handle on the database, for the tables the engine ignores.

    ``family``, ``macroarea``, ``glottocode`` and the raw ``typology`` rows are
    never read by ``derive_profile``; they exist here so an analysis can grade
    an induced representation against a structure the generator did not see.
    """
    path = ensure(cache=cache)
    if path is None:
        raise FileNotFoundError(
            "no language database. Looked in:\n  "
            + "\n  ".join(str(p) for p in SOURCES)
            + "\nSet SYMBOLIC_AI_LANG_DB to a copy, or leave it: the derived "
              "path is inert without it and every published run was made that "
              "way.")
    conn = sqlite3.connect(f"file:{path}?immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def language_rows(conn: sqlite3.Connection | None = None) -> dict[str, dict[str, Any]]:
    """``code -> {name, family, macroarea, script, rtl, tier, ...}``."""
    own = conn is None
    conn = conn or connect()
    try:
        return {r["code"]: dict(r) for r in conn.execute("SELECT * FROM language")}
    finally:
        if own:
            conn.close()


def typology_rows(conn: sqlite3.Connection | None = None,
                  params: Sequence[str] | None = None
                  ) -> dict[str, dict[str, str]]:
    """``code -> {WALS parameter: value}``, restricted to ``params`` if given."""
    own = conn is None
    conn = conn or connect()
    try:
        out: dict[str, dict[str, str]] = {}
        for r in conn.execute("SELECT code, param, value FROM typology"):
            if params is not None and r["param"] not in params:
                continue
            out.setdefault(r["code"], {})[r["param"]] = r["value"]
        return out
    finally:
        if own:
            conn.close()
