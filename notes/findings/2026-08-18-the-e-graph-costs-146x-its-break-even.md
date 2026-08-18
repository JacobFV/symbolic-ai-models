---
title: Equality saturation simplifies the constraints by 18.7% and saves 23% of solve time, at 33.7× the cost of the entire solve — break-even needs 146 reuses and the workload has 1.26
date: 2026-08-18
author: lead
status: provisional
tags: [egraph, kernels, cost, negative-result]
---

## What was built

Tier 5: a native e-graph — union-find over e-classes, hashcons, congruence
closure with parent pointers, pattern matching that binds *classes* rather than
terms, static and dynamic rewrites, saturation with reported limits, and
cost-model extraction. Plus `egraph@1` behind the kernel ABI, and a rule set over
the SMT constraint language whose interesting member is

    a <= L1  AND  a <= L2   ==   a <= min(L1, L2)

so a route crossing *k* bridges collapses to a single bound. It has to be a
**dynamic** rewrite: it fires only when both bounds are literals, and a static
pattern cannot say "compute their minimum".

It works. On the flood task's SMT calls it folds three bridge bounds
(4500, 3000, 6000) into one (3000), and satisfiability is preserved on 150/150
calls.

## Prediction, before the numbers

Stated in advance: *the e-graph will cost more than it saves, because z3 solves
these in microseconds and saturation is pure Python.* Correct — and the size of
the gap was not something I would have guessed.

## Measured, 150 SMT calls over 30 seeds

| | |
|---|---|
| constraints | 546 → 444 (**18.7% fewer**) |
| satisfiability preserved | 150/150 |
| solve time saved | **23.1%** (0.401 → 0.308 ms, 3.0 SE, 40×20 controlled reps) |
| e-graph time | **33.7× the entire solve time** |
| **reuses needed to break even** | **146** |
| reuses available | **1.26** |

The break-even is arithmetic: saturation costs ~29.2 ms per constraint set and
saves ~0.20 ms per solve, so the simplified form must be solved **146 times**
before the optimiser has paid for itself. The workload reuses each distinct
constraint shape 1.26 times. It is **116× short**, not marginally short.

A note on how the solve-time number was obtained, because the first attempt got
it backwards: a single interleaved pass reported the simplified form as *15.5%
slower*, which was machine contention. Repeated controlled measurement (40
batches of 20 solves each) gives +23.1% at 3.0 SE. The headline does not depend
on the sign — a 100% solve saving would still be a 33× net loss — but the finding
would have been wrong in its detail, and this repo has a standing lesson about
exactly that.

## The sub-result: completeness *is* the cost

Dropping the two rules that make the fold reachable:

| rule set | time | node reduction |
|---|---|---|
| full (fold + idempotence + commutativity + associativity) | 9,775 ms | 23.7% |
| lean (fold + idempotence only) | **92.8 ms** | **0.0%** |

**105× cheaper and it finds nothing.** The fold only fires when commutativity and
associativity have brought the two `<=` terms adjacent, so the rules that make
the optimisation *reachable* are the same ones that make saturation expensive.
That is not a tuning problem — it is the shape of equality saturation. You cannot
buy the fold cheaply, because finding it *is* exploring the equivalence class.

## Where an e-graph would pay, stated so this is not read as "e-graphs are bad"

The technique is correct here and the arithmetic is against it for three specific
reasons, each of which names a workload where it would not be:

1. **The artifact is used once.** Reuse of 1.26 kills any amortisation. An
   e-graph over something compiled once and run a million times — a query plan, a
   kernel, a routing policy — reverses this entirely.
2. **The thing optimised was not the binding cost.** z3 spends most of ~0.9 ms
   per call on solver construction and variable declaration; assertion count is
   a minority term. Optimising a minority term caps the win before you start.
3. **Pure Python.** `egg` is Rust and is orders faster; the 33.7× is partly an
   implementation constant, not only a structural one.

This is the same lesson as the routing finding one layer up — *routing pays in
proportion to what is downstream of the gate* — and as the perverse-regime
finding one layer above that. Three results, one shape: **an optimiser is only
worth its own cost when what it optimises is the binding term.**

## What would have refuted it

- **The simplification being wrong.** Satisfiability preserved on 150/150, and a
  test asserts it on both a sat and an unsat case.
- **The congruence closure being broken**, which would make the e-graph represent
  fewer equalities than it claims and understate what saturation could find. It
  *was* broken — the first implementation had no parent pointers, so merging `x`
  with `y` left `f(x)` and `f(y)` apart. A test caught it, and every number here
  is from the fixed engine.
- **The cost being an artefact of one constraint shape.** It is measured across
  150 real constraint sets from 30 generated worlds, not on a synthetic case.
