"""Do openflights and geonames ever disagree about which country an airport is in?

Three findings in a row have said this corpus holds no genuine **two-source
property conflict** — no property where two independently authored sources both
assert a value for the same real-world subject and the values differ. Every
conflict measured so far (251 filed-vs-filed, 4,992 closure-vs-filed) is
*within* GLEIF. This script tests the one candidate `HANDOVER.md` §4 names:
airports, which both `openflights` and `geonames` place in a country.

**The join is the whole experiment.** A bad join manufactures conflicts, and a
manufactured conflict is worse than a null because it looks like a finding. So
the join is built strictly and then attacked with keys it was not built from:

- **Subject key: the IATA code.** openflights names airports `kg:iata:XXX`
  directly; geonames reaches them through `code_bridges` (`kg:geonames:N`
  ``same-as`` `kg:iata:XXX`). No coordinate tolerance, no fuzzy name matching
  and no string normalisation anywhere in the *join*.
- **The hazard the key has:** an IATA code is not a key on the geonames side.
  8,549 of 11,403 bridged codes reach two geonames records and 537 reach three
  or more, because the code is shared by the airport and by the settlement it
  serves. Joining on the code alone compares openflights' airport against
  geonames' *city*, which is a different subject.
- **The tier that fixes it:** keep only geonames records whose feature code is
  an aerodrome (``S/AIR*``), and require exactly one survivor.
- **Two checks the join did not see:** the ICAO code (openflights carries one in
  its body, geonames carries one in the same bridge table) and the airport
  *name*. Either disagreeing is evidence the two records are different airports.

**Why the comparison needs no normalisation.** Both sources state the country as
an ISO 3166-1 alpha-2 code — openflights through its `in-country` edge to
`kg:iso:country:XX`, geonames in the place body as `country=XX`. There is no
"US" vs "United States" vs "USA" problem available to explain a disagreement
away with.

**The failure mode that the first pass missed, and why it is handled here.**
openflights' snapshot merges airports that *share* an IATA code: `kg:iata:AMN`
carries the label, ICAO (``KAMN``) and coordinates (43.32, -84.69, Michigan) of
Gratiot Community Airport but ``city=Kamloops country=Canada``. openflights is
then not asserting a country for the subject it named, so a disagreement there
is not a two-source conflict — it is one source having merged two subjects.
Detected without any external authority, from openflights alone: a **2-letter
ICAO prefix is regional**, so an airport whose asserted country never occurs
among the *other* airports sharing its ICAO prefix is internally incoherent.
The rule is deliberately conservative — it needs 3 other airports on the prefix
before it fires, which is why it leaves Western Sahara (``GM*``, asserted as
both MA and EH within openflights) and Kosovo (``BK*``, one airport) alone.

Run: ``uv run python -u scripts/two_source_country_conflict.py``
"""

from __future__ import annotations

import argparse
import collections
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq

#: geonames feature codes that denote an aerodrome rather than a settlement.
AERODROME = ("S/AIRP", "S/AIRB", "S/AIRF", "S/AIRH", "S/AIRQ", "S/AIRS",
             "S/AIRT", "S/AIRG")

#: Words that carry no identity in an airport name.
NAME_STOPWORDS = frozenset("""
airport airfield aerodrome air base station field municipal regional
international intl national county community memorial the of and
""".split())

#: ISO codes retired or superseded while these snapshots were being written.
#: Both sources describe the same ground; one is using an older vocabulary.
#: ``AN`` (Netherlands Antilles) was withdrawn in 2010.
RETIRED = {"AN": {"BQ", "CW", "SX"}}

#: One state became two. Both codes are current; the disagreement is about
#: *when*, not about who has a claim. South Sudan seceded in 2011.
SUCCESSOR = {"SD": {"SS"}}

#: Dependencies and territories whose ISO code differs from the state they
#: belong to, plus territories that were detached from another territory
#: (MF and BL left GP in 2007). A pair like ``SH`` vs ``GB`` is two sources
#: choosing a different *granularity* for the word "country", not two sources
#: disagreeing about where the airport is.
DEPENDENCY_OF = {
    "PR": "US", "VI": "US", "GU": "US", "AS": "US", "MP": "US", "UM": "US",
    "GP": "FR", "MQ": "FR", "GF": "FR", "RE": "FR", "YT": "FR", "PM": "FR",
    "BL": "FR", "MF": "FR", "WF": "FR", "PF": "FR", "NC": "FR", "TF": "FR",
    "AW": "NL", "CW": "NL", "SX": "NL", "BQ": "NL", "AN": "NL",
    "AI": "GB", "BM": "GB", "IO": "GB", "VG": "GB", "KY": "GB", "FK": "GB",
    "GI": "GB", "MS": "GB", "PN": "GB", "SH": "GB", "TC": "GB", "GG": "GB",
    "JE": "GB", "IM": "GB", "GS": "GB",
    "HK": "CN", "MO": "CN",
    "FO": "DK", "GL": "DK",
    "SJ": "NO", "BV": "NO",
    "CK": "NZ", "NU": "NZ", "TK": "NZ",
    "CX": "AU", "CC": "AU", "NF": "AU", "HM": "AU",
    "AX": "FI",
}
DETACHED_FROM = {"MF": "GP", "BL": "GP"}

