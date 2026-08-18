"""Reading the YAML, and hashing the JSON it means.

**YAML is what a person edits; canonical JSON is what is hashed.** A comment, a
reordered key or a reflowed string must not change an identity, and that is only
true if the digest is taken after parsing rather than over the file. This is the
same discipline the artifact layer already applies to values — see
``symbolic_ai_core/artifact/value.py`` — arriving at the metadata layer.

``yaml.safe_load`` and not ``yaml.load``: a manifest is data, and a format that
can construct arbitrary Python objects is a format where reading a catalogue is
executing it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

__all__ = ["Source", "Stream", "Snapshot", "ArtifactManifest",
           "canonical_json", "manifest_hash", "typed_ref", "parse_ref",
           "load_yaml", "dump_yaml", "REF_CLASSES"]

REF_CLASSES = ("source", "snapshot", "artifact", "view", "split", "run",
               "release", "stream", "kernel", "dataset")


def load_yaml(path: str | Path) -> dict[str, Any]:
    import yaml
    with Path(path).open(encoding="utf-8") as f:
        d = yaml.safe_load(f)
    if not isinstance(d, dict):
        raise ValueError(f"{path}: a manifest is a mapping, got "
                         f"{type(d).__name__}")
    return d


def dump_yaml(path: str | Path, data: Mapping[str, Any], *,
              header: str = "") -> None:
    import yaml
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(dict(data), sort_keys=False, allow_unicode=True,
                          default_flow_style=False, width=100)
    p.write_text((header + "\n" if header else "") + text, encoding="utf-8")


def canonical_json(value: Any) -> bytes:
    """Sorted keys, no whitespace, UTF-8, ``NaN`` rejected. The hashed form."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def manifest_hash(value: Mapping[str, Any], *, exclude: tuple[str, ...] = (
        "manifest_hash",)) -> str:
    """``sha256:<hex>`` over the canonical JSON, minus the self-referential bits.

    ``storage.locations`` is excluded because **filesystem location is never
    identity**: mirroring a snapshot to S3 must not produce a different
    snapshot. ``manifest_hash`` is excluded because a hash cannot cover itself.
    """
    d = {k: v for k, v in value.items() if k not in exclude}
    storage = d.get("storage")
    if isinstance(storage, dict):
        d = dict(d)
        d["storage"] = {k: v for k, v in storage.items()
                        if k not in ("locations", "root")}
    return "sha256:" + hashlib.sha256(canonical_json(d)).hexdigest()


def typed_ref(cls: str, ident: str) -> str:
    if cls not in REF_CLASSES:
        raise ValueError(f"unknown ref class {cls!r}; have {REF_CLASSES}")
    return f"{cls}/{ident}"


def parse_ref(ref: str) -> tuple[str, str]:
    """``'source/openalex'`` -> ``('source', 'openalex')``. Refuses bare strings.

    A bare string in a cross-reference field is how three different kinds of
    thing end up in one list and nothing downstream can index it.
    """
    cls, sep, ident = ref.partition("/")
    if not sep or cls not in REF_CLASSES:
        raise ValueError(
            f"{ref!r} is not a typed ref. Every cross-reference is "
            f"'<class>/<id>' with class in {REF_CLASSES}; a bare string cannot "
            f"be indexed without guessing what it names.")
    return cls, ident


@dataclass(frozen=True)
class Stream:
    """One semantic channel of a source. The id is used unchanged downstream."""

    id: str
    description: str = ""
    modality: str = ""
    quantity: str = ""
    unit: str = ""
    derivation: str = "unresolved"
    evidence_role: str = "observation"
    profiles: tuple[str, ...] = ()
    upstream: str = "unresolved"
    upstream_confidence: str = "unresolved"
    notes: str = ""


@dataclass(frozen=True)
class Source:
    """A source card: what the resource is, independent of what we hold."""

    id: str
    title: str
    raw: Mapping[str, Any] = field(default_factory=dict)
    path: Path | None = None

    @property
    def access(self) -> Mapping[str, Any]:
        return self.raw.get("access") or {}

    @property
    def license(self) -> Mapping[str, Any]:
        return self.raw.get("license") or {}

    @property
    def lifecycle(self) -> str:
        return str(self.raw.get("lifecycle", "unresolved"))

    @property
    def priority(self) -> str:
        return str(self.raw.get("priority", "watch"))

    @property
    def streams(self) -> dict[str, Stream]:
        out: dict[str, Stream] = {}
        for sid, d in (self.raw.get("streams") or {}).items():
            d = d or {}
            out[sid] = Stream(id=sid, description=d.get("description", ""),
                              modality=d.get("modality", ""),
                              quantity=d.get("quantity", ""),
                              unit=d.get("unit", ""),
                              derivation=d.get("derivation", "unresolved"),
                              evidence_role=d.get("evidence_role", "observation"),
                              profiles=tuple(d.get("profiles") or ()),
                              upstream=d.get("upstream", "unresolved"),
                              upstream_confidence=d.get("upstream_confidence",
                                                        "unresolved"),
                              notes=d.get("notes", ""))
        return out

    @property
    def ref(self) -> str:
        return typed_ref("source", self.id)

    @classmethod
    def load(cls, path: str | Path) -> "Source":
        d = load_yaml(path)
        return cls(id=d["id"], title=d.get("title", d["id"]), raw=d,
                   path=Path(path))


@dataclass(frozen=True)
class Snapshot:
    """Exact bytes from one source at one time, wherever they currently sit."""

    id: str
    source: str
    raw: Mapping[str, Any] = field(default_factory=dict)
    path: Path | None = None

    @property
    def ref(self) -> str:
        return typed_ref("snapshot", self.id)

    @property
    def storage(self) -> Mapping[str, Any]:
        return self.raw.get("storage") or {}

    @property
    def root(self) -> str:
        return str(self.storage.get("root", ""))

    @property
    def inventory(self) -> Mapping[str, Any]:
        return self.raw.get("inventory") or {}

    def total_bytes(self) -> int:
        return sum(int(v.get("bytes", 0)) for v in self.inventory.values())

    def total_files(self) -> int:
        return sum(int(v.get("files", 0)) for v in self.inventory.values())

    def resolve(self, root: Path) -> Path:
        """Where these bytes are on *this* machine. May not exist; that is legal.

        Absence of the local data root is a normal state, not an error: the
        manifests are the tracked thing and a fresh clone has none of the bytes.
        """
        return root / self.root

    @classmethod
    def load(cls, path: str | Path) -> "Snapshot":
        d = load_yaml(path)
        return cls(id=d["id"], source=parse_ref(d["source"])[1], raw=d,
                   path=Path(path))


@dataclass(frozen=True)
class ArtifactManifest:
    """A manufactured thing, with its parents and its licence closure."""

    id: str
    artifact_type: str
    raw: Mapping[str, Any] = field(default_factory=dict)
    path: Path | None = None

    @property
    def ref(self) -> str:
        return typed_ref("artifact", self.id)

    @property
    def parents(self) -> tuple[str, ...]:
        return tuple(self.raw.get("parents") or ())

    @property
    def derivation(self) -> str:
        return str(self.raw.get("derivation", "derived"))

    @classmethod
    def load(cls, path: str | Path) -> "ArtifactManifest":
        d = load_yaml(path)
        return cls(id=d["id"], artifact_type=d.get("artifact_type", ""), raw=d,
                   path=Path(path))
