"""SMT: arithmetic and logic together, with units checked before the solver.

Tier 3 of the kernel stack. Requires ``z3-solver``, an **optional** extra
(``uv sync --extra solvers``); without it the kernel raises
:class:`~symbolic_ai_kernels.abi.KernelUnavailable` rather than degrading.
"""

from __future__ import annotations

from .kernel import SMT, SmtKernel
from .project import SmtProgram, Variable, project_world, unit_of
from .units import UnitError, div, mul, parse_unit, same

__all__ = ["SMT", "SmtKernel", "SmtProgram", "Variable", "project_world",
           "unit_of", "UnitError", "div", "mul", "parse_unit", "same"]
