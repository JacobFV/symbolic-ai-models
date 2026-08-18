"""Source federation: what exists upstream, what bytes we hold, and under what terms.

Four object classes, and the whole point is that they are **not** the same thing:

``source``
    an external evidence-producing resource. What it *is*: who publishes it,
    under what licence, what streams it emits. Says nothing about this machine.
``snapshot``
    exact bytes obtained from one source at one time. The only object here that
    may assert something about a disk — and it asserts it about a *named
    location*, so a second machine that lacks the bytes disagrees with the
    location list rather than with the manifest.
``artifact``
    anything manufactured from snapshots or other artifacts, carrying parents, a
    generator, parameters, a derivation class and a licence closure.
``view`` / ``split`` / ``run``
    a declarative projection, an immutable membership assignment, an execution.
    Not implemented here yet; the schemas exist so the layer above knows they
    are coming and does not grow a fifth meaning of "dataset".

Invariants this module enforces rather than documents:

* **filesystem location is never identity.** A snapshot's ``locations`` is a
  list and is not hashed; adding a mirror does not make it a different snapshot.
* **derived can never become measured.** ``license_closure`` and the derivation
  class propagate downward and only ever get more restrictive.
* **an unknown licence poisons the closure.** ``unresolved`` is not a synonym
  for ``permitted``, and a derived artifact with one unresolved parent is
  unresolved.
"""

from __future__ import annotations

from .manifest import (ArtifactManifest, Snapshot, Source, Stream,
                       canonical_json, manifest_hash, parse_ref, typed_ref)
from .registry import SourceRegistry, data_root, default_registry
from .license import LICENSE_ORDER, license_closure

__all__ = ["ArtifactManifest", "Snapshot", "Source", "Stream",
           "canonical_json", "manifest_hash", "parse_ref", "typed_ref",
           "SourceRegistry", "data_root", "default_registry",
           "LICENSE_ORDER", "license_closure"]
