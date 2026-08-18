"""Runtime services that sit above the flow layer and below the kernels.

Currently one thing: **fusion** — how several kernels' claims about the same
property become one world, or explicitly fail to.
"""

from __future__ import annotations

from .fusion import (FUSION_RULES, ClaimGroup, FusionResult, fuse,
                     group_claims, independent_odds, intersect_intervals,
                     log_opinion_pool, register_fusion, sum_quantities)

__all__ = ["FUSION_RULES", "ClaimGroup", "FusionResult", "fuse", "group_claims",
           "independent_odds", "intersect_intervals", "log_opinion_pool",
           "register_fusion", "sum_quantities"]
