"""Rigid body: the first specialised world kernel, and the first with a clock.

Tier 6, native, deliberately small. The physics is semi-implicit Euler under a
uniform field; the point is that a domain engine sits behind the same narrow
contract as datalog and Lean and returns claims with honest error bars, which is
what makes property-specific fusion reachable.
"""

from __future__ import annotations

from .kernel import RIGID, RigidKernel
from .project import Body, RigidProgram, project_world

__all__ = ["RIGID", "RigidKernel", "Body", "RigidProgram", "project_world"]
