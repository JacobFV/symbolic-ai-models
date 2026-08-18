"""What does scoped enumeration cost when the graph is dense?

`scripts/gleif_scoped_ambiguity.py` measured `possible_answers_scoped` on the
GLEIF ownership forest and got a spectacular number: 117,129 point queries in
0.3 s, p50 **zero** conflicts read, maximum **one**. But GLEIF is 92.2% leaves
with an ownership chain of median length 2, and the repo recorded a prediction
that the result would not survive a different topology:

> **Believed, not measured:** "Scoping buys little on a dense graph." Expected:
> large read sets, frequent refusal, `additive_bounds` inapplicable to shortest
> path, set propagation asked for constantly.
> (`notes/decisions/2026-08-18-drop-the-dense-graph-arm-and-measure-the-dependency-instead.md`)

This runs it. Same three mechanisms, same table, the opposite topology: the
openflights route network, 37,042 scheduled legs over 3,321 airports, where a
0.051% input error is already known to be amplified 8.3x-44x into the answers.

**The query class is minimum-hop routing under a range limit** — the query the
task exists for, and the one the prediction singles out as beyond
`additive_bounds`. A conflict is a **leg length**: the subject is one directed
leg, and the two competing values are the two geodesies the repo's own `geo`
kernel implements. Where they straddle the range limit, the two derivations
disagree about whether the leg can be flown at all, and no evidence in the
snapshot settles which geodesy the airline used.

Three mixtures, and every one of them is labelled where it stands:

* **REAL-19** — filed-real. The 19 legs of 37,042 on which Vincenty-on-WGS84 and
  haversine disagree about admissibility at 2,000 km. Nothing injected.
* **INJ-78** and **INJ-1582** — **INJECTED**, and every number carrying them
  says so. They exist because the real set is at a 0.051% conflict rate and the
  GLEIF mixtures were at 0.21% and 4.27% of their subjects; matching the *rate*
  is what makes the two tables comparable, and it is more important here than
  matching the mechanism.

Run: ``uv run python -u scripts/dense_graph_scoping.py`` (~230 s). From a
worktree, where ``data/`` is not checked out, point ``SYMBOLIC_AI_DATA`` at the
main checkout's ``data/``.
"""

from __future__ import annotations

import collections
import random
import time
from pathlib import Path
from typing import Hashable, Mapping, Sequence

from symbolic_ai_adapters import load_airports, load_routes
from symbolic_ai_core.runtime.ambiguity import (Alternatives,
                                                AmbiguityExplosion,
                                                additive_bounds, exposure,
                                                possible_answers,
                                                possible_answers_scoped)
from symbolic_ai_core.runtime.ambiguity import _Recording
from symbolic_ai_core.source import SourceRegistry, data_root
from symbolic_ai_kernels.geo import distance_km, haversine_km
from symbolic_ai_tasks.range_limited_routing import build_network

PREDICATE = "geo.leg_km"
LIMIT_KM = 2000.0
CAP = 6
SEED = 20260818
USD_PER_CORE_SECOND = 0.02 / 3600.0            # cost.py's price sheet


def key_of(leg: tuple[str, str]) -> tuple[str, tuple[str, str]]:
    return (PREDICATE, leg)


# --------------------------------------------------------------------------
# The graph
# --------------------------------------------------------------------------
def load() -> tuple[dict[str, tuple[str, ...]], dict[tuple[str, str], float],
                    dict[tuple[str, str], float]]:
    base = next(s for s in SourceRegistry().snapshots().values()
                if s.source == "openflights").resolve(data_root())
    air = load_airports(base)
    edges, _ = load_routes(base, known=air.world.entities)
    pos = {i: (e.facets["geo.place"].values["lat"],
               e.facets["geo.place"].values["lon"])
           for i, e in air.world.entities.items()}
    exact = build_network(pos, edges)
    approx = build_network(pos, edges, metric=haversine_km)
    # Sorted adjacency, so the read set is a deterministic function of the
    # query rather than of the interpreter's hash seed.
    adj = {u: tuple(sorted(vs)) for u, vs in exact.adjacency.items()}
    return adj, dict(exact.length_km), dict(approx.length_km)


