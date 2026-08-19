"""Machine assignment under capability and capacity constraints — the third task.

Built to occupy the cell neither of the first two does: **an expensive kernel
and a tunable decision margin at the same time.**

* flood logistics — expensive kernels (ASP + SMT), moderate margin.
* solvency — a trivial kernel, tunable margin, 179x cheaper end to end.
* scheduling — expensive kernel (ASP search over an exponential space) **and** a
  margin knob, so the two regime claims can be tested jointly on a task neither
  was measured on.

The question is one boolean: *can every job be assigned to a machine that has its
capability, without any machine exceeding its time budget?* The margin is the
slack between total demand and total capacity, and it is a generator parameter.
"""

from __future__ import annotations

from .world import (CORRUPTIONS, HARD_REGIME, SchedulingCase, corrupt,
                    feasible_by_search, generate, generate_hard)

__all__ = ["SchedulingCase", "generate", "generate_hard", "HARD_REGIME",
           "feasible_by_search", "corrupt", "CORRUPTIONS"]
