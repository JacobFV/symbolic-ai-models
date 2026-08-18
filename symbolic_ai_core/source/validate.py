"""Two checks, and they are deliberately separate.

**Structure** is checked against the JSON Schemas in ``ontology/schema/``, using
a real JSON Schema implementation rather than a hand-rolled subset. A
hand-rolled validator is a second definition of the schema, and two allegedly
identical definitions of anything drift — that is the failure the ontology
README exists to name, and writing one here to check the ontology would have
been an unusually direct way to commit it.

**Vocabularies** are checked against ``ontology/vocab.yaml``, and are *not* in
the schemas at all. An ``enum`` copied into six schema files is six copies of a
list that must agree; the vocabulary lives in one file and everything that needs
it — this checker, a generated Python literal, a TypeScript union in a sibling
project — reads that one.

**Typed refs** are checked last: every ``<class>/<id>`` must resolve to
something the registry actually holds. A parent that does not exist is how a
licence closure comes out permissive — it simply skips the parent that would
have restricted it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from .manifest import load_yaml, parse_ref
from .registry import SourceRegistry, repo_root

__all__ = ["vocab", "validate_source", "validate_snapshot", "validate_artifact",
           "validate_all", "ValidationError"]


class ValidationError(ValueError):
    """A manifest that does not conform, named with the field that broke."""


@lru_cache(maxsize=1)
def vocab(root: Path | None = None) -> dict[str, list[str]]:
    return load_yaml((root or repo_root()) / "ontology" / "vocab.yaml")


@lru_cache(maxsize=8)
def _schema(name: str, root: Path | None = None) -> dict[str, Any]:
    import json
    p = (root or repo_root()) / "ontology" / "schema" / f"{name}.schema.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _structure(d: Mapping[str, Any], name: str, where: str) -> list[str]:
    import jsonschema
    v = jsonschema.Draft202012Validator(_schema(name))
    return [f"{where}: {'.'.join(str(p) for p in e.absolute_path) or '<root>'}"
            f" -- {e.message}" for e in sorted(v.iter_errors(dict(d)),
                                               key=lambda e: list(e.absolute_path))]


def _in_vocab(value: str, key: str, where: str, errs: list[str]) -> None:
    allowed = vocab().get(key) or []
    if value not in allowed:
        errs.append(f"{where}: {value!r} is not in ontology/vocab.yaml:{key} "
                    f"({allowed})")


def validate_source(d: Mapping[str, Any], *, where: str = "") -> list[str]:
    where = where or f"source/{d.get('id', '?')}"
    errs = _structure(d, "source", where)
    _in_vocab(str((d.get("access") or {}).get("class", "")), "access_classes",
              f"{where}.access.class", errs)
    _in_vocab(str((d.get("license") or {}).get("redistribution", "")),
              "redistribution", f"{where}.license.redistribution", errs)
    _in_vocab(str(d.get("lifecycle", "")), "lifecycles", f"{where}.lifecycle",
              errs)
    if "priority" in d:
        _in_vocab(str(d["priority"]), "priorities", f"{where}.priority", errs)
    for sid, s in (d.get("streams") or {}).items():
        s = s or {}
        if "evidence_role" in s:
            _in_vocab(str(s["evidence_role"]), "evidence_roles",
                      f"{where}.streams.{sid}.evidence_role", errs)
        if "derivation" in s:
            _in_vocab(str(s["derivation"]), "derivation_classes",
                      f"{where}.streams.{sid}.derivation", errs)
    return errs


def validate_snapshot(d: Mapping[str, Any], *, where: str = "") -> list[str]:
    where = where or f"snapshot/{d.get('id', '?')}"
    errs = _structure(d, "snapshot", where)
    fmt = (d.get("storage") or {}).get("format")
    if fmt:
        _in_vocab(str(fmt), "storage_formats", f"{where}.storage.format", errs)
    if "files" not in d and "files_sidecar" not in d:
        errs.append(f"{where}: neither an inline file list nor a sidecar. A "
                    f"snapshot with no per-file record cannot be the thing a "
                    f"run bottoms out in.")
    return errs


def validate_artifact(d: Mapping[str, Any], *, where: str = "") -> list[str]:
    where = where or f"artifact/{d.get('id', '?')}"
    errs = _structure(d, "artifact", where)
    if "derivation" in d:
        _in_vocab(str(d["derivation"]), "derivation_classes",
                  f"{where}.derivation", errs)
    if not d.get("parents"):
        errs.append(f"{where}: no parents. An artifact is manufactured from "
                    f"something; an empty parent list produces a licence "
                    f"closure that is wrong in the permissive direction.")
    return errs


def _refs_resolve(reg: SourceRegistry, refs: Iterable[str], where: str,
                  known: Mapping[str, set[str]]) -> list[str]:
    errs = []
    for ref in refs:
        try:
            cls, ident = parse_ref(ref)
        except ValueError as e:
            errs.append(f"{where}: {e}")
            continue
        if cls in known and ident not in known[cls]:
            errs.append(f"{where}: {ref} does not resolve; known {cls}s are "
                        f"{sorted(known[cls])[:6]}...")
    return errs


def validate_all(root: Path | None = None) -> list[str]:
    """Every card, manifest and ref in the repo. Returns the problems."""
    reg = SourceRegistry(root)
    errs: list[str] = []
    sources = reg.sources()
    snapshots = reg.snapshots()
    artifacts = reg.artifacts()
    known = {"source": set(sources), "snapshot": set(snapshots),
             "artifact": set(artifacts)}
    for s in sources.values():
        errs += validate_source(s.raw)
    for sn in snapshots.values():
        errs += validate_snapshot(sn.raw)
        errs += _refs_resolve(reg, [sn.raw["source"]], f"snapshot/{sn.id}", known)
    for a in artifacts.values():
        errs += validate_artifact(a.raw)
        errs += _refs_resolve(reg, a.parents, f"artifact/{a.id}", known)
    return errs