# --------------------------------------------------------------------------
# The computation, written so that it reads a conflict only when it looks at
# that leg. This is the whole contract `possible_answers_scoped` rests on.
# --------------------------------------------------------------------------
def min_hops_under(adj: Mapping[str, Sequence[str]],
                   length: Mapping[tuple[str, str], float],
                   source: str, target: str,
                   assignment: Mapping[Hashable, float],
                   *, limit: float = LIMIT_KM, cap: int = CAP) -> int | None:
    """Fewest flyable legs from source to target, under one assignment.

    A leg's length is taken from the assignment when that leg is one of the
    disputed ones and from the settled measurement otherwise. `_Recording`
    raises `KeyError` for a subject that is not in the mixture and records
    nothing, so `k in assignment` reads exactly the conflicts consulted.
    """
    if source == target:
        return 0
    seen = {source}
    frontier = [source]
    for hop in range(1, cap + 1):
        nxt: set[str] = set()
        for u in frontier:
            for v in adj.get(u, ()):
                if v in seen:
                    continue
                k = key_of((u, v))
                d = assignment[k] if k in assignment else length[(u, v)]
                if d <= limit:
                    nxt.add(v)
        nxt -= seen
        if target in nxt:
            return hop
        if not nxt:
            return None
        seen |= nxt
        frontier = sorted(nxt)
    return None


# --------------------------------------------------------------------------
# The mixtures
# --------------------------------------------------------------------------
def mixture_real(exact: Mapping[tuple[str, str], float],
                 approx: Mapping[tuple[str, str], float]) -> Alternatives:
    """Filed-real: legs where the two geodesies straddle the range limit.

    Every one of the 37,042 legs has two different values under the two
    derivations, but a 0.5% length disagreement that leaves the leg on the same
    side of the limit is invisible to this query class and is not a conflict
    the answer can see. Filtering to the material ones uses knowledge of the
    query, which is stated rather than hidden; the unfiltered mixture is
    reported too, in one line, because it is the honest upper end.
    """
    choices = {key_of(e): (d, approx[e]) for e, d in exact.items()
               if (d <= LIMIT_KM) != (approx[e] <= LIMIT_KM)}
    return Alternatives(choices)


def mixture_injected(exact: Mapping[tuple[str, str], float], rate: float,
                     seed: int) -> Alternatives:
    """INJECTED. A `rate` fraction of legs get a second, admissibility-flipping
    value, drawn at the rate the GLEIF mixtures ran at.

    The perturbation is the smallest one that is visible to this query: a leg
    the exact metric admits also carries a value just over the limit, and one
    it excludes also carries a value just under. That is the same *kind* of
    disagreement as REAL-19 — two derivations, one leg, opposite verdicts on
    whether it can be flown — reproduced at a chosen rate.
    """
    rng = random.Random(seed)
    legs = sorted(exact)
    picked = rng.sample(legs, int(round(rate * len(legs))))
    choices = {}
    for e in picked:
        d = exact[e]
        other = LIMIT_KM + 1.0 if d <= LIMIT_KM else LIMIT_KM - 1.0
        choices[key_of(e)] = (d, other)
    return Alternatives(choices)


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
def pct(values: list[int], q: float) -> int:
    s = sorted(values)
    return s[min(len(s) - 1, int(q * len(s)))]


def first_pass_read(adj, length, alts: Alternatives, s: str, t: str,
                    cap: int = CAP) -> int:
    """How many conflicts one run of the query looks at.

    The diagnostic `possible_answers_scoped` does not expose on a refusal: it
    raises at the *top* of the next round, so `exc.read` is the read set of the
    round before and is a lower bound. This is the actual reach of one pass.
    """
    rec = _Recording({}, alts.choices)
    min_hops_under(adj, length, s, t, rec, cap=cap)
    return len(rec.read)


def edges_examined(adj: Mapping[str, Sequence[str]],
                   length: Mapping[tuple[str, str], float],
                   source: str, target: str, *, cap: int = CAP) -> int:
    """The query's **read footprint**: how many legs it looks at at all.

    This is the variable the read set is proportional to, and it is the one
    that separates the two topologies. A GLEIF point query walks an ownership
    chain of median length 2, so it examines 2 edges; a min-hop search on a
    graph whose median out-degree is double digits examines thousands.
    """
    if source == target:
        return 0
    seen = {source}
    frontier = [source]
    looked = 0
    for _ in range(1, cap + 1):
        nxt: set[str] = set()
        for u in frontier:
            for v in adj.get(u, ()):
                if v in seen:
                    continue
                looked += 1
                if length[(u, v)] <= LIMIT_KM:
                    nxt.add(v)
        nxt -= seen
        if target in nxt or not nxt:
            return looked
        seen |= nxt
        frontier = sorted(nxt)
    return looked


