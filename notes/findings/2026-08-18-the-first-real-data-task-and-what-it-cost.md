---
title: The first task on data I did not author — hub structure survives a geographic control by 10x, and my reachability prediction was wrong by 12x
date: 2026-08-18
status: provisional
tags: [real-data, geo, datalog, cost, openflights]
---

## Why this one

Every priced number in this repo — the $2.15e-8 per solved episode, the routing
headroom, the margin curve — came from a world I generated. The named gap was
"a task not of my design". Openflights supplies one: 6,072 airports with real
coordinates and 37,042 real scheduled routes, built by strangers for their own
reasons.

## Predictions, before the numbers

1. Median direct-route great-circle distance **under 1,000 km**.
2. 2-hop reachable set from a random routed airport covers **over 50%** of the
   network.
3. Control that must fail: a degree-preserving rewiring to nearest geographic
   neighbours will **not** match the real network's reach.

## What I found

| | measured |
|---|---|
| median route length | **1,152 km** (predicted <1,000 — wrong) |
| p10 / p90 / max | 294 / 3,706 / 13,804 km |
| median random airport pair | 8,536 km |
| 2-hop reach, random airport | **0.072 mean, 0.039 median** (predicted >0.50 — **wrong by 12x**) |
| 3-hop reach, random airport | 0.366 |
| 2-hop reach, top-50 hubs | 0.423 |
| 3-hop reach, top-50 hubs | 0.835 |
| out-degree | median **3**, mean 11.4, p90 30, max 239 |

**Prediction 2 was not slightly wrong, it was the wrong mental model.** I had
"everything is two hops from a hub" in mind. That is true *of hubs* — the top 50
reach 42% in two hops and 84% in three. It is false of the network, because the
median airport has **three** outbound routes. Averaging over airports and
averaging over passengers are different questions and I conflated them.

Routes are strongly geographic in length: 1,152 km median against 8,536 km for a
random pair, a factor of 7.4.

## The control, which failed as required

Degree-preserving rewiring — every airport keeps its exact out-degree, edges go
to its nearest neighbours on the sphere:

| | real | geographic control |
|---|---|---|
| 2-hop reach | 0.072 | **0.016** |
| 3-hop reach | 0.366 | **0.035** |

**10.5x at three hops.** So the real network's reach is not a consequence of its
density or of geography — there is genuine long-range structure that a distance
matched graph with identical degrees does not have. That is the one claim here
strong enough to keep.

## What it cost, against the alternative

Ingest of 6,072 airports and 37,042 edges: **0.11 s**. One thousand shortest
path queries: **0.542 s**, i.e. **542 µs/query**, 951 of 1,000 connected within
six hops. At a commodity vCPU rate that is on the order of **$1.5e-8 per query**.

The same question put to a language model requires giving it the graph:
**~233k tokens** of edges. One query at a Haiku-class $1/Mtok is **$0.233**;
with 90% caching across a batch of a thousand, **$0.023/query**. Opus-class,
**$3.49** uncached.

**That is a factor of roughly 1.5 million against the cheapest LLM path**, and
the symbolic answer is exact while the LLM's is a guess over a context it cannot
reliably traverse.

The honest half: this is only a comparison for a **closed-form question over a
large graph**. "How many hops from Goroka to Heathrow" is that. "Why did this
airline drop this route" is not, and the ratio there is undefined because the
symbolic system cannot answer it at all.

## What it says about the kernels

The geo kernel did real work here — `distance_km`, Vincenty on WGS84 — and the
route reachability is datalog's shape. Both earned their place on this task.
But it also took an adapter to get here, and the adapter had to **assert the
CRS**: openflights states no datum in any field, so `EPSG:4326` rides on every
facet with a citation to the published documentation rather than as a default.
That is the architecture doing what it claimed — the assumption is visible and a
reader can disagree with it.

## Limits

- One source, one question shape. 3,257 of 6,072 airports have any route at all,
  so any floor assuming a connected gazetteer is wrong.
- The 1.5-million-fold cost ratio prices *this* query against *that* alternative.
  It is not a general claim about symbolic versus neural.
- No floor and no $/solved-episode-above-floor yet, because "shortest path" has
  no interesting floor — every method that answers it at all answers it exactly.
  That is itself informative: the north-star metric needs a task where being
  wrong is possible.
