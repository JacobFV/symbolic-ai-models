"""``symbolic_ai_data`` is upstream's code, and these tests keep it that way.

The fingerprint in ``test_curriculum_fingerprint.py`` catches a change that
moves the corpus. These catch the changes that *would* move it and the ones that
would make the vendoring rot — a renamed format constant, an import back up into
the models, a public name the seam depends on quietly disappearing.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import symbolic_ai_data as D
from symbolic_ai_data import _vendor

PKG = Path(D.__file__).resolve().parent


def _python_files(upstream_only: bool = False):
    """Every module here. ``upstream_only`` drops the ones written in this repo
    — currently just ``_vendor.py``, whose docstring explains the omissions and
    therefore names them."""
    out = [p for p in PKG.rglob("*.py") if "__pycache__" not in p.parts]
    if upstream_only:
        added = {PKG / a for a in _vendor.ADDED}
        out = [p for p in out if p not in added]
    return sorted(out)


def test_the_domain_separation_constant_was_not_renamed():
    """The trap this vendoring was one ``sed`` away from walking into.

    ``SPACE_KEY`` contains the upstream package name and is *not* a package
    name: it domain-separates the Feistel permutation behind ``draw`` and
    ``batch``, so substituting it reshuffles every batch index while looking
    like a tidy-up in review. Every internal import here is relative, so no
    rename was needed anywhere and none was done.
    """
    from symbolic_ai_data.address import SPACE_KEY
    assert SPACE_KEY == b"langcurriculum/address/v1"


def test_no_file_here_imports_anything_from_this_repo():
    """The data package is the bottom of the stack. Read the import statements
    rather than the runtime module graph, for the reason ``test_layering.py``
    gives: importing the top-level package pulls in everything and would measure
    the convenience surface instead of the layering."""
    ours = {"symbolic_ai_models", "symbolic_ai_parsers", "symbolic_ai_agents"}
    offenders = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for n in names:
                if n.split(".")[0] in ours:
                    offenders.append(f"{path.relative_to(PKG)}: {n}")
    assert not offenders, offenders


def test_the_omitted_files_are_genuinely_unread():
    """22 MB of the 26 MB upstream package was left behind. That is only safe if
    nothing reads it — which was checked by grep before the copy and is checked
    here after it, because the risk is that a later upstream sync brings in code
    that does."""
    for path in _python_files(upstream_only=True):
        src = path.read_text(encoding="utf-8")
        assert "gzip" not in src, f"{path.relative_to(PKG)} may want the omitted .db.gz"
        assert ".db.gz" not in src, f"{path.relative_to(PKG)} names the omitted archive"

    from symbolic_ai_data.grammar.store import LanguageDB
    assert not LanguageDB().exists(), (
        "a language database appeared. The published corpus was generated with "
        "none, so the several-hundred-language derived-grammar path was inert; "
        "if it is live now, the corpus is not the one that was measured.")


def test_the_seam_only_needs_names_that_are_actually_exported():
    """Everything ``symbolic_ai_models.data.curriculum`` reaches for through
    ``_lc()``. A missing one is an ``AttributeError`` in the middle of a sweep
    rather than at import."""
    for name in ("lesson_ids", "get", "by_tag", "by_capability", "curriculum",
                 "curriculum_ids", "language_codes"):
        assert callable(getattr(D, name)), name
    assert D.__version__ == _vendor.VERSION


@pytest.mark.parametrize("attr", ["SOURCE", "COMMIT", "OMITTED", "ADDED"])
def test_provenance_is_recorded(attr):
    assert getattr(_vendor, attr)
