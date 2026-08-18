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

import collections
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from symbolic_ai_core.world import Entity, Facet, WorldSnapshot

__all__ = ["AdapterResult", "OPENFLIGHTS_CRS", "load_airports", "load_routes",
           "parse_body", "CONSUMED_KEYS", "OpenflightsIntegrityError",
           "MERGED_IATA_NODES", "detect_merged_iata_nodes",
           "check_iata_merges"]

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

#: A value runs to the start of the *next* key, not to the next space.
#: ``country=Papua New Guinea lat=-6.08`` has a three-word value, and a parser
#: that stops at whitespace silently returns ``Papua`` -- which is what the
#: first version of this did, and what the task's ground-truth anchor caught by
#: scoring 0.9715 where it had to score ~1.0. Note the grammar is only
#: recoverable because no value here contains ``=``; it is ambiguous in
#: principle, which is what an untyped bag buys you.
_KEY = re.compile(r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)=")

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
    marks = [(m.start(1), m.end(), m.group(1).lower())
             for m in _KEY.finditer(body)]
    out: dict[str, str] = {}
    for i, (_, val_start, key) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        value = body[val_start:end].strip()
        if value:
            out[key] = value
    return out


class OpenflightsIntegrityError(RuntimeError):
    """A row carries two airports' fields, and it is not one this repo knows.

    Raised rather than repaired, dropped or counted. A silent repair is how a
    broken component reads as a working one, and this defect was invisible to
    every guard the corpus already had -- including ``airport_country``'s
    ground-truth anchor, which reads the same corrupted half it is scored
    against and therefore scores 1.0 over it.
    """


#: ``kg:iata:*`` nodes in the 2026-08-15 snapshot whose body carries one
#: airport's ``label``/``icao``/``lat``/``lon`` and a *different* airport's
#: ``city``/``country``, because openflights merged two airports that share an
#: IATA code. ``kg:iata:AMN`` is Gratiot Community Airport (``KAMN``, Michigan)
#: wearing ``city=Kamloops country=Canada``.
#:
#: Reached twice by instruments sharing no input: a cross-source join against
#: geonames (``scripts/two_source_country_conflict.py``) and, from openflights
#: alone, ICAO-prefix purity conjoined with coordinate displacement
#: (``scripts/openflights_iata_merge_audit.py``). Both give exactly these seven.
#:
#: They are **not** removed or corrected on load. Every published
#: ``airport_country`` number was measured with them in, and cleaning them
#: would silently redefine those numbers -- the measured effect is +0.0021 on
#: the 1-NN headline and +0.0009 on the swept floor, both inside the tolerance
#: those numbers are quoted to.
MERGED_IATA_NODES = frozenset({
    "kg:iata:AMN", "kg:iata:BPE", "kg:iata:EMP", "kg:iata:LND",
    "kg:iata:OCN", "kg:iata:OEL", "kg:iata:TZR",
})

#: Rows the first instrument flags and the second clears. Khrabrovo really is
#: in Kaliningrad and Kaliningrad really is Russia; ``UM*`` is a Soviet-era
#: prefix shared with Belarus, so its purity is an artefact of carrying only
#: seven airports. Named here so a later reader can see it was adjudicated
#: rather than never noticed.
SCREEN_DECLINED_BENIGN = frozenset({"kg:iata:KGD"})

#: Other airports the ICAO prefix must carry before its unanimity means
#: anything. Kaieteur sits on ``PK*`` with three and would otherwise flag.
MIN_PREFIX_SUPPORT = 4

#: Airports the asserted country must itself have. Below it, "no airport of
#: this country is nearby" is vacuous -- twelve of the rows a bare
#: leave-one-out rule flags are the only airport in their territory.
MIN_COUNTRY_SUPPORT = 4

#: How much closer the coordinates must be to the prefix country's nearest
#: airport than to the asserted country's. **Fitted, on a thin margin**: the
#: seven merges run 3.4 to 940 and Kaliningrad sits at 2.2.
MIN_DISPLACEMENT_RATIO = 3.0

_EARTH_R_KM = 6371.0088


def _great_circle_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * _EARTH_R_KM * math.asin(min(1.0, math.sqrt(h)))


