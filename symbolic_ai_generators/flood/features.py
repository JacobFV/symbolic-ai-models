"""Features a routing gate may look at, and the rule about which those are.

**A gate may only read what is already on the table.** Every feature here is
arithmetic over the world plus datalog's derived reachability — the two things
that exist before ASP and SMT run. A feature requiring a solver would make the
gate cost what it is deciding whether to spend, which is the failure the routing
finding measured at one layer and the e-graph finding at another.

That constraint is doing real work: the obvious best predictor of "does the
cheap answer match the full answer" is *the full answer*, and it is not
available. Everything below is a proxy for it.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from symbolic_ai_core.world import Claim, Quantity, WorldSnapshot

__all__ = ["FEATURES", "features_of", "feature_vector"]

#: Names in a fixed order, because a learned weight vector is meaningless
#: against a different ordering and a silently reordered feature list is the
#: kind of bug that produces a model which is merely worse rather than broken.
FEATURES: tuple[str, ...] = (
    "bias",
    "reachable",            # datalog says the demand site can be reached
    "laden_over_min_limit", # the slack ratio the hand gate thresholds on
    "laden_over_max_limit",
    "n_bridges",
    "n_qualifying",         # vehicles whose capacity clears the demand
    "spread_laden",         # heaviest minus lightest qualifying laden mass
    "spread_limits",        # heaviest minus lightest posted limit
    "flooded_share",
)


def features_of(world: WorldSnapshot, reach: Sequence[Claim]
                ) -> dict[str, float]:
    """Cheap, solver-free features. See the module docstring for the rule."""
    from .ops import _demand, _fleet, _limits

    limits = list(_limits(world).values())
    fleet, demand = _fleet(world), _demand(world)
    dem = demand.value if demand is not None else 0.0
    laden = sorted(q["mass"].value + dem for q in fleet.values()
                   if q["capacity"].value >= dem)

    depot = next((c.roles["where"].id for c in world.claims
                  if c.predicate == "depot"), None)
    site = next((c.roles["where"].id for c in world.claims
                 if c.predicate == "needs"), None)
    pairs = {(getattr(c.roles.get("a"), "id", None),
              getattr(c.roles.get("b"), "id", None))
             for c in reach if c.predicate == "reach"}
    reachable = 1.0 if (depot, site) in pairs else 0.0

    regions = {e.id for e in world.entities.values() if "region" in e.types}
    flooded = sum(1 for c in world.claims if c.predicate == "flooded")

    lo, hi = (min(limits), max(limits)) if limits else (0.0, 0.0)
    return {
        "bias": 1.0,
        "reachable": reachable,
        # Scaled so every feature sits near unit magnitude. An unscaled ratio of
        # 6000 beside a 0/1 flag makes gradient descent a study of the largest
        # column rather than of the problem.
        "laden_over_min_limit": (max(laden) / lo) if (laden and lo) else 0.0,
        "laden_over_max_limit": (max(laden) / hi) if (laden and hi) else 0.0,
        "n_bridges": len(limits) / 10.0,
        "n_qualifying": len(laden) / 3.0,
        "spread_laden": ((laden[-1] - laden[0]) / 5000.0) if laden else 0.0,
        "spread_limits": ((hi - lo) / 5000.0) if limits else 0.0,
        "flooded_share": (flooded / len(regions)) if regions else 0.0,
    }


def feature_vector(world: WorldSnapshot, reach: Sequence[Claim]) -> list[float]:
    f = features_of(world, reach)
    return [f[name] for name in FEATURES]
