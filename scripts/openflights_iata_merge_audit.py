"""How many ``kg:iata:*`` nodes are two airports, and does it change an answer?

``notes/findings/2026-08-18-the-corpus-does-contain-a-two-source-property-conflict-four-airports.md``
found, incidentally, that openflights merges distinct airports that share an
IATA code: ``kg:iata:AMN`` carries Gratiot Community Airport's label, ICAO
``KAMN`` and Michigan coordinates alongside ``city=Kamloops country=Canada``.
Two real airports collapsed into one body. That finding reached the count 7
through a **cross-source** join (openflights vs geonames) plus an ICAO-prefix
leave-one-out rule. This script re-derives it from **openflights alone**, with a
different pair of instruments, and then prices the damage.

**The two instruments, and why they are conjoined.** Neither is usable alone:

1. *ICAO-prefix purity.* An ICAO location indicator's first two letters are
   allocated by region, so the other airports on a prefix are a self-declared
   check on this one. Leave-one-out: the prefix must carry at least 4 other
   airports, **none** of them asserting this airport's country, and **all** of
   them asserting one single other country. Run alone with only the
   leave-one-out and a support floor -- the previous finding's rule -- it fires
   on 24 of 5,995, and 17 of those are dependencies and territories (Jersey on
   ``EG*``, Christmas Island on ``YP*``, Aruba on ``TN*``): a 71% false-positive
   rate corpus-wide. The purity requirement is what removes them, because a
   territory sits on a prefix its administering state shares with others.
2. *Coordinate-country incoherence.* Distance from the airport to the nearest
   **other** airport asserting the same country, against the distance to the
   nearest airport of the prefix's country. Run alone at any threshold it
   cannot tell a merge from a genuinely remote airport -- Easter Island is
   3,568 km from another Chilean airport and is not a defect.

Conjoined they screen 8 rows out of 5,995. Seven are merges. The eighth is
Kaliningrad, and it is named and left in the report rather than tuned away.

**What the screen cannot see**, stated because a blast radius quoted off a
detector with an unstated blind spot is worthless: rows with no 4-character
ICAO code, rows whose ICAO prefix carries fewer than 4 other airports, rows
whose prefix is genuinely shared between countries, and rows whose merged-in
country is the same as the coordinates' country. The eligible fraction is
printed.

Run: ``uv run python -u scripts/openflights_iata_merge_audit.py``
"""

from __future__ import annotations

import argparse
import collections
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq

#: The prefix must carry this many *other* airports before purity means
#: anything. Below it, a single-country prefix is an accident of sample size --
#: Kaieteur sits on ``PK*`` with 3 others and would otherwise flag.
MIN_PREFIX_SUPPORT = 4

#: The asserted country must itself be attested by this many airports. Below
#: it, "no other airport in this country is nearby" is vacuous: 12 of the 24
#: rows the bare leave-one-out rule flags are the *only* airport in their
#: territory (Brunei, Jersey, Norfolk Island, ...).
MIN_COUNTRY_SUPPORT = 4

#: The coordinates must be this many times closer to the prefix country's
#: nearest airport than to the asserted country's. **Fitted, and the margin is
#: thin**: the merges run 3.4 to 940, and Kaliningrad -- a real Russian
#: exclave on a prefix Belarus dominates -- sits at 2.2. A threshold between
#: 2.2 and 3.4 is a judgement, not a measurement, which is why the screen is
#: reported at 8 rows and the adjudication is named.
MIN_DISPLACEMENT_RATIO = 3.0

#: Adjudicated by hand from the screen below. Each is a body carrying one
#: airport's ``label``/``icao``/``lat``/``lon`` and another's ``city``/
#: ``country``. Identical to the seven the cross-source join reached, which is
#: the corroboration: two instruments sharing no input agree exactly.
MERGED = ("AMN", "BPE", "EMP", "LND", "OCN", "OEL", "TZR")

#: Screened and adjudicated **not** a merge. Khrabrovo really is in Kaliningrad
#: and Kaliningrad really is Russia; ``UM*`` is a Soviet-era prefix covering
#: Belarus and the exclave, so its purity-1.0 is an artefact of 7 airports.
SCREENED_BENIGN = ("KGD",)

