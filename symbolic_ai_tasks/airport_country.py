"""Which country is this airport in, given only where it is on the sphere?

The first task here with a floor worth beating. Shortest-path had none — every
method that answers it answers it exactly — so it could not produce a
``$/solved-episode-above-floor`` number however cheap it was.

This one can be wrong. 5,995 airports, 222 countries, and the ground truth is
openflights' own ``in-country`` edges: externally authored, and *discarded* by
the route adapter as a different relation, which is why they are available here
as labels rather than as features.

**The leak, named.** Each airport's body also carries ``country=Papua New
Guinea`` as a string. Using it would make this a dictionary lookup wearing the
costume of an inference, so it is excluded from every method and used instead as
the ground-truth anchor: a method that reads it must score ~1.0, and if it does
not, the labels and the bodies disagree and the task is broken before any model
touches it.
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from symbolic_ai_kernels.geo import distance_km

__all__ = ["AirportCountryTask", "load_task", "evaluate", "predict_knn",
           "predict_modal", "predict_anchor", "FLOOR_NAME", "unit_vectors"]

FLOOR_NAME = "modal country"


@dataclass(frozen=True)
class AirportCountryTask:
    """Coordinates, labels, and the leak kept separate from both."""

    pos: Mapping[str, tuple[float, float]]      #: id -> (lat, lon)
    truth: Mapping[str, str]                    #: id -> country entity id
    body_country: Mapping[str, str]             #: the leak, for the anchor only

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.truth))

    def floor(self) -> float:
        c = collections.Counter(self.truth.values())
        return c.most_common(1)[0][1] / len(self.truth)


def load_task(base: Path) -> AirportCountryTask:
    import pyarrow.parquet as pq

    from symbolic_ai_adapters import load_airports, parse_body

    air = load_airports(base)
    truth: dict[str, str] = {}
    for f in sorted(base.rglob("routes*.parquet")):
        for batch in pq.ParquetFile(f).iter_batches(
                columns=["source_id", "target_id", "kind"]):
            for row in batch.to_pylist():
                if row["kind"] == "in-country":
                    truth[row["source_id"]] = row["target_id"]
    pos, body = {}, {}
    for aid, ent in air.world.entities.items():
        if aid not in truth:
            continue
        f = ent.facets["geo.place"].values
        pos[aid] = (f["lat"], f["lon"])
        ident = ent.facets.get("core.identity")
        if ident and "country" in ident.values:
            body[aid] = ident.values["country"]
    truth = {k: v for k, v in truth.items() if k in pos}
    return AirportCountryTask(pos=pos, truth=truth, body_country=body)


def unit_vectors(pos: Mapping[str, tuple[float, float]]
                 ) -> dict[str, tuple[float, float, float]]:
    """Lat/lon to a point on the unit sphere.

    Squared chordal distance orders identically to great-circle distance, so
    neighbour *ranking* is exact under it while costing no trigonometry per
    pair. The reported distances still come from the geo kernel — this is a
    ranking shortcut, not a second geodesy.
    """
    out = {}
    for k, (la, lo) in pos.items():
        rla, rlo = math.radians(la), math.radians(lo)
        c = math.cos(rla)
        out[k] = (c * math.cos(rlo), c * math.sin(rlo), math.sin(rla))
    return out


def predict_modal(task: AirportCountryTask) -> dict[str, str]:
    """The floor: every airport is in the commonest country."""
    top = collections.Counter(task.truth.values()).most_common(1)[0][0]
    return {a: top for a in task.ids}


def predict_anchor(task: AirportCountryTask) -> dict[str, str]:
    """The leak, as an anchor. Must score ~1.0 or the task is broken."""
    by_name: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    for a, name in task.body_country.items():
        by_name[name][task.truth[a]] += 1
    lookup = {n: c.most_common(1)[0][0] for n, c in by_name.items()}
    return {a: lookup.get(task.body_country.get(a, ""), "") for a in task.ids}


def predict_knn(task: AirportCountryTask, k: int = 1, *,
                pos: Mapping[str, tuple[float, float]] | None = None
                ) -> dict[str, str]:
    """Leave-one-out k-nearest-neighbour vote over coordinates alone.

    Leave-one-out is not a convenience here: an airport is trivially its own
    nearest neighbour, and including it would score the labels against
    themselves.
    """
    pos = task.pos if pos is None else pos
    vec = unit_vectors(pos)
    ids = task.ids
    items = [(vec[a], task.truth[a], a) for a in ids]
    out = {}
    for a in ids:
        va = vec[a]
        best: list[tuple[float, str]] = []
        for vb, lab, b in items:
            if b == a:
                continue
            d = ((va[0]-vb[0])**2 + (va[1]-vb[1])**2 + (va[2]-vb[2])**2)
            if len(best) < k:
                best.append((d, lab)); best.sort()
            elif d < best[-1][0]:
                best[-1] = (d, lab); best.sort()
        out[a] = collections.Counter(l for _, l in best).most_common(1)[0][0]
    return out


def evaluate(task: AirportCountryTask, pred: Mapping[str, str]) -> float:
    return sum(pred.get(a) == task.truth[a] for a in task.ids) / len(task.ids)
