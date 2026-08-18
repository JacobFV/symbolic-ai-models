---
title: The Lean kernel refutes 100% of injected role confusions and datalog 0% — but only 11.7% of them changed any answer, and one class changed none
date: 2026-08-18
author: lead
status: provisional
tags: [kernels, lean, verification, refuted-prediction]
---

## What was built

Tier 4 of the kernel stack: `lean@1`, the verifier, and the only kernel whose
manifest declares a **veto**. It is native — on the kernel already vendored in
`symbolic_ai_lean` — because a subprocess elaborator inside a sweep breaks the
cost budget the whole repo argues about.

What it checks is narrower than "Lean proves theorems", and the manifest says
so: it reads the types the world already carries (an entity's `types` tuple,
which the relational projection emits as an inert `type/2` fact and never
consults), turns them into a signature — each type a sort, each entity a
constant of its sort, each predicate a Pi type inferred from its *first* use —
and typechecks every later use against it.

The gap it fills is real. Datalog and ASP are **untyped**: `link(truck_0,
region_1)` is a well-formed fact and a well-formed atom, and both will compute a
closure over it.

## Prediction, before the numbers

Stated in advance: Lean catches 100% of injected role confusions, datalog 0%,
and *the injection changes the flow's answer on a non-trivial share of seeds*.

The first two held. **The third was wrong for the first injection I tried and
only mildly right for the second**, and that is the finding.

## Measured, 120 seeds each

**Injection A — `link(truck_0, demand_site)`**, a vehicle where a region belongs:

| | |
|---|---|
| lean refutes it | **120/120 = 1.000** |
| datalog notices anything | **0/120 = 0.000** |
| the flow's answer changes | **0/120 = 0.000** |

Perfectly detected and completely inert. ASP's own structural constraints
exclude it without ever knowing why: the route program constrains degrees only
over `region(V)`, so `truck_0` is a dead end no simple path can traverse.

**Injection B — a crossing linked to a region id instead of a bridge id**, which
is what a reader confusing two identifier namespaces would produce. The bridge's
posted limit then silently has no crossing to attach to and vanishes:

| | |
|---|---|
| lean refutes it | **120/120 = 1.000** |
| the flow's answer changes | **14/120 = 0.117** |
| caught *and* consequential | 14/14 |
| consequential and missed | **0** |

## What this actually says

> **The verifier has perfect recall on its own class of error, and whether that
> is worth anything depends entirely on how often that class is consequential in
> the pipeline downstream.**

Here it ranged from 0% to 11.7% across two injections that are equally
ill-typed. A cost table that priced this kernel by "errors caught" would have
scored injection A as a full success; it caught 120 errors that changed nothing.
The number that matters is *caught and consequential*, and it is 14, not 240.

The complement is the honest limit, and it is not small: **a type error is not
the same as a false fact.** Injecting `link(region_0, region_4)` where no such
road exists is perfectly well typed, changes routes, and this kernel cannot see
it at all. Everything above is measured on the class it *can* see.

## What would have refuted it

- **Datalog quietly rejecting the ill-typed fact**, which would leave this
  kernel with no job. It does not: the derived closure contains `near(v0, r1)`,
  asserted by test.
- **The sort assignment inventing constraints.** An entirely untyped world must
  produce zero refutations, or the projection is manufacturing type errors out
  of absent information. Asserted, and `vacuous: true` is reported in the
  diagnostics whenever any entity is untyped.
- **The refutations being unreadable.** They name both sides —
  `argument truck_0 : vehicle does not fit region` — rather than reporting a
  count.

## What is deliberately not claimed

Real Lean 4 is not in this path and this is not theorem proving. The projection
is monomorphic, so an entity with two types loses all but the first — recorded
as a discard whose text says what the consequence will look like, because a
predicate expecting the dropped sort will read as a type error that is really a
projection error. `san_francisco` being a place *and* a jurisdiction is the
normal case, not an edge one, and a polymorphic signature is the next thing this
kernel needs.
