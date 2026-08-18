---
title: Scoping survives a dense graph on the conflicts that are actually there — the recorded prediction is half wrong, and what breaks first is wall time, not refusal
date: 2026-08-18
status: provisional
tags: [ambiguity, scoping, topology, routing, openflights, real-data, cost]
---

## The prediction this was run against

`HANDOVER.md` §4 carries it as *believed, not measured*, and
`notes/decisions/2026-08-18-drop-the-dense-graph-arm-and-measure-the-dependency-instead.md`
records the decision not to run it:

> **Scoping buys little on a dense graph.** Expected: large read sets, frequent
> refusal, `additive_bounds` inapplicable to shortest path, set propagation
> asked for constantly. **If you find otherwise, that is publishable.**

The handover is right that the topologies are opposites. GLEIF ownership is
92.2% leaves, ownership chain p50 2, error amplification 1.0x. The openflights
route network measured here is 37,042 scheduled legs over 3,241 airports with
outbound routes, out-degree p50 3 / p90 30 / **max 239**, and a known error
amplification of 8.3x–44x.

**Scouting arm.** No refuter, no permutation control, no floor audit — the
number's job is to decide whether the dense-graph direction is worth a deep
pass, not to go into `RESEARCH_LOG.md`. Two arms are **INJECTED** and say so in
every row.

Reproduce: `uv run python -u scripts/dense_graph_scoping.py` (230 s).

## What was built, and what is real versus injected

**Query class: minimum-hop routing under a 2,000 km range limit.** Chosen over
country-of-destination because it is the query the task exists for, it is the
one the prediction singles out as beyond `additive_bounds`, and it is the query
whose read footprint the dense topology actually changes — a country lookup
reads one fact on any graph.

**A conflict is a leg length.** The subject is one directed leg; the two
competing values are the two geodesies `symbolic_ai_kernels/geo.py` implements.
Where they straddle the range limit, the two derivations disagree about whether
the leg can be flown at all. That is the same *kind* of object as the GLEIF
conflict — one subject, two derivations, no evidence entitled to settle it.

| mixture | conflicts | rate | provenance |
|---|---:|---:|---|
| **REAL-19** | 19 | 0.051% of legs | **FILED-REAL.** Vincenty-on-WGS84 vs haversine, disagreeing about admissibility at 2,000 km. Nothing injected. |
| **INJ-78** | 79 | 0.213% | **INJECTED**, at GLEIF's 251/117,129 rate |
| **INJ-1582** | 1,579 | 4.262% | **INJECTED**, at GLEIF's 4,992/117,129 rate |

Stated rather than hidden: REAL-19 is filtered to conflicts that are *material
to this query class*. All 37,042 legs carry two different values under the two
geodesies; a 0.5% length disagreement that leaves the leg on the same side of
the limit is invisible to a hop count. The unfiltered mixture is 2^37,042 and
every query reads thousands of it — reported, not run. The injected arms exist
because matching the GLEIF *rate* is what makes the two tables comparable, and
the brief is explicit that rate matters more than mechanism.

Queries: **250 random (source, target) pairs, seed 20260818**, subsampled from
3,241 x 3,257 because a scoped enumeration that answers costs 2^read searches at
~760 µs each. The reach ladder uses the first 120 of the same sample.

## The table, against the GLEIF row

| mixture | conflicts | queries | REFUSED | read p50 | read p90 | read max | undet. | µs/query | retention |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GLEIF 251 (filed-real) | 251 | 117,129 | 0 | 0 | 0 | **1** | 0.216% | **2.8** | 2.8x |
| GLEIF 4,992 (closure) | 4,992 | 117,129 | 0 | 0 | 0 | **1** | 4.274% | **2.8** | 3.4x |
| **REAL-19 (filed-real)** | 19 | 250 | **0 (0%)** | 1 | 6 | 8 | 0.000% | **48,271** | 43.1x |
| **INJ-78 (INJECTED)** | 79 | 250 | 56 (22%) | 5 | 12 | 16 | 0.800% | 337,878 | **357.5x** |
| **INJ-1582 (INJECTED)** | 1,579 | 250 | **244 (98%)** | 137 | 262 | 323 | 0.000% | 2,376 | 1.8x |

