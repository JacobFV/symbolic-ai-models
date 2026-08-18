"""``P_geo`` : world -> places with coordinates in one stated CRS.

The second specialised world kernel. What it takes is narrow — ``geo.place`` or
``geo.geometry`` carrying a latitude and longitude, and a ``geo.crs`` saying
which datum they are in — and the discards are the point.

**A coordinate without a CRS is not a location.** 51.5, -0.13 is London on WGS84
and is somewhere in the North Sea on a datum shifted by a few hundred metres. The
projection therefore refuses to guess: a place with no stated CRS is discarded by
name, and two CRSs in one world is a refusal, because there is no reprojection
here on purpose — a reframe belongs in an explicit flow node where the trace can
show it, exactly as with units.

**Latitude and longitude are not interchangeable and the order is not obvious.**
EPSG:4326 is officially latitude-first; almost every JSON API is longitude-first;
GeoJSON is longitude-first by specification. So the facet must name its fields
rather than carry a pair, and a bare two-element list is discarded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from symbolic_ai_core.world import WorldSnapshot

from ..abi import Discard, Projection

__all__ = ["Place", "GeoProgram", "project_world", "SEMANTICS", "SUPPORTED_CRS"]

SEMANTICS = ("classical",)

#: The only datum this kernel does geodesy on. Named rather than assumed, so a
#: world in anything else is refused rather than silently measured wrong.
SUPPORTED_CRS = ("EPSG:4326",)


@dataclass(frozen=True)
class Place:
    """One located thing. Degrees, in the program's single CRS."""

    id: str
    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.lat <= 90.0:
            raise ValueError(
                f"{self.id}: latitude {self.lat} is out of range. This is what a "
                f"longitude in the latitude field looks like, and it is the one "
                f"coordinate error that announces itself.")
        if not -180.0 <= self.lon <= 180.0:
            raise ValueError(f"{self.id}: longitude {self.lon} is out of range")


@dataclass
class GeoProgram:
    places: dict[str, Place] = field(default_factory=dict)
    crs: str = ""

    def __repr__(self) -> str:                                # pragma: no cover
        return f"GeoProgram({len(self.places)} places in {self.crs!r})"


def project_world(world: WorldSnapshot) -> Projection:
    """``P_geo(world)``."""
    prog = GeoProgram()
    discards: list[Discard] = []
    covered: set[str] = set()
    crss: set[str] = set()

    # Declared CRSs are collected BEFORE anything is filtered. The first version
    # compared the set after discarding unsupported ones, so with a single
    # supported CRS the mixed-datum branch was unreachable -- dead code that
    # read as a guard. A test that expected it to fire is what found that.
    declared = {str((e.facet("geo.place") or e.facet("geo.geometry")).values
                    .get("crs", ""))
                for e in world.entities.values()
                if (e.facet("geo.place") or e.facet("geo.geometry")) is not None}
    declared.discard("")
    if len(declared) > 1:
        raise ValueError(
            f"places arrive in {sorted(declared)}. There is no reprojection "
            f"here on purpose: a reframe belongs in an explicit flow node where "
            f"the trace can show it, exactly as with units.")

    for eid, e in sorted(world.entities.items()):
        facet = e.facet("geo.place") or e.facet("geo.geometry")
        if facet is None:
            continue
        vals = dict(facet.values or {})
        crs = str(vals.get("crs", ""))
        if not crs:
            discards.append(Discard(
                "entity", eid,
                "no CRS on the geo facet. A coordinate without a datum is not a "
                "location -- 51.5,-0.13 is London on WGS84 and open water on a "
                "datum a few hundred metres away."))
            continue
        if crs not in SUPPORTED_CRS:
            discards.append(Discard(
                "entity", eid,
                f"CRS {crs!r} is not one this kernel does geodesy on "
                f"{list(SUPPORTED_CRS)}; reproject in an explicit node rather "
                f"than letting the numbers through"))
            continue
        lat, lon = vals.get("lat"), vals.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            discards.append(Discard(
                "entity", eid,
                f"lat={lat!r} lon={lon!r}: the facet must NAME its fields. "
                f"EPSG:4326 is latitude-first, GeoJSON is longitude-first, and "
                f"a bare pair is a coin flip between them."))
            continue
        try:
            prog.places[eid] = Place(id=eid, lat=float(lat), lon=float(lon))
        except ValueError as err:
            discards.append(Discard("entity", eid, str(err)))
            continue
        crss.add(crs)
        covered.add(eid)

    prog.crs = next(iter(crss), "")

    return Projection(
        kernel="geo@1", program=prog, semantics=SEMANTICS,
        covered_entities=frozenset(covered), covered_claims=(),
        discarded=tuple(discards),
        meta={"n_places": len(prog.places), "crs": prog.crs,
              "supported_crs": list(SUPPORTED_CRS)})