#: The 29 IATA codes where geonames asserts a different country from
#: openflights, over 5,882 subjects both sources place. **Copied, not
#: re-derived**, from
#: ``notes/findings/2026-08-18-the-corpus-does-contain-a-two-source-property-conflict-four-airports.md``
#: -- reproduce with ``scripts/two_source_country_conflict.py --all``.
SECOND_SOURCE_DISAGREES = (
    "ACF", "HGI", "BOR", "HLJ",                       # bad joins
    "AMN", "BPE", "EMP", "LND", "OCN", "OEL", "TZR",  # the merges audited here
    "BON", "CUR", "EUX", "SAB", "SXM",                # retired ISO code
    "HLE", "LYR", "MHQ", "SBH", "SFG",                # dependency vs sovereign
    "MAK", "RBX", "WUU",                              # Sudan / South Sudan
    "EUN", "SMW", "VIL", "PRN",                       # contested sovereignty
    "AKT",                                            # unexplained
)

#: The subset of the above that the same finding adjudicated as a genuine
#: two-source conflict: a disagreement no source is entitled to settle.
SECOND_SOURCE_UNSETTLEABLE = ("EUN", "SMW", "VIL", "PRN")

_KEY = re.compile(r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)=")
_R_KM = 6371.0088


def data_root() -> Path:
    env = os.environ.get("SYMBOLIC_AI_DATA")
    if env:
        return Path(env).expanduser()
    here = Path(__file__).resolve().parents[1]
    if (here / "data" / "sources").exists():
        return here / "data"
    for parent in here.parents:
        if (parent / "data" / "sources").exists():
            return parent / "data"
    return here / "data"


def parse_body(body: str | None) -> dict[str, str]:
    """The shadow schema. A value runs to the start of the next key."""
    if not body:
        return {}
    marks = [(m.start(1), m.end(), m.group(1).lower()) for m in _KEY.finditer(body)]
    out: dict[str, str] = {}
    for i, (_, val_start, key) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        value = body[val_start:end].strip()
        if value:
            out[key] = value
    return out


def great_circle_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * _R_KM * math.asin(min(1.0, math.sqrt(h)))


@dataclass(frozen=True)
class Corpus:
    """Everything the audit reads, loaded once."""

    body: dict[str, dict[str, str]]
    label: dict[str, str]
    iso: dict[str, str]                     #: id -> ISO2, from the in-country edge
    pos: dict[str, tuple[float, float]]
    routes: list[tuple[str, str]]

    @property
    def ids(self) -> list[str]:
        return sorted(set(self.pos) & set(self.iso))


def load(root: Path) -> Corpus:
    base = root / "sources" / "openflights"
    body, label = {}, {}
    for f in sorted(base.rglob("airports*.parquet")):
        for row in pq.read_table(f).to_pylist():
            body[row["id"]] = parse_body(row["body"])
            label[row["id"]] = row["label"] or ""
    iso: dict[str, str] = {}
    routes: list[tuple[str, str]] = []
    for f in sorted(base.rglob("routes*.parquet")):
        for batch in pq.ParquetFile(f).iter_batches(
                columns=["source_id", "target_id", "kind"]):
            for row in batch.to_pylist():
                if row["kind"] == "in-country":
                    iso[row["source_id"]] = row["target_id"].rsplit(":", 1)[-1]
                elif row["kind"] == "flies-to":
                    routes.append((row["source_id"], row["target_id"]))
    pos = {}
    for nid, kv in body.items():
        try:
            pos[nid] = (float(kv["lat"]), float(kv["lon"]))
        except (KeyError, ValueError):
            pass
    return Corpus(body=body, label=label, iso=iso, pos=pos, routes=routes)


@dataclass(frozen=True)
class Screened:
    """One row both instruments fired on."""

    iata: str
    asserted: str
    prefix: str
    prefix_country: str
    prefix_support: int
    d_asserted_km: float
    d_prefix_km: float

    @property
    def ratio(self) -> float:
        return (self.d_asserted_km / self.d_prefix_km
                if self.d_prefix_km else math.inf)


