"""Runtime services that sit above the flow layer and below the kernels.

Two things:

**fusion** — how several kernels' claims about the same property become one
world, or explicitly fail to.

**margin** — how far a decision sits from its boundary, measured on uncorrupted
worlds. Three tasks say that one number governs both whether a cheap gate can
fire and whether recall or precision errors dominate, so it is worth measuring
before building either a router or a reader.
"""

from __future__ import annotations

from .margin import (MarginProfile, margin_profile, relative_margin)
from .fusion import (FUSION_RULES, ClaimGroup, FusionResult, fuse,
                     group_claims, independent_odds, intersect_intervals,
                     inverse_variance, log_opinion_pool, register_fusion,
                     sum_quantities)

__all__ = ["MarginProfile", "margin_profile", "relative_margin",
           "FUSION_RULES", "ClaimGroup", "FusionResult", "fuse", "group_claims",
           "independent_odds", "intersect_intervals", "inverse_variance",
           "log_opinion_pool", "register_fusion", "sum_quantities"]
