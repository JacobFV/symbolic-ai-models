---
title: Size orders datalog cost perfectly and SMT cost two thirds of the time — a 1,491-clause instance beat a 2,250-clause one by 7,892x the wrong way
date: 2026-08-18
status: provisional
tags: [kernel-abi, cost, routing, smt, calibration, negative-result]
---

## The experiment that could embarrass yesterday's finding

Yesterday's cost estimator scored **ordering 1.000** on datalog even while
under-predicting the full corpus by 7x, and I published the conclusion that an
estimate can be useless for budgeting and perfect for routing. I named the case
that would break it: **SMT, where a slightly larger problem can be dramatically
easier.**

**Prediction: ordering falls to 0.55–0.70 — barely above chance.**

## The first run said 0.924, and it was wrong

Random 3-SAT with z3 at 30–120 variables across ratios 2.0 to 10.0:
**ordering 0.924**. The mechanism was visible — at 120 variables, ratio 4.26
took 5.21 ms on 511 clauses while ratio 10.0 took 1.04 ms on 1,200 — but
everything finished under 6 ms, so the effect was a rounding error.

**That is yesterday's own lesson firing on today's experiment, within a day:** a
measurement taken in the cheap regime describes the cheap regime. I had written
that sentence about cost fits and immediately made the same mistake about
ordering.

## Scaled into the region where the transition bites

Five instances per cell, z3, 15-second cap:

| vars | ratio | clauses | median | censored |
|---|---|---|---|---|
| 150 | 2.50 | 375 | 0.6 ms | 0 |
| 150 | **4.26** | 639 | **9.0 ms** | 0 |
| 150 | 15.0 | 2,250 | 1.9 ms | 0 |
| 250 | 2.50 | 625 | 0.9 ms | 0 |
| 250 | **4.26** | 1,065 | **3,051.9 ms** | 0 |
| 250 | 15.0 | 3,750 | 3.5 ms | 0 |
| 350 | **4.26** | 1,491 | **>15,000 ms** | **5 of 5** |
| 350 | 8.00 | 2,800 | 43.2 ms | 0 |
| 350 | 15.0 | 5,250 | 6.0 ms | 0 |

**Ordering: 0.667.** Prediction held.

| the larger problem | the smaller one | |
|---|---|---|
| 2,250 clauses, 1.9 ms | 1,491 clauses, >15,000 ms | **≥7,892x cheaper, 1.5x larger** |
| 5,250 clauses, 6.0 ms | 1,491 clauses, >15,000 ms | ≥2,502x cheaper, 3.5x larger |
| 1,200 clauses, 1.7 ms | 1,065 clauses, 3,051.9 ms | 1,749x cheaper, 1.1x larger |

All five instances at 350/4.26 hit the cap, so those ratios are **lower
bounds** — the true cost is unbounded, and an uncapped earlier run left one
instance grinding for over ten minutes.

## What this does to yesterday's conclusion

It survives, narrowed, and the narrowing is the finding: **size-based cost
estimation is regime-dependent, not general.**

- Where cost is **monotone in the input** — a datalog closure — an estimate can
  be 7x low and still order every pair correctly, and a router can use it.
- Where difficulty is a property of **structure rather than size** — distance
  from a satisfiability phase transition — size orders cost barely better than
  chance, and an estimator is not merely inaccurate but *misleading*: it will
  confidently send the planner down the branch that never returns.

So the manifest now has to carry more than an estimator. `Calibration.orderable`
makes the distinction a property a router can read, and **`smt@1` declares
`COST_IS_SIZE_ORDERABLE = False` and offers no estimator at all**, because
offering one would be worse than offering none.

The honest interface for a non-orderable kernel is a **budget**: give it a
timeout, treat exhaustion as an outcome rather than an error, and never let a
planner conclude from a small instance that a larger one costs more.

## What would refute it

- The threshold `ORDERABLE = 0.90` is a judgement, not a measurement. Nothing
  measured lands between 0.70 and 1.00, so it is not yet load-bearing — and
  when something does land there, the number will need an argument it does not
  currently have.
- Random 3-SAT is the textbook hard family. A *practical* SMT workload — unit
  checks over quantities, which is what `smt@1` actually projects — may be far
  better behaved, and I have not measured that. The claim is about the kernel's
  worst case, which is the case a planner must survive.
- Cost was measured as wall clock on one machine with one z3 seed. Phase
  transition instances are famously seed-sensitive; the medians of five hide a
  spread that the max column showed running to 25x the median at 150 variables.
