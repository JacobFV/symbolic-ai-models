"""Where artifact bytes live. Content-addressed, so a cache cannot be wrong.

The store is deliberately dumb: ``put`` returns the id it computed and ``get``
returns what is under an id. It cannot overwrite — writing a different value
under an existing id is impossible, because the id *is* the value — which is the
property that makes ``test_cache_is_semantically_inert`` provable rather than
hoped for.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, Protocol, runtime_checkable

from .value import Artifact

__all__ = ["ArtifactStore", "MemoryStore", "FileStore"]


@runtime_checkable
class ArtifactStore(Protocol):
    """Put a value in, get it back by its content address."""

    def put(self, artifact: Artifact) -> str: ...
    def get(self, artifact_id: str) -> Artifact: ...
    def has(self, artifact_id: str) -> bool: ...
    def __iter__(self) -> Iterator[str]: ...


def _from_dict(d: dict[str, Any]) -> Artifact:
    from .value import ArtifactRef, Interval, Provenance
    ref = d.get("ref")
    prov = d.get("provenance") or {}
    return Artifact(
        type=d["type"], value=d.get("value"),
        ref=ArtifactRef(**ref) if ref else None,
        schema=d.get("schema", ""), profiles=tuple(d.get("profiles") or ()),
        unit=d.get("unit", ""), frame=d.get("frame", ""),
        valid_time=Interval(**(d.get("valid_time") or {})),
        transaction_time=Interval(**(d.get("transaction_time") or {})),
        provenance=Provenance(producer=prov.get("producer", ""),
                              inputs=tuple(prov.get("inputs") or ()),
                              source=prov.get("source", ""),
                              source_version=prov.get("source_version", ""),
                              license=prov.get("license", ""),
                              method=prov.get("method", "")),
        present=d.get("present", True), meta=dict(d.get("meta") or {}))


class MemoryStore:
    """One process, one dict. The default, because most runs never spill."""

    def __init__(self) -> None:
        self._by_id: dict[str, Artifact] = {}

    def put(self, artifact: Artifact) -> str:
        aid = artifact.id
        self._by_id.setdefault(aid, artifact)     # first writer wins; same bytes
        return aid

    def get(self, artifact_id: str) -> Artifact:
        try:
            return self._by_id[artifact_id]
        except KeyError:
            raise KeyError(f"no artifact {artifact_id} in this store") from None

    def has(self, artifact_id: str) -> bool:
        return artifact_id in self._by_id

    def __iter__(self) -> Iterator[str]:
        return iter(self._by_id)

    def __len__(self) -> int:
        return len(self._by_id)


class FileStore:
    """One JSON file per artifact, fanned out by the first two hex digits.

    Survives a process, which is what a resumed run needs. Large payloads are
    supposed to be ``ArtifactRef``s to a blob written elsewhere; this store is
    for the descriptors, not for the meshes.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, artifact_id: str) -> Path:
        digest = artifact_id.rsplit(":", 1)[-1]
        return self.root / digest[:2] / f"{digest}.json"

    def put(self, artifact: Artifact) -> str:
        aid = artifact.id
        p = self._path(aid)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(artifact.to_dict(), ensure_ascii=False),
                         encoding="utf-8")
        return aid

    def get(self, artifact_id: str) -> Artifact:
        p = self._path(artifact_id)
        if not p.exists():
            raise KeyError(f"no artifact {artifact_id} under {self.root}")
        return _from_dict(json.loads(p.read_text(encoding="utf-8")))

    def has(self, artifact_id: str) -> bool:
        return self._path(artifact_id).exists()

    def __iter__(self) -> Iterator[str]:
        for p in sorted(self.root.glob("*/*.json")):
            yield f"artifact:blake2b:{p.stem}"
