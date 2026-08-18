---
title: Inspectability is asymmetric — a witness verifies 247x cheaper than solving, and certifying optimality costs twice as much as re-solving
date: 2026-08-18
status: provisional
tags: [proof-trace, inspectability, cost, real-data, negative-result]
---

## Why this, now

`APPROACH.md` makes two claims for this substrate: a different order of
magnitude in cost, and **reasoning that is inspectable rather than inferred**.
Six wake-ups went into the first — four real-data tasks, an advantage curve
across seven orders of magnitude, a composition study, a sensitivity profiler.
The second had nothing. The naming law reserves `proof_trace` and
`lineage_trace`; `lineage_trace` existed as the flow layer's `Trace`, and
**`proof_trace` existed nowhere.** No kernel and no task justified its answer.

That is the half a language model cannot match at any price, so leaving it
unmeasured while quoting cost ratios was measuring the easy side.

## The distinction that turned up immediately

A symbolic answer to "how few legs from A to B, none over 2,000 km" has two
halves, and they are not equally justifiable:

- **existential** — *there is a route of five legs, each within range*. The
  route is its own witness. Checking it is five distance comparisons and touches
  nothing else in the graph.
- **universal** — *and there is no shorter route*. No witness exists. The
  standard certificate is a **distance labelling**: level every node, then check
  that no admissible edge skips a level. Real verification — no search, no
  queue, no trust in the solver — but it quantifies over every edge.

## Predictions

1. Witness verification **more than 500x cheaper** than solving.
2. Optimality-certificate verification **within 3x of solving** — the universal
   half is not cheap.

## Measured, 400 solvable pairs on the real network, mean 5.19 hops

| | per query | vs solving |
|---|---|---|
| solve (BFS with parents) | **274.8 µs** | — |
| verify witness | **1.1 µs** | **247x cheaper** |
| verify optimality certificate | **542.4 µs** | **2.0x more expensive** |

**Prediction 1 was wrong** — 247x, not >500x. **Prediction 2 held in magnitude
and the sign is the finding**: certifying optimality does not merely fail to be
cheap, it costs *twice what recomputing the answer costs*.

The reason is structural. BFS stops the moment it reaches the target — a mean of
5.19 hops, levelling 778 of 3,241 nodes. The certificate cannot stop early: it
must scan the out-edges of every levelled node to prove that nothing skips a
level. Early exit is available to the solver and forbidden to the verifier.

### I tried to fix it and made it worse

Restricting the scan to the nodes the certificate actually levels — 778 instead
of 3,241 — should have cut it. Measured: **746.1 µs, worse than the 542.4 µs
full scan.** The inner edge loop is identical either way, because only levelled
nodes have their edges checked in both versions; the restriction only adds
lookups. So the asymmetry is a property of the problem and not of my first
implementation, which is the thing I checked because the last two findings both
turned on my own method being weak.

## What this means for the programme

**"Inspectable" is true and it is not uniform, and the substrate should say
which half it is claiming.** A system that returns a route and calls it the
shortest has cheaply justified the part that says what *is*, and asserted the
part that says what *is not*.

The 247x is genuinely valuable and is the case worth designing around: an
answer plus its witness can be cached, shipped, and re-checked by a party that
trusts nothing, for a fraction of a percent of the cost of producing it. Against
the LLM comparison this is the sharper contrast than cost — a model can be given
a graph and produce a route, and it cannot produce a certificate that anyone can
check without redoing the work.

For the universal half, the certificate buys **trust-independence, not speed**.
If you trust the solver, re-running is half the price. That is a real and
narrow value: it is what a third-party auditor needs, and it is not what a
caching layer needs. Conflating them would have made optimality certification
look like an optimisation, and it is the opposite.

The trace also carries `sources`, which is nearly free and is the other half of
inspectability: a route certified from bytes under an unresolved licence is a
route that may not be publishable, and the trace is where that travels **with**
the answer rather than beside it.

## What would refute it

- One problem shape. Shortest-path has an unusually cheap witness and an
  unusually expensive universal certificate. A datalog derivation has a
  proof tree whose verification is closer to linear in the derivation, not the
  database, and I would expect a much better ratio there. Untested.
- The 247x is against *my* BFS. A faster solver narrows it; the witness check
  is already near the floor of what Python can do, at 1.1 µs.
- Optimality certification against a solver that itself scanned everything
  (no early exit) would show a ratio near 1.0, not 0.5. The 2.0x is partly a
  statement about how good early termination is.