# --------------------------------------------------------------------------
# Arm 1: the point query
# --------------------------------------------------------------------------
def arm_point_query(name: str, adj, length, alts: Alternatives,
                    pairs: list[tuple[str, str]]) -> dict:
    print(f"\n=== {name}: min-hop routing under {LIMIT_KM:.0f} km, "
          f"{len(alts.choices)} conflicts, cap={CAP} ===")
    print(f"  world_count of the whole mixture = 2^{len(alts.choices)}")
    try:
        possible_answers(
            lambda a: min_hops_under(adj, length, *pairs[0], a), alts)
        print("  full enumeration: DID NOT REFUSE -- unexpected")
    except AmbiguityExplosion:
        print("  full enumeration: refused, as it must")

    reads, refused_reads, answered, refused, undetermined = [], [], 0, 0, 0
    t0 = time.perf_counter()
    for s, t in pairs:
        try:
            got = possible_answers_scoped(
                lambda a, s=s, t=t: min_hops_under(adj, length, s, t, a), alts)
            answered += 1
            reads.append(len(got.read))
            if got.ambiguous:
                undetermined += 1
        except AmbiguityExplosion as exc:
            refused += 1
            refused_reads.append(len(exc.read))
    wall = time.perf_counter() - t0

    t1 = time.perf_counter()
    for s, t in pairs:
        min_hops_under(adj, length, s, t, {})
    collapsed = time.perf_counter() - t1

    n = len(pairs)
    fp = [first_pass_read(adj, length, alts, s, t) for s, t in pairs]
    print(f"  queries attempted: {n}")
    print(f"    answered: {answered} ({answered/n*100:.1f}%)   "
          f"REFUSED (AmbiguityExplosion): {refused} ({refused/n*100:.1f}%)")
    print(f"  conflicts read per query, one pass (the query's true reach): "
          f"p50={pct(fp,0.5)} p90={pct(fp,0.9)} max={max(fp)} "
          f"mean={sum(fp)/n:.1f}")
    if reads:
        print(f"  conflicts read per *answered* query: p50={pct(reads,0.5)} "
              f"p90={pct(reads,0.9)} max={max(reads)}")
    if refused_reads:
        print(f"  conflicts named by the refusal: p50={pct(refused_reads,0.5)} "
              f"p90={pct(refused_reads,0.9)} max={max(refused_reads)}")
    print(f"  answers undetermined (>1 distinct answer): {undetermined} "
          f"({undetermined/n*100:.3f}% of attempted, "
          f"{undetermined/max(1,answered)*100:.3f}% of answered)")
    print(f"  wall: {wall:.2f}s over {n} queries = {wall/n*1e6:.1f} us each")
    print(f"  collapsed (one world, no mixture): {collapsed:.2f}s = "
          f"{collapsed/n*1e6:.1f} us each")
    print(f"  retention ratio vs collapsing: {wall/collapsed:.2f}x   "
          f"(${wall*USD_PER_CORE_SECOND/n:.2e} per attempted query)")
    foot = [edges_examined(adj, length, s, t) for s, t in pairs]
    rate = len(alts.choices) / len(length)
    print(f"  read footprint (legs examined per query): p50={pct(foot,0.5):,} "
          f"p90={pct(foot,0.9):,} max={max(foot):,}   "
          f"[GLEIF point query: 2]")
    print(f"  conflict rate x footprint = {rate:.5f} x {sum(foot)/n:,.0f} = "
          f"{rate*sum(foot)/n:.2f} expected conflicts read; the bound is "
          f"log2(1024) = 10")
    return {"name": name, "conflicts": len(alts.choices), "n": n,
            "answered": answered, "refused": refused,
            "read_p50": pct(fp, 0.5), "read_p90": pct(fp, 0.9),
            "read_max": max(fp), "undetermined": undetermined,
            "us_per_query": wall / n * 1e6, "retention": wall / collapsed}


# --------------------------------------------------------------------------
# Arm 2: the reach ladder. Where does it break?
# --------------------------------------------------------------------------
def arm_reach_ladder(adj, length, alts: Alternatives,
                     pairs: list[tuple[str, str]], label: str) -> None:
    print(f"\n=== reach ladder on {label}: is it the topology, or the "
          f"query's reach? ===")
    print("  cap  answered  refused  read_p50  read_p90  read_max  us/query")
    for cap in (1, 2, 3, 4, 6):
        reads, answered, refused = [], 0, 0
        t0 = time.perf_counter()
        for s, t in pairs:
            try:
                possible_answers_scoped(
                    lambda a, s=s, t=t, cap=cap: min_hops_under(
                        adj, length, s, t, a, cap=cap), alts)
                answered += 1
            except AmbiguityExplosion:
                refused += 1
        wall = time.perf_counter() - t0
        for s, t in pairs:
            rec = _Recording({}, alts.choices)
            min_hops_under(adj, length, s, t, rec, cap=cap)
            reads.append(len(rec.read))
        print(f"  {cap:>3}  {answered:>8}  {refused:>7}  {pct(reads,0.5):>8}  "
              f"{pct(reads,0.9):>8}  {max(reads):>8}  "
              f"{wall/len(pairs)*1e6:>8.0f}")


