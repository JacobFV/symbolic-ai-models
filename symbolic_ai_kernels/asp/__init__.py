"""Answer set programming: defaults, exceptions and world completion.

Tier 2 of the kernel stack. Requires ``clingo``, which is an **optional** extra
(``uv sync --extra solvers``); without it the kernel raises
:class:`~symbolic_ai_kernels.abi.KernelUnavailable` rather than degrading to a
weaker reasoner, because a silent fallback is how a broken component reads as a
working one.
"""

from __future__ import annotations

from .kernel import ASP, AspKernel
from .mangle import Mangler, quote
from .project import AspProgram, project_world

__all__ = ["ASP", "AspKernel", "Mangler", "quote", "AspProgram", "project_world"]
