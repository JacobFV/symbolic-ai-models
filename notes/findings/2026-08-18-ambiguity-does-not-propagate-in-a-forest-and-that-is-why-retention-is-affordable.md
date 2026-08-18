---
title: Ambiguity does not propagate in a wide shallow forest — 251 conflicts touch 253 entities, amplification 1.0x, against 44x on the route network
date: 2026-08-18
status: provisional
tags: [fusion, ambiguity, topology, real-data, gleif, negative-result]
---

## The gap this closes

`fuse` retains a disagreement it cannot settle, and since the last fix the
mixture survives serialisation. **Nothing read one.** A retained alternative no
consumer can act on is a data structure rather than a capability, and the
pressure to collapse it returns the moment a caller needs an answer.

## Prediction, and how wrong it was

The 251 unresolved conflicts in GLEIF's filings are not isolated in principle:
any entity whose ownership chain passes *through* a conflicted one inherits the
ambiguity.

**Prediction: 400–800 contaminated entities, a multiplier of 1.6–3.2x.**

| | |
|---|---|
| conflicted entities | 251 |
| others whose chain passes through one | 45, of which **2** are not themselves conflicted |
| total entities whose answer depends on an unresolved conflict | **253** (0.22% of the world) |
| **amplification** | **1.0x** |

Badly wrong, and the mechanism is clean: **92.2% of the 117,129 entities are
leaves**, and a conflicted entity has a **median of zero descendants** (mean
0.21, max 17). The ownership graph is a wide, shallow forest. A conflict has
nothing beneath it to contaminate.

## Set against the route network, this is the sharper result

The sensitivity work measured the opposite case on the same substrate: a 0.05%
input error became 0.43% of answers, an amplification of **8.3x at one range
limit and 44x at another**, because the route graph is dense and nearly
connected so every edge lies on many shortest paths.

| graph | shape | amplification |
|---|---|---|
| openflights routes | dense, near-connected | **1.6x – 44x** |
| GLEIF ownership | wide, shallow forest, 92.2% leaves | **1.0x** |

Same substrate, same kind of question — how far does a local disagreement
travel — and the answer is a property of the **topology**, not of the kernels,
the data volume or the conflict rate. That is now measured at both extremes
rather than argued.

## Why that makes retention affordable, and why the bound still matters

The practical consequence is the interesting half. Enumerating every world
consistent with 251 independent conflicts is **2^251**, which
`possible_answers` refuses outright. It is tractable here only because the
conflicts do not interact: each query touches exactly one, so each returns two
answers rather than exponentially many.

**Retention is cheap in this graph precisely because ambiguity does not
propagate in it.** On the route network it would not be, and the bound is the
difference between the two topologies rather than paranoia about a case that
never happens.

## Built

`symbolic_ai_core/runtime/ambiguity.py` — `Alternatives`, `possible_answers`,
`alternatives_from`. Give it the retained choices and a computation and it
returns **every answer the evidence permits**, grouped, with the assignments
that produce each. A caller getting one answer back learns the ambiguity did
not matter; a caller getting two learns which unresolved conflict it is standing
on.

Three decisions worth naming:

- **Answers are grouped, worlds are counted separately.** 1,024 worlds that all
  give the same number is not an ambiguous result, it is an irrelevant conflict,
  and collapsing that distinction would waste the entire exercise.
- **The explosion is refused, never truncated.** A truncated answer set looks
  complete and is not.
- **`alternatives_from` takes the value extractor from the caller**, because
  what counts as *the* value is predicate-specific and guessing it is how a
  fusion layer starts deciding semantics it has no business deciding.

The full arc now runs on real bytes: 251 conflicts → retained by `fuse` →
through a JSON round trip → read back as choices → 251 queries each returning
two possible answers.

## Correction, one day later: that was a median reported as a property

The headline above is wrong in a specific and instructive way. **1.0x describes
where those 251 conflicts happened to sit, not the graph.**

Measuring `exposure` — how many answers change if a conflict lands on a given
node — across every GLEIF relation:

| relation | mean | p50 | p90 | p99 | **max** |
|---|---|---|---|---|---|
| `IS_DIRECTLY_CONSOLIDATED_BY` | 1.98 | 1 | 3 | 14 | **769** |
| `IS_FUND-MANAGED_BY` | 1.94 | 1 | 1 | 15 | **1,259** |
| `IS_SUBFUND_OF` | 1.89 | 1 | 2 | 17 | **3,848** |

Four orders of magnitude **inside a single relation**. The graph has hubs — a
manager with 1,258 funds, a fund family with 3,847 subfunds — and those are
precisely the entities whose ownership is most worth arguing about.

The 251 real conflicts sat at ordinary positions: median exposure 1, mean 1.21,
max 18, against a random entity's median 1, mean 1.28, max 175. Total exposure
**304 answers**.

> **The same 251 conflicts, placed on the 251 highest-exposure nodes, would
> contaminate 31,111 answers — 102x worse from an identical conflict count.**

So "retention is cheap in this graph" is true of the conflicts that occurred and
false as a statement about the graph. The correct rule is that **the cost of
retaining a conflict is a property of the node it sits on**, spanning three
orders of magnitude, and a flat `max_worlds` bound cannot express that.

`exposure` and `rank_by_exposure` now make it visible *before* enumeration —
`possible_answers` refusing an explosion is the right failure and a late one.

A cycle bug surfaced while testing this: the walk counted the start node once in
a `1 +` and again in the visited set, so a two-entity ownership loop reported an
exposure of 3. Six such loops are real in this data. Seeding the visited set
with the node fixes it, and the test that caught it was written before the code.

## What would refute it

- One graph shape per measurement. Two points is a contrast, not a curve, and
  nothing here predicts where a given graph falls between them — the
  sensitivity work already showed that no cheap statistic I tried predicts the
  amplification.
- The 253 counts entities whose chain *passes through* a conflict. An entity
  whose answer depends on a conflict some other way — a fund whose manager is
  conflicted, say — is not counted, and `IS_FUND-MANAGED_BY` has 123,825 edges
  that this measurement ignores entirely.
- `possible_answers` enumerates. A query touching 30 interacting conflicts is
  refused rather than answered, and the useful thing there would be to reason
  about the answer set symbolically instead — which is a solver's job and not
  this module's.
