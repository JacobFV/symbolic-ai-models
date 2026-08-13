"""Where this package came from, and the one rule for changing it.

``symbolic_ai_data`` is a **verbatim** vendored copy of ``langcurriculum`` — the
same files the git dependency installed, byte for byte, with two deliberate
differences recorded in :data:`OMITTED` and :data:`ADDED`. It is the only module
in this package that was written here; every other file is upstream's.

Why verbatim, and not renamed
-----------------------------

The obvious tidying — rewrite ``langcurriculum`` to ``symbolic_ai_data``
throughout — would have silently rewritten the corpus. Every internal import is
already relative, so nothing *needed* renaming, and one of the few places the
old name appears in code is::

    SPACE_KEY = b"langcurriculum/address/v1"     # address.py

which domain-separates the Feistel permutation behind ``draw`` and ``batch``.
Substituting the package name there reshuffles every batch index. The string is
a format constant that happens to contain a package name, and a rename would
have looked like a no-op in review.

So: no substitution was performed anywhere, and none should be. If this package
is ever renamed at the import level, the constants stay as they are.

The rule for changing it
------------------------

Vendoring means the generator can now be modified, and the repo's convention for
models applies to lessons and render modes with more force, because editing a
model in place invalidates one row and editing the generator in place
invalidates every row at once. ``symbolic_ai_core/data/fingerprint.py`` holds
a checksum of the corpus and ``tests/test_curriculum_fingerprint.py`` fails if
it moves.

Anything that varies surface realization — to attack the long-range templating
regularity ``asymptotics.py`` measures — goes in as a **new lesson or a new
presentation registered beside the existing one**, never as an edit to how an
existing lesson generates. :class:`~symbolic_ai_data.presentation.Presentation`
is already the seam for this: it carries ``language``, ``answer_format`` and
``surface``, it is part of an episode's address via ``Presentation.key()``, and
a new value there is a new address rather than a new rendering of an old one.
The fingerprint pins the default presentation only, which is exactly the set of
episodes the published numbers were drawn from.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["SOURCE", "VERSION", "COMMIT", "HEAD_AT_VENDORING", "OMITTED",
           "ADDED", "ROOT"]

ROOT = Path(__file__).resolve().parent

SOURCE = "https://github.com/JacobFV/formal-language-cirriculum"
VERSION = "0.2.0"

#: The commit ``uv.lock`` pinned, and therefore the one every number in
#: ``RESEARCH_LOG.md``, ``README.md`` and ``runs/*`` was generated from.
COMMIT = "504e1182e179bb82f159289e2a186d906e97af4d"

#: Upstream's ``master`` when this was vendored. Recorded because it is *not*
#: the pinned commit — and because the ``langcurriculum/`` directory is
#: byte-identical between the two, so the difference is only in the website and
#: the README and nothing about the corpus turns on which one was copied.
HEAD_AT_VENDORING = "ba8acd62f63f72b74ca5d9cb495a048161c85906"

#: Not copied. ``site-languages.db.gz`` is 22 MB — 92% of the upstream package —
#: and is a build artefact for the project's website: no Python in the package
#: reads it, decompresses it, or mentions ``gzip`` at all. Its uncompressed form
#: ``grammar/data/languages.db`` was likewise absent from the installed
#: dependency, so ``LanguageDB.exists()`` was already ``False`` and the
#: several-hundred-language derived grammar path was already inert. The seven
#: hand-written packs are what rendered every published episode, and they are
#: here. Omitting these files is what keeps the fingerprint honest *and* the
#: repo small; had either been read at generation time, the fingerprint would
#: have said so.
OMITTED = ("grammar/data/site-languages.db.gz", "grammar/data/languages.db")

#: Written here rather than upstream.
ADDED = ("_vendor.py", "LICENSE")