#: Pairs where the two codes are two states' claims on the same ground. This is
#: the category that makes a disagreement a *genuine* two-source conflict rather
#: than a modelling choice, a vocabulary vintage or an ingest defect.
CONTESTED = {
    frozenset(("TW", "CN")),   # Taiwan
    frozenset(("EH", "MA")),   # Western Sahara
    frozenset(("XK", "RS")),   # Kosovo
    frozenset(("PS", "IL")),   # Palestine
    frozenset(("UA", "RU")),   # Crimea / Donbas
    frozenset(("CY", "TR")),   # Northern Cyprus
    frozenset(("GE", "RU")),   # Abkhazia / South Ossetia
    frozenset(("MD", "RU")),   # Transnistria
    frozenset(("AM", "AZ")),   # Nagorno-Karabakh
    frozenset(("IN", "PK")),   # Kashmir
    frozenset(("IN", "CN")),   # Aksai Chin / Arunachal
}

JOIN_ERROR_ICAO = "join error: ICAO codes differ"
JOIN_ERROR_NAME = "join error: different airport names"
OF_INCOHERENT = "openflights merged two airports sharing an IATA code"
VINTAGE = "retired ISO code (vocabulary vintage)"
GRANULARITY = "dependency vs sovereign (granularity)"
TEMPORAL = "successor state (one source stale)"
CONTESTED_LABEL = "contested sovereignty"
UNEXPLAINED = "unexplained — candidate genuine conflict"

#: Categories in which the two sources are talking about the same subject, both
#: assert the property, and the values genuinely differ.
GENUINE = (TEMPORAL, CONTESTED_LABEL, UNEXPLAINED)


@dataclass(frozen=True)
class Pair:
    """One airport both sources assert a country for."""

    iata: str
    gid: str
    of_country: str
    gn_country: str
    of_name: str
    gn_name: str
    gn_feature: str
    of_icao: str
    gn_icao: str
    of_city: str
    lat: float
    lon: float

    @property
    def agrees(self) -> bool:
        return self.of_country == self.gn_country

    @property
    def icao_confirms(self) -> bool | None:
        """True/False if both sides carry an ICAO, None if the check is blind."""
        if not self.of_icao or not self.gn_icao:
            return None
        return self.of_icao == self.gn_icao


def data_root() -> Path:
    env = os.environ.get("SYMBOLIC_AI_DATA")
    if env:
        return Path(env).expanduser()
    here = Path(__file__).resolve().parents[1]
    if (here / "data" / "sources").exists():
        return here / "data"
    # Worktrees do not carry the (gitignored) bulk data; fall back to the
    # checkout they were cut from rather than reporting an empty corpus.
    for parent in here.parents:
        if (parent / "data" / "sources").exists():
            return parent / "data"
    return here / "data"


def parse_body(body: str) -> dict[str, str]:
    """``feature=S/AIRP country=AM pop=0`` -> a dict.

    Values are split on ``key=`` boundaries rather than on whitespace, because
    openflights' ``city=`` and ``country=`` hold names with spaces in them.
    """
    out: dict[str, str] = {}
    key, parts = None, []
    for tok in (body or "").split():
        if "=" in tok:
            head, _, tail = tok.partition("=")
            if key is not None:
                out[key] = " ".join(parts)
            key, parts = head, [tail] if tail else []
        else:
            parts.append(tok)
    if key is not None:
        out[key] = " ".join(parts)
    return out


def name_tokens(name: str) -> frozenset[str]:
    """Identity-bearing tokens of an airport name, accent- and case-folded."""
    flat = unicodedata.normalize("NFKD", name or "")
    flat = "".join(c for c in flat if not unicodedata.combining(c)).lower()
    flat = re.sub(r"\([^)]*\)", " ", flat)
    return frozenset(t for t in re.split(r"[^a-z0-9]+", flat)
                     if len(t) > 1 and t not in NAME_STOPWORDS)