`read` is the conflicts one pass of the query looks at — the query's true reach.
`possible_answers_scoped` raises at the *top* of the next round, so `exc.read`
on a refusal is the round before and is a lower bound; the column above is
measured directly with a recording assignment so refused and answered rows are
the same quantity.

**ANCHOR: 179/179.** On an 8-conflict sub-mixture (256 worlds), scoped
enumeration and full `possible_answers` return identical answer sets on 60/60,
60/60 and 59/59 pairs across the three mixtures. There is no scoping bug; the
topology question stands.

## Did the prediction hold? Half.

| predicted | measured | verdict |
|---|---|---|
| large read sets | REAL-19: p50 **1**, max **8** — against GLEIF's p50 0, max 1 | **FALSE on the real mixture.** True only once the rate is injected up to GLEIF's own (p50 5) and beyond (p50 137) |
| frequent refusal | REAL-19: **0 of 250** | **FALSE on the real mixture.** True at rate-matched injection: 22%, then 98% |
| `additive_bounds` inapplicable to shortest path | confirmed, structurally | **TRUE** |
| set propagation asked for constantly | not tested — the set-propagation control was out of scouting scope | **UNTESTED**, and it should stay in the parking lot rather than be inherited |

So the headline is the one the handover said would be publishable: **on the
conflicts that are actually in the data, scoped enumeration works on the dense
graph.** Every query was answered, the read set never exceeded 8 of 19, and the
answer was exact.

## But the interesting half is *what* degraded, because it is not what was named

Wall time. **48.3 ms per query against GLEIF's 2.8 µs — 17,000x** — at a
conflict rate 4x *below* GLEIF's and with zero refusals. Retention costs 43x
over collapsing the mixture, against GLEIF's 2.8x. Priced at `cost.py`'s
$0.02/core-hour that is **$2.7e-07 per query against $1.6e-11**.

Refusal is the *second* thing to break, and read-set size is not really a
separate failure from it. The order is: **wall time, then refusal.** Which
matters, because a refusal is a contract the caller can act on — it names the
conflicts to settle — and a 17,000x slowdown that returns a correct answer is
invisible until it is in a budget.

### The variable is neither the topology nor the conflict count

It is **conflict rate x read footprint**, and the script measures both halves.
A GLEIF point query walks an ownership chain of median length 2, so it examines
**2 legs-equivalent**. A min-hop search here examines **p50 3,262, p90 6,171,
max 7,734** — a ~1,600x footprint. That product predicts the refusal column:

| | rate | footprint (mean) | product | bound is log2(1024) = 10 | refused |
|---|---:|---:|---:|---|---:|
| GLEIF 251 | 0.00214 | 2 | **0.004** | far under | 0% |
| REAL-19 | 0.00051 | 3,468 | **1.78** | under | 0% |
| INJ-78 | 0.00213 | 3,468 | **7.40** | at the edge | 22% |
| INJ-1582 | 0.04263 | 3,468 | **147.8** | far over | 98% |

GLEIF's headline was not a property of a forest. It was a property of a query
that reads two facts. Put the *same conflict rate* on a query that reads three
thousand and scoping refuses a fifth of the time.

### The reach ladder: the graph is safe, the query is not

Same graph, same mixture, only the hop cap moves.

REAL-19 (filed-real), 120 pairs:

| cap | answered | refused | read p50 | read p90 | read max | µs/query |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 120 | 0 | 0 | 0 | 0 | **10** |
| 2 | 120 | 0 | 0 | 1 | 5 | 1,084 |
| 3 | 120 | 0 | 0 | 3 | 6 | 6,030 |
| 4 | 120 | 0 | 0 | 4 | 7 | 10,626 |
| 6 | 120 | 0 | 1 | 6 | 8 | **45,876** |

INJ-78 (INJECTED): refusal appears at cap 2 (1/120) and reaches 26/120 at cap 6,
with µs/query 8 → 338,668. INJ-1582 (INJECTED): 0/120 refused at cap 1, 44/120
at cap 2, 115/120 at cap 6.

