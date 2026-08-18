"""E-graphs: equality saturation and cost-model extraction. Tier 5, native.

**Measured not to pay on the workload it was built for.** See
``notes/findings/2026-08-18-the-e-graph-costs-41x-what-it-optimises.md`` —
the technique is correct and the constraint sets it was pointed at were not the
binding cost. Kept because it is the only thing in the stack that can answer
*what else is the same thing*, and because the negative result is specific.
"""

from __future__ import annotations

from .egraph import (DynRewrite, EGraph, ENode, PVar, Rewrite,
                     SaturationReport, ematch, extract, saturate, term)
from .kernel import EGRAPH, EGraphKernel
from .constraints import RULES, from_term, node_cost, simplify, to_term

__all__ = ["DynRewrite", "EGraph", "ENode", "PVar", "Rewrite",
           "SaturationReport", "ematch", "extract", "saturate", "term",
           "EGRAPH", "EGraphKernel", "RULES", "from_term", "node_cost",
           "simplify", "to_term"]