def names_match(a: str, b: str) -> bool:
    """Do these two names plausibly denote the same airport?

    Deliberately permissive: its job is to catch a join that landed on a
    *different* airport (``Fontaine`` vs ``Bokeo International``), not to police
    spelling. A subset relation counts, so ``RAF Akrotiri`` matches
    ``Akrotiri Airfield`` and ``L'Esperance`` matches ``Grand Case-Esperance``.
    """
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return True          # no evidence either way; do not invent a rejection
    if ta <= tb or tb <= ta:
        return True
    return len(ta & tb) / len(ta | tb) >= 0.3


def load_openflights(root: Path) -> tuple[dict, dict]:
    """``kg:iata:XXX`` -> body dict, and -> ISO2 country from the edge."""
    base = root / "sources" / "openflights"
    nodes: dict[str, dict] = {}
    for f in sorted(base.rglob("airports*.parquet")):
        for row in pq.read_table(f).to_pylist():
            nodes[row["id"]] = dict(parse_body(row["body"]),
                                    _label=row["label"] or "")
    country: dict[str, str] = {}
    for f in sorted(base.rglob("routes*.parquet")):
        for batch in pq.ParquetFile(f).iter_batches(
                columns=["source_id", "target_id", "kind"]):
            for row in batch.to_pylist():
                if row["kind"] == "in-country":
                    country[row["source_id"]] = \
                        row["target_id"].rsplit(":", 1)[-1]
    return nodes, country


def load_geonames(root: Path) -> tuple[dict, dict, dict]:
    """IATA -> [geonames ids], geonames id -> ICAO, geonames id -> body."""
    base = root / "sources" / "geonames"
    by_iata: dict[str, list[str]] = collections.defaultdict(list)
    icao: dict[str, str] = {}
    for f in sorted(base.rglob("code_bridges*.parquet")):
        for row in pq.read_table(f).to_pylist():
            t = row["target_id"]
            if t.startswith("kg:iata:"):
                by_iata[t.rsplit(":", 1)[-1]].append(row["source_id"])
            elif t.startswith("kg:icao:"):
                icao[row["source_id"]] = t.rsplit(":", 1)[-1]
    wanted = {g for ids in by_iata.values() for g in ids}
    bodies: dict[str, dict] = {}
    for f in sorted(base.rglob("place_nodes*.parquet")):
        for batch in pq.ParquetFile(f).iter_batches(
                columns=["id", "label", "body"], batch_size=200_000):
            for row in batch.to_pylist():
                if row["id"] in wanted:
                    bodies[row["id"]] = dict(parse_body(row["body"]),
                                             _label=row["label"] or "")
    return dict(by_iata), icao, bodies


def icao_prefix_countries(of_nodes, of_country
                          ) -> dict[str, collections.Counter]:
    """2-letter ICAO prefix -> how often openflights asserts each ISO2 on it.

    Built from openflights alone. ICAO allocates the first two letters by
    region, so a prefix's country tally is a *self-declared* consistency check:
    an airport whose asserted country is asserted by no **other** airport on
    its own ICAO prefix is one openflights contradicts itself about.
    """
    out: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    for nid, body in of_nodes.items():
        icao = (body.get("icao") or "").strip()
        c = of_country.get(nid, "")
        if len(icao) == 4 and c:
            out[icao[:2]][c] += 1
    return dict(out)


def build_pairs(of_nodes, of_country, by_iata, gn_icao, gn_bodies):
    """The strict tier: one openflights airport, one geonames *aerodrome*."""
    pairs: list[Pair] = []
    stats: collections.Counter = collections.Counter()
    multi_gn_disagree: list[tuple[str, set[str]]] = []
    for nid, body in sorted(of_nodes.items()):
        iata = nid.rsplit(":", 1)[-1]
        stats["openflights airports"] += 1
        ofc = of_country.get(nid, "")
        if not ofc:
            stats["openflights asserts no country"] += 1
        cands = by_iata.get(iata, [])
        if not cands:
            stats["no geonames record for this IATA"] += 1
            continue
        stats["IATA reaches geonames"] += 1
        known = [g for g in cands if g in gn_bodies]
        seen = {gn_bodies[g].get("country", "") for g in known}
        seen.discard("")
        if len(seen) > 1:
            multi_gn_disagree.append((iata, seen))
        aero = [g for g in known
                if gn_bodies[g].get("feature", "").startswith(AERODROME)]
        if not aero:
            stats["geonames record is not an aerodrome"] += 1
            continue
        if len(aero) > 1:
            stats["ambiguous: >1 geonames aerodrome"] += 1
            continue
        gid = aero[0]
        gnc = gn_bodies[gid].get("country", "")
        if not ofc or not gnc:
            stats["one side asserts no country"] += 1
            continue
        stats["both sources assert a country"] += 1
        pairs.append(Pair(
            iata=iata, gid=gid, of_country=ofc, gn_country=gnc,
            of_name=body.get("_label", ""), gn_name=gn_bodies[gid]["_label"],
            gn_feature=gn_bodies[gid].get("feature", ""),
            of_icao=(body.get("icao") or "").strip(),
            gn_icao=gn_icao.get(gid, ""),
            of_city=body.get("city", ""),
            lat=float(body.get("lat", "nan") or "nan"),
            lon=float(body.get("lon", "nan") or "nan")))
    return pairs, stats, multi_gn_disagree


