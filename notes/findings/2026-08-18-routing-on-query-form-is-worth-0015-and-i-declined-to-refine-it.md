---
title: Routing on a query's static form beats the better single world by +0.015 and leaves 0.026 to an oracle — and the obvious refinement is contradicted by the third case I checked it against
date: 2026-08-18
author: lead
status: provisional
tags: [routing, monotonicity, extraction, negative-result, slices, flow]
---

## Why

Monotonicity is now measured on the same axis **four** times — twice before this
session (`inspectability-is-asymmetric`: a witness verifies **247x** cheaper than
solving, an optimality certificate **2.0x dearer** than re-solving; plus its
datalog companion) and twice inside it (the **93x** maintenance split, and
monotone queries repairing a noisy world where the antitone one cannot).

All four end in the same stated design consequence, and none of them built it:

> world construction and answer construction want **opposite defaults**, and
> nothing in the architecture says so.

This builds it. Two worlds already exist — `precise` (abstains) and `complete`
(emits every candidate) — and the claim is that a query's **form** decides which
one should answer it. This is also the first **routing decision** this repo has
ever measured, which is the mandate's stated long-term object.

**The honest constraint:** routing on *measured* per-class performance is
tautological. So the router is handed the query's declared set expression and
**nothing else** — no result, no score — and scored against each single world and
against an oracle that picks the winner per class *after* seeing both.

## Result

| query class | form | monotone | precise | complete | **routed** | oracle |
|---|---|---|---:|---:|---:|---:|
| `institutions_of(work)` | `A` | yes | **0.576** | 0.454 | 0.454 ✗ | 0.576 |
| `collaborators(institution)` | `⋃ Aᵢ` | yes | 0.338 | **0.417** | 0.417 | 0.417 |
| `works_at(institution)` | `⋃ Aᵢ` | yes | 0.601 | **0.671** | 0.671 | 0.671 |
| `works_at_both(A,B)` | `A ∩ B` | yes | 0.282 | **0.465** | 0.465 | 0.465 |
| `institutions_unique_to(w1,w2)` | `A − B` | **no** | **0.599** | 0.473 | 0.599 | 0.599 |
| `is_single_institution(work)` | `\|A\| == 1` | **no** | 0.715 | **0.750** | 0.715 ✗ | 0.750 |
| **mean, mixed workload** | | | 0.518 | 0.539 | **0.553** | 0.580 |

**+0.015 over the better single world. −0.026 against the oracle.** I predicted
+0.03 to +0.08 and within 0.01 of the oracle; both were optimistic.

So **form is a real signal and a partial one**. It gets four of six classes
right, including both that decide the axis, and it beats either world alone on a
mixed workload — which is the thing that had never been shown.

## The refinement I declined, and why that is the point

The two failures suggest a fix immediately. `institutions_of(work)` is monotone,
but its expression is a bare `A`: there is nothing to filter against, so it
inherits the fact-level trade-off where precision wins. That gives a tidy rule —
**monotone *and* combining ≥ 2 sets → complete** — and it explains the failure.

I checked it against a case it did not come from:

| | form | arity | monotone | winner | rule says | |
|---|---|---:|---|---|---|---|
| `institutions_of(work)` | `A` | 1 | yes | precise | precise | ✓ |
| **`works_at(institution)`** | `inv[A]` | **1** | **yes** | **complete** | precise | **✗** |
| `collaborators(institution)` | `⋃ Aᵢ` | n | yes | complete | complete | ✓ |
| `works_at_both(A,B)` | `A ∩ B` | 2 | yes | complete | complete | ✓ |

**Two arity-1 monotone queries, opposite winners.** The refinement explains one
failure and is contradicted by the third case, so it is not adopted and the
residual stays unexplained.

This morning I published
`notes/lessons/2026-08-18-i-designed-an-experiment-from-five-printed-examples.md`
after building an entire arm out of five sampled failures. Here the same
temptation arrived with **two** data points and a mechanism that sounded right,
and the guard fired before the code did. **The declining is the result** — the
number is small, and not fitting it is the part worth keeping.

## What is left open

**What separates the two arity-1 monotone queries is not known.** One returns the
extraction output directly, so its precision *is* the extraction's precision. The
other asks which works *contain* an institution, and over-generation concentrated
on siblings apparently costs it less. That is a hypothesis and it has one
supporting case, which is exactly the position the paragraph above declines to
build on.

## What would refute this

- **Six classes, one corpus, one pair of worlds.** The +0.015 is a mean over a
  workload I chose; a workload weighted differently moves it, and a workload of
  only projections would make routing *worse* than the complete world alone.
- **Two operating points.** `precise` and `complete` bracket a range whose
  interior was never searched, so "which world" is a binary the real design
  probably is not.
- **The oracle is per-class, not per-query.** A per-query oracle would be higher
  still, and the gap to it is unmeasured.
- **`is_single_institution` was already inconclusive** against its 65.8%
  majority floor in the finding it comes from, so one of the two failures may not
  be a failure.

## Reproduce

```bash
SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \
  uv run python -u scripts/route_by_monotonicity.py
```

`runs/route_by_monotonicity.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `route-by-monotonicity`.
