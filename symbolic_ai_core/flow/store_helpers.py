"""One import-cycle-free place to rebuild an :class:`Artifact` from JSON."""

from __future__ import annotations

from typing import Any, Mapping

from ..artifact.store import _from_dict
from ..artifact.value import Artifact

__all__ = ["artifact_from_dict"]


def artifact_from_dict(d: Mapping[str, Any]) -> Artifact:
    return _from_dict(dict(d))
