"""The dependency direction, asserted rather than hoped for.

`symbolic_ai_data` -> `symbolic_ai_core` -> {`symbolic_ai_models`,
`symbolic_ai_parsers`}, and inside the models package `parsers.primitives` ->
`parsers` -> `models`, one way. It was not always so: the parsing primitives
arrived welded to the models that first used them, so `parsers` imported
`models` for the clause splitter and the syllogism fragment while `models`
imported `parsers` for its parser. That is a cycle, and it survived only because
the model-side import was function-local — exactly the arrangement that works
until someone tidies it.

The checks here are **static**, over the import statements themselves. A runtime
probe does not work and it is worth saying why: the top-level
`symbolic_ai_models/__init__.py` is a convenience surface that imports
everything, so importing any submodule initialises the parent and loads `models`
whatever the parsers do. That measures the convenience package, not the layering.
Reading the imports measures the layering.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

#: These subprocesses only need the import graph, never the GPU. Initialising
#: CUDA in several of them at once made the suite flaky under load.
_ENV = {**os.environ, "CUDA_VISIBLE_DEVICES": ""}

ROOT = Path(__file__).resolve().parent.parent
PARSERS = ROOT / "symbolic_ai_models" / "parsers"
CORE = ROOT / "symbolic_ai_core"


def _imported_modules(path: Path) -> set[str]:
    """Every module named by an import in one file, relative imports resolved."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package = path.relative_to(PARSERS.parent.parent).with_suffix("").parts[:-1]
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:                       # relative: walk up from here
                base = list(package)[:len(package) - node.level + 1]
                out.add(".".join([*base, node.module or ""]).rstrip("."))
            elif node.module:
                out.add(node.module)
    return out


def test_no_parser_imports_a_model():
    """The rule the primitives were moved to satisfy."""
    offenders: list[str] = []
    for path in sorted(PARSERS.rglob("*.py")):
        for module in _imported_modules(path):
            if module.startswith("symbolic_ai_models.models"):
                offenders.append(f"{path.name} -> {module}")
    assert not offenders, "parsers must not depend on models: " + "; ".join(offenders)


def test_models_may_import_parsers_eagerly():
    """The allowed direction, and the proof the cycle is really gone.

    A function-local import would hide a cycle; a top-level one cannot, so this
    failing is the signal that the layering has regressed.
    """
    out = subprocess.run(
        [sys.executable, "-c",
         "from symbolic_ai_models.models.symbolic import build_parser\n"
         "print(build_parser('none').name)\n"],
        capture_output=True, text=True, timeout=300, env=_ENV)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip() == "none"


def test_every_parser_is_registered():
    from symbolic_ai_models.parsers import parser_names
    for expected in ("none", "induced", "chunker", "regex", "categorical"):
        assert expected in parser_names()


def test_the_core_does_not_import_its_consumers():
    """`symbolic_ai_core` exists so that three packages can share the episode
    types without depending on the models package. That is only true while the
    dependency runs one way, and the tempting regression is a convenience import
    back up into `symbolic_ai_models` — which would re-create exactly the cycle
    the split was for, with an extra package in it.
    """
    consumers = {"symbolic_ai_models", "symbolic_ai_parsers", "symbolic_ai_agents"}
    offenders: list[str] = []
    for path in sorted(CORE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for module in _imported_modules(path):
            if module.split(".")[0] in consumers:
                offenders.append(f"{path.relative_to(CORE)} -> {module}")
    assert not offenders, "core must not depend on its consumers: " + "; ".join(offenders)


def test_the_deprecated_data_paths_still_resolve_to_the_moved_objects():
    """`symbolic_ai_models.data.*` are re-export shims now. They are not
    decoration: `symbolic_ai_agents` on the `omegaclaw` branch imports `Episode`,
    `Graph`, `SymbolTokenizer`, `collate_graph` and friends from the old paths in
    twenty places, and a merge that silently lost them would look green.

    Identity, not equality — a shim that rebound a *copy* of `Graph` would pass
    an equality check and then fail every `isinstance` in the parsers.
    """
    import symbolic_ai_core.data.batch as new_batch
    import symbolic_ai_core.data.curriculum as new_curriculum
    import symbolic_ai_core.data.graph as new_graph
    import symbolic_ai_core.data.tokenizer as new_tokenizer
    import symbolic_ai_models.data.batch as old_batch
    import symbolic_ai_models.data.curriculum as old_curriculum
    import symbolic_ai_models.data.graph as old_graph
    import symbolic_ai_models.data.tokenizer as old_tokenizer

    for old, new in ((old_batch, new_batch), (old_curriculum, new_curriculum),
                     (old_graph, new_graph), (old_tokenizer, new_tokenizer)):
        assert new.__all__, new.__name__
        for name in new.__all__:
            assert getattr(old, name) is getattr(new, name), (
                f"{old.__name__}.{name} is not {new.__name__}.{name}")
