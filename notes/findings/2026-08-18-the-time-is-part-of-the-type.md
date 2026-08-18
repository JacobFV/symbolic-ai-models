---
title: Two poses for different moments fused into a position at no time at all — the predicate is the type, and the time is part of it
date: 2026-08-18
author: lead
status: provisional
tags: [fusion, kernels, world-ir, mechanism]
---

## How it was found

Writing the geo kernel produced a lesson — a generic predicate name lets fusion
average two different properties, because the registry groups by
`(predicate, subject)`. `distance` covered both a 344 km geodesic and a 459 km
road length and averaged them into 381 km.

The obvious next question was whether any other kernel emits a name loose enough
to do that. `rigid@1` emits `pose`, and a sensor would emit `pose` too — but that
is the case fusion is *for*: a predicted pose and an observed pose really are two
readings of one property.

Then: two readings of one property **at what time?**

## Measured, before the fix

```
dt = 0.1s  ->  pose 0.100 m   valid_time (None, None)
dt = 0.9s  ->  pose 0.900 m   valid_time (None, None)
fuse(...)  ->  0.387 m,  resolved 1,  unresolved 0
```

Two predictions for different horizons combined by inverse variance into a
position the body occupies at no moment, silently, with no unresolved group and
nothing in the trace. From the fusion layer's point of view it did exactly its
job.

## The fix, in two halves

**`Interval.overlaps`, and grouping on it.** `group_claims` now partitions each
`(predicate, subject)` bucket into runs whose validity can refer to the same
moment. A claim joins a run only when it overlaps *every* member, so a chain of
pairwise-overlapping-but-collectively-inconsistent intervals is not merged into
one.

Two properties of that rule are deliberate:

- an **unbounded** interval overlaps everything, which is the correct reading of
  "this claim does not say when" — it cannot be shown to be about a different
  time, so it stays combinable, and every existing untimed claim behaves as
  before;
- bounds that are not ISO-parseable are treated as **disjoint unless equal**,
  which is the conservative direction: it produces an unresolved mixture rather
  than a silent merge, and an unresolved mixture is a thing a reader notices.

**`rigid@1` stamps the moment its prediction is for**, given a `t0`. Without one
it stamps nothing — it steps a relative `dt` and has no clock of its own, and
inventing an epoch would be worse — and reports `timed: false` with a warning in
its diagnostics saying exactly what will happen if two horizons meet.

After: the two horizons stay apart, and two estimates of the *same* moment still
fuse. Both asserted, the second because a fix that separated everything would
also have "worked".

## The general rule this makes explicit

> **In this substrate the predicate is the type, and the type includes the
> subject and the time.** Fusion, entitlement and authority all key on it.

Three category errors of the same shape have now appeared within a day, each
caught by a test written to assert a refusal:

| what was merged | should have been |
|---|---|
| geodesic 344 km with road 459 km | two **properties** |
| pose at t+0.1s with pose at t+0.9s | two **moments** |
| (guarded from the start) claims about different entities | two **subjects** |

The third was right by construction from the beginning; the first two were not,
and neither announced itself. The cheap check for a kernel author is now three
questions rather than one: for every predicate you emit, what else could emit
that name, of what else could it be true, and **when** is it true.

## What would have refuted it

- **The fix separating claims that should combine.** Two estimates of the same
  moment still fuse to one, asserted, and the test also constructs the merged
  case explicitly to show the split is what separated the horizons rather than
  something else.
- **Breaking untimed claims.** Every pre-existing fusion test uses unbounded
  intervals and passes unchanged, which is the intended semantics rather than a
  coincidence.
- **The warning being unreachable.** `timed: false` and its message are asserted
  on an untimed run and asserted empty on a timed one. An earlier draft put that
  signal on a `Discard` added to the projection *inside* `run` — which the
  caller never sees, the same dead-guard shape as the geo CRS check, an hour
  after writing the lesson about it. It is a returned diagnostic instead.
