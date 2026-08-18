---
title: $ per solved episode above floor has a perverse regime — far above the floor it pays to give up accuracy, and here 11 points buys 2.8%
date: 2026-08-18
author: lead
status: provisional
tags: [cost, metric, routing, refuted-prediction]
---

## The question

The routing finding ended by saying the next arm is *a gate that is allowed to be
wrong, scored on the ranking*, and predicted the lossless gate would already be
on the Pareto frontier. **It is not.** Chasing that turned into a result about
the metric rather than about the router.

The escalation gate's second condition — every qualifying vehicle's laden mass
clears the lightest posted limit — is provable at slack 1.0. Relaxing it to
*within a factor s of* the lightest limit gives a family of gates from lossless
(s = 1) to always-cheap (s → ∞).

## Measured, 800 seeds, floor 0.440

| slack | acc | lift | $/episode | **$/solved above floor** | vs lossless |
|---|---|---|---|---|---|
| 1.00 | 1.000 | 0.560 | 1.152e-08 | 2.058e-08 | — |
| 1.20 | 0.970 | 0.530 | 1.076e-08 | 2.030e-08 | **+1.4%** |
| 1.40 | 0.887 | 0.447 | 8.954e-09 | **2.001e-08** | **+2.8%** |
| 1.50 | 0.887 | 0.447 | 8.954e-09 | **2.001e-08** | **+2.8%** |
| 1.60 | 0.786 | 0.346 | 7.200e-09 | 2.079e-08 | −1.0% |
| 1.70 | 0.706 | 0.266 | 5.950e-09 | 2.235e-08 | −8.6% |
| 2.00 | 0.588 | 0.148 | 4.339e-09 | 2.942e-08 | −43.0% |
| 2.50 | 0.534 | 0.094 | 3.601e-09 | 3.841e-08 | −86.7% |

Accuracy SE at N = 800 is 0.018, so the 0.113 accuracy drop at the optimum is
**6.3 SE** — not noise. The 2.8% improvement in the ratio is small but the
accuracy it was bought with is not.

## What it says about the metric

> **`$ / solved above floor` rewards giving up accuracy whenever accuracy is far
> above the floor.**

The condition is one line. A lossy arm wins iff

    relative cost saving  >  relative lift loss
    Δcost / cost          >  Δacc / (acc − floor)

and when `acc ≫ floor` the denominator on the right is large, so accuracy is
*cheap in lift terms*. Going 1.000 → 0.887 costs 20% of the lift and saves 22%
of the cost, and the ratio improves.

Near the floor the same algebra bites the other way — the denominator collapses
and any accuracy loss is catastrophic, which is exactly what the slack ≥ 2.0 rows
show. So the metric is well-behaved where the system is weak and perverse where
it is strong, which is the opposite of the regime a maturing system spends its
time in.

This is not an argument for abandoning it. `usd_per_solved_episode_above_floor`
was written to stop a *throughput* number standing in for a capability price, and
it does that. But it is a **ratio**, and a ratio maximised without a constraint
will find the numerator's cheapest point.

## The fix, stated so it is not rediscovered

Quote the ratio **with an accuracy constraint**, not alone:

> the cheapest arm achieving accuracy ≥ *a*

which turns "minimise $/solved" into "minimise $ subject to capability", and is
what anyone deploying this would actually want. On the table above, at a ≥ 0.95
the answer is slack 1.20; at a ≥ 0.99 it is lossless; and the unconstrained
answer is slack 1.40, which nobody would ship.

The corollary for `symbolic_ai_core/cost.py`: `Ledger` should carry the accuracy
its ratio was computed at — it does — **and no table should sort on the ratio
without showing that column**. Sorting on it alone would have ranked a 0.887 arm
above a 1.000 arm, and the reader would have had no way to see why.

## The prediction that failed

Stated in advance: *no s > 1 will beat s = 1; the lossless gate is on the Pareto
frontier and lossy relaxation is never worth it here.* Wrong by 2.8% at
s = 1.40–1.50, and the interesting part is that the reason has nothing to do with
routing — it is arithmetic in the objective, and it would apply to any arm that
trades accuracy for cost anywhere in this repo.

## What would have refuted it

- **Noise.** Re-measured at N = 800 after seeing it at N = 300, where the gap was
  within one SE. At 800 the accuracy difference is 6.3 SE and the ordering is
  stable across slack 1.20–1.50.
- **A single cost outlier.** Cost is a mean over 800 runs; the per-episode figure
  moved by ~10% between runs under machine contention, which is why the argument
  above is made on the *relative* condition rather than on the absolute numbers.
- **The floor.** 0.440 throughout, the strongest of the seven from the earlier
  flood finding. A lower floor would make the perverse regime *worse*, not
  better, since it enlarges `acc − floor`.