def of_incoherent(p: Pair, prefixes: dict[str, collections.Counter],
                  min_support: int = 4) -> bool:
    """Does openflights contradict *itself* about where this airport is?

    Leave-one-out on the ICAO prefix: the airport's own assertion is removed
    before asking whether any other airport on the prefix agrees with it. The
    prefix needs ``min_support`` airports before the rule is allowed to fire,
    which is what keeps it away from Kosovo (``BK*``, one airport) — and the
    leave-one-out is what keeps it away from Western Sahara, whose three
    airports sit on Morocco's ``GM*`` prefix and vouch for each other.
    """
    if len(p.of_icao) != 4:
        return False
    tally = prefixes.get(p.of_icao[:2])
    if tally is None or sum(tally.values()) < min_support:
        return False
    return tally[p.of_country] - 1 <= 0


def classify(p: Pair, prefixes: dict[str, collections.Counter]) -> str:
    """What kind of thing a disagreement is. Rules fire in order.

    The first two rules remove pairs where the two records are different
    airports — not a disagreement, a bad join. The vocabulary and granularity
    rules then remove pairs that are two renderings of the same fact. The
    self-incoherence rule comes *after* those, because a territory whose ISO
    code differs from its administering state (``TF*`` for Saint-Barthélemy)
    would otherwise look like an ingest defect. Only what is left is a
    disagreement about the world.
    """
    if p.icao_confirms is False:
        return JOIN_ERROR_ICAO
    if not names_match(p.of_name, p.gn_name):
        return JOIN_ERROR_NAME
    a, b = p.of_country, p.gn_country
    if b in RETIRED.get(a, ()) or a in RETIRED.get(b, ()):
        return VINTAGE
    if DEPENDENCY_OF.get(a) == b or DEPENDENCY_OF.get(b) == a or \
            DETACHED_FROM.get(a) == b or DETACHED_FROM.get(b) == a:
        return GRANULARITY
    if of_incoherent(p, prefixes):
        return OF_INCOHERENT
    if b in SUCCESSOR.get(a, ()) or a in SUCCESSOR.get(b, ()):
        return TEMPORAL
    if frozenset((a, b)) in CONTESTED:
        return CONTESTED_LABEL
    return UNEXPLAINED


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples", type=int, default=10,
                    help="disagreements to print for hand inspection")
    ap.add_argument("--all", action="store_true",
                    help="print every disagreement, not a sample")
    args = ap.parse_args()

    root = data_root()
    print(f"data root: {root}")
    of_nodes, of_country = load_openflights(root)
    print(f"openflights: {len(of_nodes)} airport nodes, "
          f"{len(of_country)} in-country edges")
    by_iata, gn_icao, gn_bodies = load_geonames(root)
    print(f"geonames: {len(by_iata)} distinct IATA codes bridged, "
          f"{len(gn_bodies)} bridged place records read, "
          f"{len(gn_icao)} ICAO bridges")

    pairs, stats, multi = build_pairs(
        of_nodes, of_country, by_iata, gn_icao, gn_bodies)
    prefixes = icao_prefix_countries(of_nodes, of_country)

    print("\n--- join funnel (subject key: IATA code; geonames side restricted "
          "to a unique aerodrome) ---")
    for k in ["openflights airports", "openflights asserts no country",
              "no geonames record for this IATA", "IATA reaches geonames",
              "geonames record is not an aerodrome",
              "ambiguous: >1 geonames aerodrome",
              "one side asserts no country",
              "both sources assert a country"]:
        print(f"  {stats[k]:6d}  {k}")

    conf = [p.icao_confirms for p in pairs]
    both = [c for c in conf if c is not None]
    named = sum(names_match(p.of_name, p.gn_name) for p in pairs)
    print("\n--- join precision, against two keys the join did not use ---")
    print(f"  {len(both):6d}  pairs where both sides carry an ICAO code")
    print(f"  {sum(both):6d}  of those agree on it "
          f"({(sum(both) / len(both) if both else 0):.4f})")
    print(f"  {len(conf) - len(both):6d}  pairs where the ICAO check is blind")
    print(f"  {named:6d}  pairs whose airport names match "
          f"({named / len(pairs) if pairs else 0:.4f})")

    agree = [p for p in pairs if p.agrees]
    dis = [p for p in pairs if not p.agrees]
    print("\n--- the property: country, ISO 3166-1 alpha-2 on both sides ---")
    print(f"  {len(pairs):6d}  subjects where both sources assert it")
    print(f"  {len(agree):6d}  agree")
    print(f"  {len(dis):6d}  disagree  "
          f"(rate {len(dis) / len(pairs) if pairs else 0:.5f})")

    fp = [p for p in agree if of_incoherent(p, prefixes)]
    fpn = [p for p in agree if not names_match(p.of_name, p.gn_name)]
    print("\n--- false-positive audit: the two filters, run on the pairs that "
          "AGREE (where they should almost never fire) ---")
    print(f"  {len(fp):6d}  agreeing pairs the self-incoherence rule would "
          f"flag ({len(fp) / len(agree) if agree else 0:.4f})")
    print(f"  {len(fpn):6d}  agreeing pairs the name filter would reject "
          f"({len(fpn) / len(agree) if agree else 0:.4f})")

    conf_pairs = [p for p in pairs
                  if p.icao_confirms and names_match(p.of_name, p.gn_name)]
    conf_dis = [p for p in conf_pairs if not p.agrees]
    print("\n--- the same property on the confirmed tier (ICAO agrees AND "
          "names match) ---")
    print(f"  {len(conf_pairs):6d}  subjects")
    print(f"  {len(conf_dis):6d}  disagree  "
          f"(rate {len(conf_dis) / len(conf_pairs) if conf_pairs else 0:.5f})")

    kind = {p.iata: classify(p, prefixes) for p in dis}
    buckets = collections.Counter(kind.values())
    print("\n--- what the disagreements are ---")
    for k in [JOIN_ERROR_ICAO, JOIN_ERROR_NAME, OF_INCOHERENT, VINTAGE,
              GRANULARITY, TEMPORAL, CONTESTED_LABEL, UNEXPLAINED]:
        print(f"  {buckets[k]:6d}  {k}")

    genuine = [p for p in dis if kind[p.iata] in GENUINE]
    strict = [p for p in dis if kind[p.iata] == CONTESTED_LABEL]
    print(f"\n  same subject, both assert, values genuinely differ: "
          f"{len(genuine)}")
    print(f"  of those, neither source is entitled to settle it: {len(strict)}")

    shown = dis if args.all else sorted(
        dis, key=lambda p: (kind[p.iata], p.iata))[:args.samples]
    print(f"\n--- {len(shown)} disagreements, for hand inspection ---")
    for p in sorted(shown, key=lambda p: (kind[p.iata], p.iata)):
        icao = ("icao ok" if p.icao_confirms
                else "ICAO MISMATCH" if p.icao_confirms is False else "no icao")
        print(f"  {p.iata}  of={p.of_country:2s} gn={p.gn_country:2s}  "
              f"{icao:13s}  {p.gn_feature:6s}  {p.lat:8.3f},{p.lon:9.3f}")
        print(f"        of: {p.of_name!r} (city={p.of_city!r}, "
              f"icao={p.of_icao})")
        print(f"        gn: {p.gn_name!r} ({p.gid}, icao={p.gn_icao or '-'})")
        print(f"        -> {kind[p.iata]}")

    print("\n--- the within-geonames hazard the strict tier avoids ---")
    print(f"  {len(multi):6d}  IATA codes whose own geonames records disagree "
          f"about country")

    print("\n--- verdict ---")
    if strict:
        print(f"  A genuine two-source property conflict EXISTS: {len(strict)} "
              f"airports where two sources assert different sovereigns and "
              f"neither is entitled to settle it "
              f"({', '.join(sorted(p.iata for p in strict))}).")
        print(f"  Broadest defensible count, including one-source-is-stale: "
              f"{len(genuine)}.")
    else:
        print("  NO genuine two-source property conflict on country. Every "
              "disagreement is a join artefact, an ingest defect, a retired "
              "code or a granularity choice.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
