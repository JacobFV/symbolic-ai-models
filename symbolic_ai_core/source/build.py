"""Compile the hand-authored YAML into one canonical JSON index.

``generated/catalog.json`` is the machine-readable form: every source card,
snapshot manifest and artifact manifest in one document, with a digest over the
canonical serialisation. It exists so that a consumer that is not Python — a
TypeScript canvas, a static site, a sibling project's loader — reads one file
instead of walking a directory of YAML and reimplementing the merge.

It is **generated and never edited**. ``tests/test_source_catalog.py`` rebuilds
it and compares digests, so a hand edit fails rather than surviving as a second,
divergent catalogue.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .license import license_closure
from .manifest import canonical_json
from .registry import SourceRegistry, repo_root

__all__ = ["build_catalog", "write_catalog", "catalog_path"]


def catalog_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / "generated" / "catalog.json"


def build_catalog(root: Path | None = None) -> dict[str, Any]:
    reg = SourceRegistry(root)
    sources = reg.sources()
    snapshots = reg.snapshots()
    artifacts = reg.artifacts()

    doc: dict[str, Any] = {
        "schema": "sai.catalog@1",
        "vocab": _vocab_digest(root),
        "sources": {sid: dict(s.raw) for sid, s in sorted(sources.items())},
        "snapshots": {k: dict(v.raw) for k, v in sorted(snapshots.items())},
        "artifacts": {k: dict(v.raw) for k, v in sorted(artifacts.items())},
    }
    # The lineage index: which snapshots and artifacts descend from which
    # source, precomputed so a consumer does not have to parse refs to answer
    # "which licences attach to this number".
    lineage: dict[str, list[str]] = {}
    for sid, snap in snapshots.items():
        lineage.setdefault(f"source/{snap.source}", []).append(f"snapshot/{sid}")
    for aid, art in artifacts.items():
        for parent in art.parents:
            lineage.setdefault(parent, []).append(f"artifact/{aid}")
    doc["lineage"] = {k: sorted(v) for k, v in sorted(lineage.items())}
    doc["closures"] = {
        f"artifact/{aid}": license_closure(
            [dict(sources[snapshots[p.split('/', 1)[1]].source].license)
             for p in art.parents if p.startswith("snapshot/")
             and p.split("/", 1)[1] in snapshots])
        for aid, art in sorted(artifacts.items())}
    doc["digest"] = "sha256:" + hashlib.sha256(
        canonical_json({k: v for k, v in doc.items()})).hexdigest()
    return doc


def _vocab_digest(root: Path | None = None) -> str:
    from .validate import vocab
    return "sha256:" + hashlib.sha256(canonical_json(vocab(root))).hexdigest()


def write_catalog(root: Path | None = None) -> Path:
    doc = build_catalog(root)
    p = catalog_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False)
                 + "\n", encoding="utf-8")
    return p