# --------------------------------------------------------------------------
# Arm 3: the anchor. Scoped must equal full enumeration.
# --------------------------------------------------------------------------
def arm_anchor(adj, length, alts: Alternatives, pairs: list[tuple[str, str]],
               *, k: int = 8, sample: int = 60) -> None:
    print(f"\n=== ANCHOR: scoped == full enumeration on a {k}-conflict "
          f"sub-mixture ({2**k} worlds) ===")
    small = Alternatives(dict(sorted(alts.choices.items(), key=repr)[:k]))
    live = [(s, t) for s, t in pairs
            if first_pass_read(adj, length, small, s, t) > 0][:sample]
    same = 0
    for s, t in live:
        full = possible_answers(
            lambda a, s=s, t=t: min_hops_under(adj, length, s, t, a),
            small, max_worlds=2 ** k)
        scoped = possible_answers_scoped(
            lambda a, s=s, t=t: min_hops_under(adj, length, s, t, a),
            small, max_worlds=2 ** k)
        same += set(full.answers) == set(scoped.answers)
    print(f"  identical answer sets on {same}/{len(live)} pairs "
          f"(pairs that read at least one of the {k})")
    if same != len(live):
        print("  *** ANCHOR FAILED -- this outranks the topology question ***")


# --------------------------------------------------------------------------
# Arm 4: how much of the read set is a real dependency?
# --------------------------------------------------------------------------
def arm_over_approximation(adj, length, alts: Alternatives,
                           pairs: list[tuple[str, str]], *,
                           sample: int = 40) -> None:
    print("\n=== read set vs effective dependency: of the conflicts a query "
          "reads, how many can change its answer? ===")
    read_tot = live_tot = 0
    checked = 0
    for s, t in pairs[:sample]:
        rec = _Recording({}, alts.choices)
        base = min_hops_under(adj, length, s, t, rec)
        read = sorted(rec.read, key=repr)
        if not read:
            continue
        checked += 1
        live = 0
        for kk in read:
            flipped = {kk: alts.choices[kk][1]}
            if min_hops_under(adj, length, s, t, flipped) != base:
                live += 1
        read_tot += len(read)
        live_tot += live
    if checked:
        print(f"  over {checked} queries: {read_tot} conflicts read, "
              f"{live_tot} of them change the answer when flipped alone "
              f"({live_tot/read_tot*100:.2f}%) -- "
              f"the recorder over-approximates by "
              f"{read_tot/max(1,live_tot):.0f}x")


# --------------------------------------------------------------------------
# Arm 5: exposure, and additive_bounds
# --------------------------------------------------------------------------
def arm_exposure_and_bounds(adj, length, alts: Alternatives) -> None:
    print("\n=== exposure and additive_bounds on this topology ===")
    limited: dict[str, list[str]] = collections.defaultdict(list)
    for (u, v), d in length.items():
        if d <= LIMIT_KM:
            limited[u].append(v)
    keys = sorted(alts.choices, key=repr)[:200]
    exps = sorted(exposure(k[1][1], limited) for k in keys)
    print(f"  exposure of the conflicted legs' head nodes (n={len(exps)}): "
          f"min={exps[0]} p50={exps[len(exps)//2]} max={exps[-1]}   "
          f"[GLEIF: 1 to 3,848 -- four orders of magnitude]")
    print(f"  spread max/min = {exps[-1]/max(1,exps[0]):.1f}x; "
          f"rank_by_exposure can only discriminate what the spread allows")

    # additive_bounds: applicable to an edge count, not to a hop count.
    base = sum(1 for e, d in length.items()
               if d <= LIMIT_KM and key_of(e) not in alts.choices)
    b = additive_bounds(alts, lambda s, v: 1.0 if v <= LIMIT_KM else 0.0,
                        base=float(base))
    print(f"  additive_bounds on 'how many legs are flyable': "
          f"[{b.low:.0f}, {b.high:.0f}] over 2^{len(alts.choices)} worlds, "
          f"width {b.width:.0f} -- exact and attained, because the terms are "
          f"independent")
    print("  additive_bounds on min-hops: INAPPLICABLE. A hop count is a "
          "minimum over paths, not a sum of per-subject terms, and the "
          "interface refuses to express it (contribution sees one subject).")


