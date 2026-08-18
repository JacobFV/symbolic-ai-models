"""Distance on an ellipsoid, and why the spherical answer is not good enough.

The haversine formula on a mean-radius sphere is the usual choice and is wrong by
up to ~0.5% — about 5 km on a 1,000 km leg. That is fine for "which city is
nearer" and not fine for a fuel budget, and the difference between those two uses
is exactly the kind of thing this substrate is supposed to make visible rather
than leave to whoever wrote the helper.

So both are here, the ellipsoidal one is the default, and the kernel reports
which it used. WGS84, because that is what ``SUPPORTED_CRS`` names.
"""

from __future__ import annotations

import math

__all__ = ["haversine_km", "vincenty_km", "distance_km", "WGS84_A", "WGS84_F",
           "MEAN_RADIUS_KM"]

WGS84_A = 6_378_137.0          #: semi-major axis, metres
WGS84_F = 1 / 298.257223563    #: flattening
MEAN_RADIUS_KM = 6371.0088     #: IUGG mean radius


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance on a sphere. Fast, and up to ~0.5% out."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * MEAN_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def vincenty_km(lat1: float, lon1: float, lat2: float, lon2: float, *,
                tol: float = 1e-12, max_iter: int = 200) -> float:
    """Geodesic distance on the WGS84 ellipsoid, by Vincenty's inverse method.

    Returns ``float('nan')`` on the antipodal case, where the iteration is known
    not to converge — **not** a fallback to haversine. A silent substitution
    there would return a plausible number computed by a different method than the
    one the caller asked for, which is the failure mode this repo's no-fallback
    rule exists to prevent. The caller can see the NaN and choose.
    """
    if lat1 == lat2 and lon1 == lon2:
        return 0.0
    b = WGS84_A * (1 - WGS84_F)
    U1 = math.atan((1 - WGS84_F) * math.tan(math.radians(lat1)))
    U2 = math.atan((1 - WGS84_F) * math.tan(math.radians(lat2)))
    L = math.radians(lon2 - lon1)
    sinU1, cosU1 = math.sin(U1), math.cos(U1)
    sinU2, cosU2 = math.sin(U2), math.cos(U2)
    lam = L
    for _ in range(max_iter):
        sin_lam, cos_lam = math.sin(lam), math.cos(lam)
        sin_sigma = math.sqrt((cosU2 * sin_lam) ** 2 +
                              (cosU1 * sinU2 - sinU1 * cosU2 * cos_lam) ** 2)
        if sin_sigma == 0:
            return 0.0
        cos_sigma = sinU1 * sinU2 + cosU1 * cosU2 * cos_lam
        sigma = math.atan2(sin_sigma, cos_sigma)
        sin_alpha = cosU1 * cosU2 * sin_lam / sin_sigma
        cos2_alpha = 1 - sin_alpha ** 2
        cos2sm = (cos_sigma - 2 * sinU1 * sinU2 / cos2_alpha
                  if cos2_alpha != 0 else 0.0)
        C = WGS84_F / 16 * cos2_alpha * (4 + WGS84_F * (4 - 3 * cos2_alpha))
        prev, lam = lam, L + (1 - C) * WGS84_F * sin_alpha * (
            sigma + C * sin_sigma * (cos2sm + C * cos_sigma *
                                     (-1 + 2 * cos2sm ** 2)))
        if abs(lam - prev) < tol:
            break
    else:
        return float("nan")            # antipodal; see the docstring
    u2 = cos2_alpha * (WGS84_A ** 2 - b ** 2) / (b ** 2)
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    d_sigma = B * sin_sigma * (
        cos2sm + B / 4 * (cos_sigma * (-1 + 2 * cos2sm ** 2) -
                          B / 6 * cos2sm * (-3 + 4 * sin_sigma ** 2) *
                          (-3 + 4 * cos2sm ** 2)))
    return b * A * (sigma - d_sigma) / 1000.0


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float, *,
                method: str = "ellipsoid") -> float:
    if method == "ellipsoid":
        return vincenty_km(lat1, lon1, lat2, lon2)
    if method == "sphere":
        return haversine_km(lat1, lon1, lat2, lon2)
    raise ValueError(f"unknown method {method!r}; have 'ellipsoid', 'sphere'")
