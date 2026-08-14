"""Every package that exists is on the mainline, tracked, and importable.

This test exists because none of that was true. `symbolic_ai_agents` -- 29
modules, four test files, an entire half of the repo -- was never committed to
`master`. It lived only on an unmerged branch whose tip commit read "Preserve the
symbolic_ai_agents package found uncommitted on this branch", while `master` ran
94 commits without it and nothing indicated anything was missing. The README
described a repo that did not include it, and the suite passed.

That is the quietest form of the failure `CLAUDE.md`'s merge rule was written
for: not a conflict resolving the wrong way, but work parked "for now" and never
merged. Three sibling failures the same day -- a tokenizer silently deleting
underscores, `runs/` discarding every number the docs cite, a floor compared
against a differently-fitted copy of itself -- share the shape: **something was
true of the repo that no test and no document would have surfaced.**

So: assert the inventory itself.
"""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

#: A directory here is a package if it has an `__init__.py`. Anything matching
#: `symbolic_ai_*` is ours and must be on the mainline.
PACKAGES = sorted(
    p.name for p in ROOT.iterdir()
    if p.is_dir() and p.name.startswith("symbolic_ai_") and (p / "__init__.py").exists()
)


def test_there_are_packages_to_check():
    """A glob that silently matches nothing would make every test below pass."""
    assert len(PACKAGES) >= 4, f"expected the repo's packages, found {PACKAGES}"


@pytest.mark.parametrize("name", PACKAGES)
def test_every_package_is_tracked_by_git(name):
    """On disk is not the same as committed. `symbolic_ai_agents` was on disk as
    stale `__pycache__` directories and had zero tracked files."""
    tracked = subprocess.run(
        ["git", "ls-files", name], cwd=ROOT, capture_output=True, text=True,
    ).stdout.split()
    python_files = [f for f in tracked if f.endswith(".py")]
    assert python_files, (
        f"{name}/ exists but git tracks no .py files in it -- it is not on the "
        f"mainline and would vanish from a fresh clone")


@pytest.mark.parametrize("name", PACKAGES)
def test_every_package_imports(name):
    """A tracked package that cannot be imported is no better than a missing one."""
    importlib.import_module(name)


@pytest.mark.parametrize("name", PACKAGES)
def test_every_package_appears_in_the_readme_layout(name):
    """The README described a five-package repo while listing three.

    Documentation drift is not cosmetic here: the layout block is how someone
    arriving cold learns what exists, and it is what let a missing package go
    unnoticed.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert name in readme, f"{name}/ is not mentioned in README.md"
