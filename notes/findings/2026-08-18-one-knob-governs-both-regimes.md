---
title: A third task fills the missing cell — and the decision margin turns out to govern both the routing headroom and the recall/precision ordering, on tasks 179× apart in cost
date: 2026-08-18
author: lead
status: provisional
tags: [third-task, generalisation, routing, synthesis]
---

## Why this task exists

The synthesis note left a specific gap: two flood findings had each been bounded
to a regime, but **no task had an expensive kernel *and* a tunable decision
margin at once**, so the two boundaries had never been tested together.

| | expensive kernel | tunable margin |
|---|---|---|
| flood logistics | ASP + SMT, 68% of cost | no |
| solvency | no — 179× cheaper end to end | yes |
| **scheduling** | **ASP, 99.1% of cost** | **yes** |

Machine assignment: six jobs, three machines, capability and capacity
constraints, one feasibility boolean. 3⁶ = 729 assignments, so the oracle is
**exhaustive** rather than heuristic — a heuristic that occasionally missed a
feasible packing would be indistinguishable from a kernel bug. ASP agrees with it
on 60/60.

## Predictions, before the numbers

1. The ASP node dominates the pipeline (>50% of cost).
2. Routing headroom shrinks as slack grows.
3. At large slack, precision errors beat recall — inverting flood's ordering.

**All three held**, and (1) held harder than predicted: 99.1%, not 50%.

## Measured

**Cost.** $4.96 × 10⁻⁹ per episode, of which the solve node is **99.1%**. Between
the other two tasks and firmly in the "has an expensive kernel" regime:

| | flood | **scheduling** | solvency |
|---|---|---|---|
| $/episode | 1.2e-08 | **4.96e-09** | 6.7e-11 |
| kernel share | 68% | **99.1%** | 62% of ~nothing |

**Routing.** The provable gate — total demand above total capacity is infeasible
whatever the assignment — fires on everything below the boundary and nothing
above it, and is **never wrong at any slack**:

| slack | gate fires | feasible | gate errors |
|---|---|---|---|
| −0.30 | 1.000 | 0.000 | 0 |
| −0.05 | 1.000 | 0.000 | 0 |
| 0.00 | 0.250 | 0.000 | 0 |
| +0.15 | 0.000 | 0.355 | 0 |
| +1.00 | 0.000 | 0.890 | 0 |

**Corruption, rate 0.20.** The solvency inversion reproduces, on a pipeline with
a combinatorial search in it:

| slack | drop_job | misread | ratio |
|---|---|---|---|
| 0.15 | 0.253 | 0.107 | **2.38** |
| 0.50 | 0.193 | 0.120 | 1.61 |
| 1.00 | 0.067 | 0.113 | 0.59 |
| 2.00 | 0.013 | 0.100 | **0.13** |

against solvency's **2.28 → 0.11**. Two tasks, different kernels, different
answers, **179× apart in cost**, and the ratios agree to within a few percent at
both ends.

## The result

> **One variable governs both.** The distance from the decision boundary sets
> the routing headroom *and* the recall/precision ordering, because both are
> asking the same question: how large an error does it take to change the answer.

Below the boundary, cheap sufficient conditions fire (routing pays) and small
errors flip decisions (recall dominates, because a missing term is a certain
error). Far above it, no cheap condition can decide (routing is useless) and only
multiplicative errors flip anything (precision dominates).

That was not predicted. The two regime findings were reached separately, on
separate tasks, and this is the first measurement where the same knob moves both
at once — which is the argument for their being one phenomenon rather than two
coincidences.

## What would have refuted it

- **The gate being a heuristic.** It is a theorem — demand above capacity cannot
  be packed — and it is asserted correct at six slack levels across 360
  instances, with zero errors. The converse is deliberately *not* a gate, and a
  test finds instances with ample capacity that are still infeasible because the
  capabilities do not line up.
- **The third task being a flood variant.** It shares no generator, no kernel
  mix and no answer shape with either predecessor; its cost sits between them and
  its kernel share is higher than both.
- **The oracle sharing the kernel's code.** Asserted by source inspection to
  contain no reference to clingo, `get_kernel`, `build_program` or `asp@1`.

## The honest cost of building it

The relational projection **discards every `Quantity`** — that is what makes
datalog and ASP unit-safe, and it is measured working. This task is entirely
about durations and capacities, so those numbers reach the solver through the
**supplied program text** as scaled integers, and are therefore **not
unit-checked by the projection**. A duration in minutes against a capacity in
hours would produce a well-formed answer to the wrong question.

The check is re-imposed by hand in `build_program`, which raises on any unit but
hours, and a test confirms it fires. That is a weaker guarantee than the
projection gives, in exactly one place, stated rather than discovered later.
