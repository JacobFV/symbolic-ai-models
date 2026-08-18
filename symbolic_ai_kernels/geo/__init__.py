"""Geo: geodesic distance and budgets on a stated datum. Tier 6, native.

The kernel that knows a coordinate is meaningless without a CRS, that latitude
and longitude are not interchangeable, and that the spherical answer is 0.5% out
— which is fine for "which is nearer" and not fine for a fuel budget.
"""

from __future__ import annotations

from .geodesy import (MEAN_RADIUS_KM, WGS84_A, WGS84_F, distance_km,
                      haversine_km, vincenty_km)
from .kernel import GEO, GeoKernel
from .project import SUPPORTED_CRS, GeoProgram, Place, project_world

__all__ = ["GEO", "GeoKernel", "GeoProgram", "Place", "project_world",
           "SUPPORTED_CRS", "distance_km", "haversine_km", "vincenty_km",
           "MEAN_RADIUS_KM", "WGS84_A", "WGS84_F"]
