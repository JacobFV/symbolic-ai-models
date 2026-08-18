---
title: Two checks that looked present and were not — a guard placed after the filter that removes its trigger, and a predicate generic enough to fuse two different properties
date: 2026-08-18
tags: [mechanism, kernels, fusion, guards]
---

Both found by tests on the geo kernel within an hour of writing it, both invisible
to inspection, and both general enough to recur anywhere in this substrate.

## 1. A guard placed after the filter that removes its own trigger

`P_geo` refused a world containing two coordinate reference systems — mixing
datums silently is exactly the failure the projection exists to prevent. The code
read:

```python
for eid, e in entities:
    if crs not in SUPPORTED_CRS:
        discard(...); continue        # <- removes every non-4326 place
    crss.add(crs)
if len(crss) > 1:                     # <- can now only ever see {"EPSG:4326"}
    raise ValueError("no reprojection here on purpose")
```

`SUPPORTED_CRS` has one member, so the filter removed every place that could have
made the set bigger than one. **The guard was unreachable.** It read as a
protection, tested as absent, and would have stayed that way indefinitely because
nothing in the happy path ever touches it.

The mechanism: **a check downstream of a filter that removes the very cases it
checks for.** It generalises past CRSs — the same shape would hide a unit guard
placed after unit-unsupported values are dropped, or an authority check placed
after unauthorised producers are already excluded.

The guard: **write the test that expects the guard to fire, not the test that
expects the happy path to pass.** The fix here was to collect the declared CRSs
*before* any filtering, so the refusal sees what the world actually contains.

## 2. A predicate generic enough to fuse two different properties

The geo kernel first emitted `distance`. A road survey also emits `distance`.
London to Paris is **344 km** across the ellipsoid and **459 km** by road, and
the fusion registry groups by `(predicate, subject)` — so inverse-variance
weighting averaged them into **381 km**, which is neither, and did it without a
warning because from fusion's point of view that is exactly its job.

They are not two measurements of one property. They are two properties.

> **In this substrate the predicate *is* the type.** Fusion, entitlement and
> authority all key on it, so a name loose enough to cover two quantities makes a
> category error representable — and representable errors get made.

Renaming the claim to `geodesic_distance` makes the merge impossible rather than
merely discouraged, and costs nothing. The general rule for a kernel author:
**name the claim after what the kernel computed, not after what it is about.**
`geodesic_distance`, not `distance`; `predicted_pose`, not `pose`, if a sensor
might also speak; `derived_fact`, not `fact`.

The cheap check: for every predicate a kernel emits, ask what *else* in the
system could plausibly emit that name, and whether averaging the two would mean
anything. If it would not, the name is too generic.

## Why these are one note

Both are checks that pass inspection. A reviewer reading the CRS guard sees a
guard; a reviewer reading `Claim("distance", ...)` sees a claim. Neither
misbehaves until something exercises the exact case, and in both instances the
thing that exercised it was a test written to assert the *refusal* rather than
the result.