A 1-hop question on this graph costs **10 µs and reads nothing**. It is not the
density that scoping cannot pay for; it is reach. That is the actionable line:
scoping is a per-query-class property, and the class is defined by read
footprint, not by which graph it runs on.

## Two things that degraded worse than predicted, and one that did not

**`exposure` and `rank_by_exposure` go nearly flat.** On GLEIF, exposure spans
**1 to 3,848** — four orders of magnitude — which is what makes "rank conflicts
by consequence and spend evidence on the expensive ones" a real instrument.
Here the conflicted legs' head nodes have exposure **1,193 to 1,957, a spread of
1.6x** (REAL-19; 10 to 1,957, 196x, over 200 sampled conflicts of INJ-1582,
where the sample reaches leaf-ish nodes). Almost every node reaches the same
giant component, so the ranking carries almost no information. The prediction
did not mention this and it is the sharper loss: refusal is at least
actionable, a degenerate priority order is not.

**The read set stops being the dependency.** Over 23 REAL-19 queries that read
anything, **66 conflicts were read and 0 of them changed the answer when flipped
alone** — the recorder over-approximates the effective dependency by ~66x on
this sample. On the forest the read set was tight (max 1, and 0.216% of answers
genuinely undetermined). This is the real cost to the certificate line in
`HANDOVER.md` §7 item 1: "here is the answer and everything it rests on" becomes
a certificate naming 66 facts, none of which mattered. Caveat: single-flip is a
*lower bound* on liveness, and 0/250 undetermined on REAL-19 is a small-sample
number — the published `answer_sensitivity` figure for these same 19 legs is
0.427% of answers changed, which predicts ~1 in 250. The two are consistent;
neither is a tight estimate.

**`additive_bounds` behaved exactly as predicted, in both directions.** Exact
and attained where the answer is a sum of independent per-subject terms —
"how many legs are flyable" is `[27,261, 27,280]` over 2^19 worlds and
`[26,079, 27,658]` over 2^1,579 — and structurally inexpressible for a hop
count, because a minimum over paths is not a sum and `contribution` sees one
subject. That is the interface refusing to express an unattainable bound, which
is the behaviour it was designed for.

## The trap in the retention ratio

It is **non-monotone**: 43x, then 357x, then **1.8x**. The worst mixture is the
*cheapest*, because a refusal costs one search and returns immediately. So the
retention ratio must never be quoted without the refusal rate beside it — on its
own it says the 1,579-conflict world is 24x easier than the 19-conflict one,
which is exactly backwards. The expensive regime is the **boundary**: queries
whose read set lands just under the 1,024-world bound pay 2^10 searches to
answer.

## What would have refuted the headline

- The anchor disagreeing on any pair. It did not: **179/179**.
- REAL-19 refusing on a meaningful share of queries, or p50 read > 2. Neither:
  0/250 and p50 1.
- The `rate x footprint` product failing to order the refusal rates. It ordered
  them 0.004 / 1.78 / 7.40 / 147.8 against 0% / 0% / 22% / 98%.

## What this changes

1. **`HANDOVER.md` §4's "scoping buys little on a dense graph" should be struck
   and replaced** with: *scoping's cost is `conflict rate x read footprint`, and
   topology enters only through the footprint.* The prediction named the wrong
   variable, which is why it got the direction right on the injected arms and
   wrong on the real one.
2. **Quote the read footprint next to every scoping number.** GLEIF's 2.8 µs is
   a two-fact query; it was never evidence about graphs.
3. **The certificate line (§7 item 1) has a measured obstacle now.** A read set
   that over-approximates 66x is a weak certificate. The cheap fix worth a next
   arm: a second pass that drops from the read set every conflict whose flip
   does not change the answer, which is `|read|` extra runs and turns an
   over-approximate certificate into a minimal one.
4. **Do not chase set propagation on this graph.** It stays in the parking lot,
   untested, and must not be inherited as either confirmed or refuted.
