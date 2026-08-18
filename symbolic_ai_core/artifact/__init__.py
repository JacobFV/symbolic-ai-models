"""What travels on an edge of a flow graph.

Every edge carries an **artifact**: an immutable, content-addressed value with a
declared type, a schema, and enough metadata that a consumer can refuse it. The
refusal is the point. This repo's most expensive standing lesson is that the
shared substrate moves results more than the models do, and an untyped value
passed between two components is exactly how a unit, a coordinate frame or a
time base changes without anybody choosing it.
"""

from __future__ import annotations

from .value import (Artifact, ArtifactRef, Interval, Provenance, artifact_id,
                    canonical_bytes)
from .store import ArtifactStore, MemoryStore, FileStore

__all__ = ["Artifact", "ArtifactRef", "Interval", "Provenance", "artifact_id",
           "canonical_bytes", "ArtifactStore", "MemoryStore", "FileStore"]
