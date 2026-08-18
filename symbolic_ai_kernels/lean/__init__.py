"""Lean: the verifier. Tier 4 of the kernel stack.

Native and total, on the kernel already vendored in :mod:`symbolic_ai_lean`.
Real Lean 4 remains the out-of-band conformance oracle it was there — a
subprocess elaborator inside a sweep breaks the cost budget this repo is arguing
about, which is a standing rule in ``ROADMAP.md``.
"""

from __future__ import annotations

from .kernel import LEAN, LeanKernel
from .project import LeanProgram, project_world

__all__ = ["LEAN", "LeanKernel", "LeanProgram", "project_world"]
