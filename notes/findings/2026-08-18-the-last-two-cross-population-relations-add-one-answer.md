---
title: The two relations the fund-exposure finding admitted it had not checked add exactly one exposed answer between them
date: 2026-08-18
status: provisional
tags: [fusion, ambiguity, topology, real-data, gleif, negative-result, refuter]
---

## The refuter this closes

`notes/findings/2026-08-18-the-fund-graph-was-named-as-ignored-and-it-is-genuinely-irrelevant.md`
found zero overlap between the 251 real ownership conflicts and GLEIF's two
large fund relations, and named its own hole:

> Restricting to `IS_FUND-MANAGED_BY`/`IS_SUBFUND_OF` misses a third
> cross-population relation this script did not check —
> `IS_INTERNATIONAL_BRANCH_OF` (1,920 edges) and `IS_FEEDER_TO` (1,359 edges)
> are smaller and unexamined here.

Checked, with the same 251, the same `exposure` walk and the same script.

| relation | nodes | hubs | of the 251: hubs | of the 251: appear at all | summed exposure |
|---|---:|---:|---:|---:|---:|
| `IS_INTERNATIONAL_BRANCH_OF` | 3,334 | 1,420 | **1** | 4 | **252** (251 + 1) |
| `IS_FEEDER_TO` | 2,318 | 968 | **0** | 0 | **251** (every node exposure 1) |

One of the 251 conflicted entities is an international-branch hub, with a single
branch beneath it. That is the entire additional exposure the two unexamined
relations contribute: **one answer**.

## What it means, and what it does not

The prior null holds and is now checked against every cross-population relation
GLEIF files, not two of them. The reason remains structural rather than lucky:
consolidation ownership, fund administration, branch registration and feeder
structures relate different kinds of entity, and an entity conflicted about its
corporate parent is usually not also a fund manager, a branch hub or a feeder.

It does **not** say a conflict on those relations would be cheap. A branch hub
in general has branches beneath it; these particular conflicts sit on one that
has exactly one.

## What would refute it

The same thing that would refute the finding it extends: a different
conflict-defining rule, or a later GLEIF snapshot. This is a measurement of
where 251 particular disagreements happen to sit, and that has already been the
mistake once — a median reported as a property of the graph.
