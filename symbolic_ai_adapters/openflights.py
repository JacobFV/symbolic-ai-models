"""Openflights airports and routes -> world IR.

The first adapter over externally authored bytes. Everything measured through it
is a claim about a dataset somebody else built for their own reasons, which is
the property the generated tasks cannot have however carefully they are
constructed.

The coordinates arrive inside a string: ``city=Goroka country=Papua New Guinea
lat=-6.0816 lon=145.39``. That shadow schema is why a column-level audit read
this source as carrying nothing — see
``notes/lessons/2026-08-18-a-column-audit-cannot-see-a-shadow-schema.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from symbolic_ai_core.world import Entity, Facet, WorldSnapshot

__all__ = ["AdapterResult", "OPENFLIGHTS_CRS", "load_airports", "load_routes",
           "parse_body", "CONSUMED_KEYS"]

#: Asserted, not measured. Openflights' published documentation gives airport
#: coordinates as decimal degrees on WGS84; no field in the parquet says so.
#: Recorded on every facet as an assumption with this citation attached, because
#: the alternative -- defaulting -- makes a guess indistinguishable from a fact.
OPENFLIGHTS_CRS = "EPSG:4326"
CRS_BASIS = ("asserted from openflights.org/data.html, which documents airport "
             "latitude and longitude as decimal degrees on WGS84; no field in "
             "the held bytes states a datum")

#: Body keys this adapter turns into world state. Everything else is discarded
#: by name rather than ignored.
CONSUMED_KEYS = frozenset({"lat", "lon", "city", "country"})

_KV = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^ ]*)")

#: The relation that means "an airline flies this". The route files also carry
#: ``in-country`` edges to jurisdictions, and mixing the two would make a
#: reachability question meaningless.
ROUTE_KIND = "flies-to"


def parse_body(body: str | None) -> dict[str, str]:
    """The shadow schema, made explicit.

    Values are left as strings. Coercion is the caller's decision because the
    caller is the one that knows whether an empty string means absent — this
    corpus writes ``iata=`` for "no IATA code", and a parser that returned
    ``""`` as a value would make missing into present.
    """
    if not body:
        return {}
    return {k.lower(): v for k, v in _KV.findall(body) if v}


@dataclass
class AdapterResult:
    """What came through, and what did not."""

    world: WorldSnapshot
    rows: int = 0
    admitted: int = 0
    discarded: dict[str, int] = field(default_factory=dict)
    dropped_keys: dict[str, int] = field(default_factory=dict)

    def discard(self, reason: str) -> None:
        self.discarded[reason] = self.discarded.get(reason, 0) + 1

    @property
    def loss_rate(self) -> float:
        return 0.0 if not self.rows else 1.0 - self.admitted / self.rows

    def summary(self) -> str:
        drops = ", ".join(f"{k}={v}" for k, v in
                          sorted(self.discarded.items(), key=lambda kv: -kv[1]))
        return (f"{self.admitted}/{self.rows} admitted "
                f"({self.loss_rate:.1%} lost)" + (f"; {drops}" if drops else ""))


def _rows(base: Path, stem: str, columns: Sequence[str]) -> Iterator[dict]:
    import pyarrow.parquet as pq
    for f in sorted(base.rglob(f"{stem}*.parquet")):
        pf = pq.ParquetFile(f)
        if not set(columns) <= set(pf.schema_arrow.names):
            continue
        for batch in pf.iter_batches(columns=list(columns)):
            yield from batch.to_pylist()


def load_airports(base: Path, *, limit: int | None = None) -> AdapterResult:
    """Airport nodes with coordinates, as ``geo.place`` entities."""
    res = AdapterResult(world=WorldSnapshot())
    entities: list[Entity] = []
    for row in _rows(base, "airports", ("id", "label", "kind", "body")):
        res.rows += 1
        if limit is not None and res.admitted >= limit:
            break
        kv = parse_body(row.get("body"))
        for k in kv:
            if k not in CONSUMED_KEYS:
                res.dropped_keys[k] = res.dropped_keys.get(k, 0) + 1
        if "lat" not in kv or "lon" not in kv:
            res.discard("no coordinate in body")
            continue
        try:
            lat, lon = float(kv["lat"]), float(kv["lon"])
        except ValueError:
            res.discard("uncoercible coordinate")
            continue
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            res.discard("coordinate out of range")
            continue
        facets = {"geo.place": Facet("geo.place", {
            "lat": lat, "lon": lon, "crs": OPENFLIGHTS_CRS,
            "crs_basis": CRS_BASIS})}
        if "country" in kv:
            facets["core.identity"] = Facet(
                "core.identity", {"label": row.get("label") or row["id"],
                                  "country": kv["country"]})
        entities.append(Entity(id=row["id"], facets=facets))
        res.admitted += 1
    res.world = WorldSnapshot(entities={e.id: e for e in entities})
    return res


def load_routes(base: Path, known: Mapping[str, Any] | None = None
                ) -> tuple[list[tuple[str, str]], AdapterResult]:
    """Directed route edges between airports.

    Route files also carry ``in-country`` edges to jurisdictions; those are a
    different relation and are discarded by name rather than folded into the
    network, because a reachability question over a graph that silently mixes
    "you can fly there" with "it is in the same country" answers neither.
    """
    res = AdapterResult(world=WorldSnapshot())
    edges: list[tuple[str, str]] = []
    for row in _rows(base, "routes", ("source_id", "target_id", "kind")):
        res.rows += 1
        if row["kind"] != ROUTE_KIND:
            res.discard(f"kind={row['kind']}")
            continue
        s, t = row["source_id"], row["target_id"]
        if known is not None and (s not in known or t not in known):
            res.discard("endpoint not a located airport")
            continue
        edges.append((s, t))
        res.admitted += 1
    return edges, res