def detect_merged_iata_nodes(
        rows: Mapping[str, tuple[Mapping[str, str], tuple[float, float]]]
) -> tuple[frozenset[str], frozenset[str]]:
    """Which rows carry two airports, and which rows the test could speak about.

    ``rows`` maps node id to its parsed body and its ``(lat, lon)``. Returns
    ``(detected, eligible)``. **Both** halves matter: a detector that reports
    an empty set because nothing was eligible is indistinguishable from a clean
    corpus, and the caller has to be able to tell those apart.

    Two instruments must agree, because neither is usable alone:

    1. *ICAO-prefix purity.* The first two letters of an ICAO location
       indicator are allocated by region, so the other airports on a prefix
       are a self-declared check on this one. Leave-one-out: at least
       :data:`MIN_PREFIX_SUPPORT` others, **none** asserting this row's
       country, and **all** asserting one single other country. Without the
       unanimity requirement this fires on 24 of 5,995 rows and 17 are
       dependencies -- Jersey on ``EG*``, Christmas Island on ``YP*`` -- a 71%
       false-positive rate, because a territory sits on a prefix its
       administering state shares.
    2. *Coordinate displacement.* The coordinates must be
       :data:`MIN_DISPLACEMENT_RATIO` times closer to the prefix country's
       nearest airport than to the asserted country's. Alone this cannot tell
       a merge from a remote airport: Easter Island is 3,568 km from another
       Chilean airport and is not a defect.

    The country is read from the body's ``country`` **name**, not from an ISO
    code, because the airports table is all this sees -- and the two are
    interchangeable here: 223 name strings map to 223 ISO codes with no
    collisions in the held snapshot.
    """
    usable = {nid: (kv, pos) for nid, (kv, pos) in rows.items()
              if kv.get("country") and len((kv.get("icao") or "").strip()) == 4}
    by_country: dict[str, list[str]] = collections.defaultdict(list)
    prefix: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    for nid, (kv, _) in usable.items():
        by_country[kv["country"]].append(nid)
        prefix[kv["icao"].strip()[:2]][kv["country"]] += 1

    def nearest(nid: str, country: str) -> float:
        here = usable[nid][1]
        return min((_great_circle_km(here, usable[b][1])
                    for b in by_country.get(country, ()) if b != nid),
                   default=math.inf)

    detected: set[str] = set()
    eligible: set[str] = set()
    for nid, (kv, _) in usable.items():
        others = collections.Counter(prefix[kv["icao"].strip()[:2]])
        others[kv["country"]] -= 1
        others = +others
        support = sum(others.values())
        if support < MIN_PREFIX_SUPPORT:
            continue
        if len(by_country[kv["country"]]) < MIN_COUNTRY_SUPPORT:
            continue
        eligible.add(nid)
        if others.get(kv["country"], 0):
            continue
        top, count = others.most_common(1)[0]
        if count != support:
            continue
        d_here = nearest(nid, kv["country"])
        d_prefix = nearest(nid, top)
        if d_prefix <= 0.0:
            continue
        if d_here / d_prefix >= MIN_DISPLACEMENT_RATIO:
            detected.add(nid)
    return frozenset(detected), frozenset(eligible)


def check_iata_merges(
        rows: Mapping[str, tuple[Mapping[str, str], tuple[float, float]]]
) -> frozenset[str]:
    """Refuse to hand back a corpus whose contamination is not the known one.

    Two ways to fail, and both are loud:

    * a row trips the detector that :data:`MERGED_IATA_NODES` does not name --
      the snapshot has contamination nobody has looked at;
    * a row :data:`MERGED_IATA_NODES` names is present and *eligible* and does
      not trip -- either the snapshot was fixed or the detector drifted, and
      either way the manifest is now a lie about the bytes.

    Restricting the second check to *eligible* rows is what makes this correct
    under a partial load: a detector cannot speak about a row whose ICAO prefix
    is not in front of it, and a guard that fires on its own blindness would be
    noise rather than a signal.
    """
    detected, eligible = detect_merged_iata_nodes(rows)
    unknown = detected - MERGED_IATA_NODES
    if unknown:
        raise OpenflightsIntegrityError(
            f"{len(unknown)} openflights row(s) carry a country that contradicts "
            f"their own ICAO prefix and coordinates, and are not in "
            f"MERGED_IATA_NODES: {sorted(unknown)}. Adjudicate them with "
            f"scripts/openflights_iata_merge_audit.py before using this "
            f"snapshot -- do not widen the manifest to silence this.")
    stale = (MERGED_IATA_NODES & eligible) - detected
    if stale:
        raise OpenflightsIntegrityError(
            f"MERGED_IATA_NODES names {sorted(stale)} as merged, but the "
            f"detector no longer flags them in bytes it can see. The snapshot "
            f"changed or the detector drifted; every airport_country number was "
            f"measured with these rows in, so re-audit before editing either.")
    return detected


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
    """Airport nodes with coordinates, as ``geo.place`` entities.

    Every admitted row is checked by :func:`check_iata_merges` before the
    snapshot is handed back, because openflights merges airports that share an
    IATA code and the merged rows are indistinguishable from clean ones at the
    row level. The known seven load **unchanged** -- the check refuses an
    *unrecognised* contamination, it does not repair a recognised one, so no
    number measured over this adapter moves.
    """
    res = AdapterResult(world=WorldSnapshot())
    entities: list[Entity] = []
    seen: dict[str, tuple[dict[str, str], tuple[float, float]]] = {}
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
        seen[row["id"]] = (kv, (lat, lon))
        res.admitted += 1
    check_iata_merges(seen)
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
