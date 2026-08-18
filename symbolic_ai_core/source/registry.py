"""Every source, snapshot and artifact this repo knows about, from the manifests.

There is **no hardcoded dictionary of sources**. ``symbolic_ai_kg.registry``
holds one — four entries, four functions — and it was the right first seam; it
does not survive three hundred sources, and more to the point it cannot express
the source/snapshot split, because a Python function that returns a graph has
nowhere to say *which bytes*.

The registry is a directory scan over tracked YAML. That means adding a source
is adding a file, a fresh clone sees every source it has a card for whether or
not any bytes are present, and ``symbolic-ai-models sources`` can print what is
held versus what is merely known.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Iterator

from .manifest import ArtifactManifest, Snapshot, Source

__all__ = ["SourceRegistry", "default_registry", "data_root", "repo_root"]

#: Where bulk bytes live. Overridable because the bytes are big, re-fetchable
#: and frequently on another disk — and because a path is never an identity.
DATA_ROOT_ENV = "SYMBOLIC_AI_DATA"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_root() -> Path:
    """The local bulk root. **Its absence is a normal state, not an error.**

    A fresh clone holds every manifest and none of the bytes. Code that treats a
    missing data root as a failure makes the manifests useless to exactly the
    reader they were tracked for.
    """
    env = os.environ.get(DATA_ROOT_ENV)
    return Path(env).expanduser() if env else repo_root() / "data"


class SourceRegistry:
    """A directory of YAML, read once."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else repo_root()

    # ---- reading -----------------------------------------------------
    @property
    def catalog_dir(self) -> Path:
        return self.root / "catalog" / "sources"

    @property
    def snapshot_dir(self) -> Path:
        return self.root / "manifests" / "snapshots"

    @property
    def artifact_dir(self) -> Path:
        return self.root / "manifests" / "artifacts"

    def sources(self) -> dict[str, Source]:
        out: dict[str, Source] = {}
        for p in sorted(self.catalog_dir.glob("*.yaml")):
            s = Source.load(p)
            if s.id in out:
                raise ValueError(f"duplicate source id {s.id!r} in "
                                 f"{p} and {out[s.id].path}")
            if s.id != p.stem:
                raise ValueError(f"{p}: source id {s.id!r} does not match its "
                                 f"filename; the filename is how a ref is "
                                 f"resolved without opening every card")
            out[s.id] = s
        return out

    def snapshots(self, source: str | None = None) -> dict[str, Snapshot]:
        out: dict[str, Snapshot] = {}
        base = self.snapshot_dir / source if source else self.snapshot_dir
        if not base.exists():
            return out
        for p in sorted(base.rglob("*.yaml")):
            s = Snapshot.load(p)
            out[s.id] = s
        return out

    def artifacts(self) -> dict[str, ArtifactManifest]:
        out: dict[str, ArtifactManifest] = {}
        if not self.artifact_dir.exists():
            return out
        for p in sorted(self.artifact_dir.rglob("*.yaml")):
            a = ArtifactManifest.load(p)
            out[a.id] = a
        return out

    def source(self, source_id: str) -> Source:
        try:
            return self.sources()[source_id]
        except KeyError:
            raise KeyError(f"no source card for {source_id!r} under "
                           f"{self.catalog_dir}") from None

    # ---- holdings ----------------------------------------------------
    def held(self, snapshot: Snapshot, root: Path | None = None) -> bool:
        """Whether *this machine* has the bytes. A property of the disk."""
        return snapshot.resolve(root or data_root()).exists()

    def census(self, root: Path | None = None) -> list[dict[str, object]]:
        """One row per snapshot: source, files, bytes, and whether it is here."""
        root = root or data_root()
        rows = []
        for s in self.snapshots().values():
            rows.append({"snapshot": s.id, "source": s.source,
                         "files": s.total_files(), "bytes": s.total_bytes(),
                         "held": self.held(s, root)})
        return sorted(rows, key=lambda r: (-int(r["bytes"]), str(r["snapshot"])))

    def __iter__(self) -> Iterator[Source]:
        return iter(self.sources().values())


@lru_cache(maxsize=1)
def default_registry() -> SourceRegistry:
    return SourceRegistry()