def main() -> None:
    t0 = time.perf_counter()
    adj, exact, approx = load()
    nodes = sorted(adj)
    print(f"openflights: {len(exact):,} legs over {len(nodes):,} airports "
          f"with outbound routes, loaded in {time.perf_counter()-t0:.1f}s")
    deg = [len(v) for v in adj.values()]
    print(f"  out-degree: p50={pct(deg,0.5)} p90={pct(deg,0.9)} max={max(deg)}")
    flyable = sum(1 for d in exact.values() if d <= LIMIT_KM)
    print(f"  legs flyable at {LIMIT_KM:.0f} km: {flyable:,} "
          f"({flyable/len(exact)*100:.1f}%)")

    rng = random.Random(SEED)
    all_nodes = sorted(set(adj) | {v for vs in adj.values() for v in vs})
    pairs = [(rng.choice(nodes), rng.choice(all_nodes)) for _ in range(250)]
    pairs = [(s, t) for s, t in pairs if s != t]
    ladder_pairs = pairs[:120]
    print(f"  query sample: {len(pairs)} random (source, target) pairs, "
          f"seed {SEED} -- SUBSAMPLED from {len(nodes):,} x {len(all_nodes):,} "
          f"possible pairs because a scoped enumeration that answers costs "
          f"2^read searches at ~760 us each. The reach ladder uses the first "
          f"{len(ladder_pairs)} of the same sample.")

    real = mixture_real(exact, approx)
    print(f"\nREAL-19 mixture: {len(real.choices)} legs of {len(exact):,} "
          f"({len(real.choices)/len(exact)*100:.3f}%) on which Vincenty and "
          f"haversine disagree about admissibility at {LIMIT_KM:.0f} km. "
          f"FILED-REAL, nothing injected.")
    print(f"  (unfiltered: all {len(exact):,} legs carry two different values, "
          f"so the honest upper-end mixture is 2^{len(exact)} and every query "
          f"reads thousands of them -- reported here and not run)")

    rows = [arm_point_query("REAL-19 (filed-real)", adj, exact, real, pairs)]
    arm_anchor(adj, exact, real, pairs)
    arm_reach_ladder(adj, exact, real, ladder_pairs, "REAL-19 (filed-real)")
    arm_over_approximation(adj, exact, real, pairs)
    arm_exposure_and_bounds(adj, exact, real)

    for rate, tag in ((251 / 117129, "INJ-78"), (4992 / 117129, "INJ-1582")):
        alts = mixture_injected(exact, rate, SEED)
        print(f"\n\n########## {tag} -- INJECTED at {rate*100:.3f}% of legs, "
              f"the rate the GLEIF mixture ran at "
              f"({'251' if tag == 'INJ-78' else '4,992'}/117,129 subjects)")
        rows.append(arm_point_query(f"{tag} (INJECTED)", adj, exact, alts,
                                    pairs))
        arm_anchor(adj, exact, alts, pairs)
        arm_reach_ladder(adj, exact, alts, ladder_pairs, f"{tag} (INJECTED)")
        arm_exposure_and_bounds(adj, exact, alts)

    print("\n\n########## the table, against the GLEIF row")
    hdr = ("mixture", "conflicts", "queries", "refused", "read p50",
           "read p90", "read max", "undet.", "us/query", "retention")
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))
    print("| GLEIF 251 (filed-real) | 251 | 117,129 | 0 | 0 | 0 | 1 | "
          "0.216% | 2.8 | 2.8x |")
    print("| GLEIF 4,992 (closure) | 4992 | 117,129 | 0 | 0 | 0 | 1 | "
          "4.274% | 2.8 | 3.4x |")
    for r in rows:
        print(f"| {r['name']} | {r['conflicts']} | {r['n']} | "
              f"{r['refused']} ({r['refused']/r['n']*100:.0f}%) | "
              f"{r['read_p50']} | {r['read_p90']} | {r['read_max']} | "
              f"{r['undetermined']/r['n']*100:.3f}% | "
              f"{r['us_per_query']:.0f} | {r['retention']:.2f}x |")
    print(f"\ntotal wall: {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    main()