def screen(c: Corpus) -> tuple[list[Screened], dict[str, int]]:
    """The conjunction of the two instruments, with its own blind spot counted."""
    ids = c.ids
    by_country: dict[str, list[str]] = collections.defaultdict(list)
    for a in ids:
        by_country[c.iso[a]].append(a)
    prefix: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    for a in ids:
        icao = (c.body[a].get("icao") or "").strip()
        if len(icao) == 4:
            prefix[icao[:2]][c.iso[a]] += 1

    def nearest(a: str, country: str) -> float:
        return min((great_circle_km(c.pos[a], c.pos[b])
                    for b in by_country.get(country, ()) if b != a),
                   default=math.inf)

    stats: collections.Counter = collections.Counter()
    hits: list[Screened] = []
    for a in ids:
        icao = (c.body[a].get("icao") or "").strip()
        if len(icao) != 4:
            stats["no 4-character ICAO -- invisible to the screen"] += 1
            continue
        others = collections.Counter(prefix[icao[:2]])
        others[c.iso[a]] -= 1
        others = +others
        support = sum(others.values())
        if support < MIN_PREFIX_SUPPORT:
            stats["prefix too thin -- invisible to the screen"] += 1
            continue
        if len(by_country[c.iso[a]]) < MIN_COUNTRY_SUPPORT:
            stats["asserted country too thin -- invisible to the screen"] += 1
            continue
        stats["eligible for the screen"] += 1
        if others.get(c.iso[a], 0):
            continue
        top, cnt = others.most_common(1)[0]
        if cnt != support:
            stats["prefix shared between countries -- instrument 1 declines"] += 1
            continue
        stats["instrument 1 (ICAO purity) fires"] += 1
        d_ass, d_top = nearest(a, c.iso[a]), nearest(a, top)
        hit = Screened(iata=a.rsplit(":", 1)[-1], asserted=c.iso[a],
                       prefix=icao[:2], prefix_country=top,
                       prefix_support=support,
                       d_asserted_km=d_ass, d_prefix_km=d_top)
        if hit.ratio < MIN_DISPLACEMENT_RATIO:
            stats["instrument 2 (displacement) declines"] += 1
            continue
        hits.append(hit)
    return sorted(hits, key=lambda h: -h.ratio), dict(stats)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=1, help="k for the kNN answer check")
    args = ap.parse_args()

    root = data_root()
    print(f"data root: {root}")
    c = load(root)
    ids = c.ids
    print(f"openflights: {len(c.body)} airport rows, {len(c.pos)} with "
          f"coordinates, {len(c.iso)} with an in-country edge, "
          f"{len(c.routes)} flies-to edges")
    print(f"subjects carrying both a coordinate and a country: {len(ids)}")

    # ---------------------------------------------------------------- 1. count
    hits, stats = screen(c)
    print("\n=== 1. the screen ===")
    for k in ["no 4-character ICAO -- invisible to the screen",
              "prefix too thin -- invisible to the screen",
              "asserted country too thin -- invisible to the screen",
              "eligible for the screen",
              "prefix shared between countries -- instrument 1 declines",
              "instrument 1 (ICAO purity) fires",
              "instrument 2 (displacement) declines"]:
        print(f"  {stats.get(k, 0):6d}  {k}")
    blind = len(ids) - stats.get("eligible for the screen", 0)
    print(f"  {blind:6d}  BLIND SPOT: rows the screen structurally cannot see "
          f"({blind / len(ids):.2%})")

    print(f"\n  screened: {len(hits)} rows")
    print(f"  {'iata':5s} {'of':3s} {'pfx':4s} {'->':3s} {'n':>4s} "
          f"{'d_asserted':>11s} {'d_prefix':>10s} {'ratio':>8s}  verdict")
    for h in hits:
        nid = f"kg:iata:{h.iata}"
        verdict = ("MERGE" if h.iata in MERGED else
                   "benign (adjudicated)" if h.iata in SCREENED_BENIGN
                   else "UNADJUDICATED -- inspect")
        print(f"  {h.iata:5s} {h.asserted:3s} {h.prefix:4s} "
              f"{h.prefix_country:3s} {h.prefix_support:4d} "
              f"{h.d_asserted_km:11.0f} {h.d_prefix_km:10.0f} {h.ratio:8.1f}  "
              f"{verdict}")
        print(f"        label={c.label[nid]!r} city={c.body[nid].get('city','')!r} "
              f"icao={c.body[nid].get('icao','')} "
              f"at {c.pos[nid][0]:.3f},{c.pos[nid][1]:.3f}")

    merged = [f"kg:iata:{x}" for x in MERGED]
    missing = [m for m in merged if m not in c.body]
    unadjudicated = [h.iata for h in hits
                     if h.iata not in MERGED and h.iata not in SCREENED_BENIGN]
    print(f"\n  adjudicated merges: {len(MERGED)}  "
          f"({len(MERGED) / len(ids):.5f} of the corpus)")
    print(f"  final screen: {len(hits)} rows, of which {len(unadjudicated)} are "
          f"unadjudicated")
    print(f"  instrument 1 alone fired on "
          f"{stats.get('instrument 1 (ICAO purity) fires', 0)}; instrument 2 "
          f"declined {stats.get('instrument 2 (displacement) declines', 0)} "
          f"({', '.join(SCREENED_BENIGN)}).")
    print(f"  THE THIN MARGIN, stated rather than hidden: the lowest-ratio merge "
          f"is {min(hits, key=lambda h: h.ratio).iata} at "
          f"{min(h.ratio for h in hits):.1f} and the declined row sits at 2.2. "
          f"A cut anywhere in (2.2, 3.4) gives this answer; the ordering is "
          f"measured, the cut is a judgement.")
    if missing:
        print(f"  !! manifest is stale: {missing} not in the corpus")

    # -------------------------------------------- 2/3. airport_country damage
    print("\n=== 2. blast radius: airport_country ===")
    from symbolic_ai_tasks.airport_country import (STRONGEST_FLOOR_DEG,
                                                   evaluate, load_task,
                                                   predict_anchor, predict_grid,
                                                   predict_knn)
    base = root / "sources" / "openflights"
    task = load_task(base)
    inside = [m for m in merged if m in task.truth]
    print(f"  task instances: {len(task.ids)}")
    print(f"  instances that ARE a merged node: {len(inside)}  "
          f"({len(inside) / len(task.ids):.5f} = "
          f"{100 * len(inside) / len(task.ids):.3f}%)")

    print("\n=== 3. does it change an answer? ===")
    pred = predict_knn(task, args.k)
    grid = predict_grid(task, STRONGEST_FLOOR_DEG)
    anchor = predict_anchor(task)
    wrong = [a for a in inside if pred[a] != task.truth[a]]
    print(f"  a. the contaminated instances themselves, {args.k}-NN:")
    for a in inside:
        print(f"     {a.rsplit(':', 1)[-1]:4s} truth={task.truth[a].rsplit(':', 1)[-1]:3s} "
              f"pred={pred[a].rsplit(':', 1)[-1]:3s} "
              f"{'WRONG' if pred[a] != task.truth[a] else 'right'}")
    print(f"     -> {len(wrong)}/{len(inside)} scored wrong. Each is a label from "
          f"one airport judged against another's coordinates.")

    clean_ids = [a for a in task.ids if a not in set(merged)]
    from symbolic_ai_tasks.airport_country import AirportCountryTask
    clean = AirportCountryTask(
        pos={a: task.pos[a] for a in clean_ids},
        truth={a: task.truth[a] for a in clean_ids},
        body_country={a: v for a, v in task.body_country.items()
                      if a in set(clean_ids)})
    cpred = predict_knn(clean, args.k)
    flipped = [a for a in clean_ids if cpred[a] != pred[a]]
    newly_right = [a for a in flipped if cpred[a] == task.truth[a]]
    newly_wrong = [a for a in flipped if pred[a] == task.truth[a]]
    print(f"\n  b. the OTHER instances, when the {len(inside)} are removed from "
          f"the reference set:")
    print(f"     {len(flipped)} of {len(clean_ids)} change their prediction "
          f"({len(flipped) / len(clean_ids):.6f})")
    print(f"     {len(newly_right)} become right, {len(newly_wrong)} become wrong")
    for a in flipped:
        print(f"     {a.rsplit(':', 1)[-1]:4s} {pred[a].rsplit(':', 1)[-1]:3s} -> "
              f"{cpred[a].rsplit(':', 1)[-1]:3s}  (truth "
              f"{task.truth[a].rsplit(':', 1)[-1]})")

    print("\n  c. what the published numbers become on the cleaned task:")
    cgrid = predict_grid(clean, STRONGEST_FLOOR_DEG)
    canchor = predict_anchor(clean)
    rows = [("1-NN over coordinates", evaluate(task, pred), evaluate(clean, cpred)),
            (f"grid floor @{STRONGEST_FLOOR_DEG} deg", evaluate(task, grid),
             evaluate(clean, cgrid)),
            ("ground-truth anchor (the leak)", evaluate(task, anchor),
             evaluate(clean, canchor)),
            ("modal floor", task.floor(), clean.floor())]
    print(f"     {'metric':32s} {'published':>10s} {'cleaned':>10s} {'delta':>9s}")
    for name, pub, cl in rows:
        print(f"     {name:32s} {pub:10.4f} {cl:10.4f} {cl - pub:+9.4f}")

    # ---------------------------------- 2b/3b. range_limited_routing damage
    print("\n=== 2b/3b. blast radius: range_limited_routing ===")
    from symbolic_ai_adapters import load_airports, load_routes
    from symbolic_ai_tasks.range_limited_routing import build_network
    air = load_airports(base)
    pos = {aid: (e.facets["geo.place"].values["lat"],
                 e.facets["geo.place"].values["lon"])
           for aid, e in air.world.entities.items()}
    edges, rres = load_routes(base, known=pos)
    net = build_network(pos, edges)
    touching = [(s, t) for s, t in edges if s in set(merged) or t in set(merged)]
    in_graph = [m for m in merged if m in net.adjacency]
    legs = [k for k in net.length_km if k[0] in set(merged) or k[1] in set(merged)]
    print(f"  admitted flies-to edges: {len(edges)}")
    print(f"  network nodes: {len(net.nodes)}   measured legs: {len(net.length_km)}")
    print(f"  edges incident to a merged node: {len(touching)}  "
          f"({len(touching) / len(edges):.6f})")
    print(f"  legs whose length is computed from a merged node's coordinates: "
          f"{len(legs)}")
    print(f"  merged nodes present in the network at all: {len(in_graph)} "
          f"of {len(merged)}")
    print("  the merge corrupts `city` and `country`; this task reads `lat`, "
          "`lon` and `flies-to` and reads neither.")
    if not touching and not in_graph:
        print("  -> blast radius is EXACTLY ZERO, for two independent reasons: "
              "no merged node carries a route, so none is a node of the graph; "
              "and the corrupted fields are not among the ones read.")

    # --------------------------------------------- 5. ground-truth circularity
    print("\n=== 5. the ground-truth circularity ===")
    name_to_iso: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    for a in ids:
        n = c.body[a].get("country")
        if n:
            name_to_iso[n][c.iso[a]] += 1
    ambiguous = {k: v for k, v in name_to_iso.items() if len(v) > 1}
    print(f"  distinct country-name strings in the body: {len(name_to_iso)}")
    print(f"  strings mapping to more than one in-country ISO2: {len(ambiguous)}")
    print("  -> the body string and the in-country edge are the SAME assertion "
         "rendered twice.")
    print(f"  the anchor scores {evaluate(task, anchor):.4f} on the contaminated "
          f"task and {evaluate(clean, canchor):.4f} on the cleaned one: it reads "
          f"the merged-in half and is judged against the merged-in half, so it "
          f"is structurally blind to this defect.")

    print("\n  the second circularity: the labels ARE one side of a two-source "
          "disagreement.")
    print(f"  Not re-derived -- taken from the finding on disk, which joined "
          f"{len(SECOND_SOURCE_DISAGREES)} IATA codes where geonames asserts a "
          f"different country from openflights over 5,882 joined subjects.")
    contested = [f"kg:iata:{x}" for x in SECOND_SOURCE_DISAGREES]
    present = [a for a in contested if a in task.truth]
    unsettleable = [f"kg:iata:{x}" for x in SECOND_SOURCE_UNSETTLEABLE]
    up = [a for a in unsettleable if a in task.truth]
    agree_of = [a for a in up if pred[a] == task.truth[a]]
    print(f"  instances whose label a second source contradicts: {len(present)} "
          f"({len(present) / len(task.ids):.5f} = "
          f"{100 * len(present) / len(task.ids):.3f}%)")
    print(f"  of those, ones no source is entitled to settle: {len(up)} "
          f"({100 * len(up) / len(task.ids):.3f}%) -- "
          f"{', '.join(x.rsplit(':', 1)[-1] for x in up)}")
    print(f"  1-NN reproduces openflights' own answer on {len(agree_of)}/{len(up)} "
          f"of them, because its neighbours are openflights rows too.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
