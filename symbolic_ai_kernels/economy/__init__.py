"""Economy: consolidated aggregates as known on a date. Tier 6, native.

The kernel that refuses to default ``as_of`` to now, because the only default
available is the look-ahead bias every optimistic backtest is made of.
"""

from __future__ import annotations

from .kernel import ECONOMY, EconomyKernel, as_of_value
from .project import EconomyProgram, Observation, project_world

__all__ = ["ECONOMY", "EconomyKernel", "as_of_value", "EconomyProgram",
           "Observation", "project_world"]
