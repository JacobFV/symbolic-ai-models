"""A flood-logistics world: cyclic roads, load limits, and an answer nobody said.

The point of this generator is to be the first task in the repo that **cannot**
be answered by any single kernel, and cannot be answered by copying from the
text at all. Getting the answer requires, in order:

1. a relational closure — which regions are still reachable once flooding closes
   some links (datalog: recursion over a **cyclic** road network);
2. a discrete choice under constraints — which vehicle to dispatch, given that
   closure (ASP: the completion space depends on step 1's *derived* facts, which
   is the explicit coupling);
3. arithmetic with units — whether that vehicle plus its load clears every
   bridge limit on the route (SMT: exactly the quantity claims datalog discards).

The report states the roads, the flooding, the bridge limits and the vehicle
masses. It never states which vehicle can do the job, and no sentence in it is
close to the answer — the answer is a function of three facts that never appear
in one paragraph.
"""

from __future__ import annotations

from .world import (FloodCase, REACH_RULES, generate, render_report,
                    solution_by_search)

__all__ = ["FloodCase", "REACH_RULES", "generate", "render_report",
           "solution_by_search"]
