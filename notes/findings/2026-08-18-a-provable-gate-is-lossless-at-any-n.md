---
title: A provable gate's accuracy is a theorem and a learned gate's is a sample estimate — boosted trees capture 19.3% of the routing headroom against 14.5%, and are wrong once per 750 worlds
date: 2026-08-18
author: lead
status: provisional
tags: [routing, learning, cost, correction]
---

## Why this exists

`2026-08-18-learning-does-not-beat-proof-where-proof-is-available.md` ended by
naming its own falsification: *a gradient-boosted tree on the same features; if
it captures materially more than 16.6% at bar 1.00, this note is wrong about
why.* It was run. It does. **The earlier headline was too strong**, and the
correct statement is sharper than either "learning wins" or "proof wins".

## Prediction, before the numbers

Stated in advance: the boosted gate captures **12–20%** of headroom at bar 1.00,
above the logistic model's 11.1% and around the hand gate's 13.7%; more than 30%
would falsify the ceiling argument.

Measured **16.7%** at N = 400 and **19.3%** at N = 1,200 — inside the predicted
range, and above the hand gate. The ceiling argument survives; the headline
above it does not.

## Measured

Eval seeds 1,000,000–1,001,199 (N = 1,200), threshold tuned on a development
split from 500,000, fitted on seeds 0–799.

| arm, at bar 1.00 | acc | $/episode | cheap share | headroom | **wrong** |
|---|---|---|---|---|---|
| always full | 1.000 | 1.468e-08 | 0.000 | 0.0% | 0 |
| **hand gate (provable)** | **1.000** | 1.390e-08 | 0.139 | 14.5% | **0** |
| logistic (thr 0.71) | 1.000 | 1.404e-08 | 0.121 | 12.0% | 0 |
| **boosted trees (thr 0.71)** | **0.999** | 1.364e-08 | 0.158 | **19.3%** | **1** |
| ORACLE (cheats) | 1.000 | 8.923e-09 | 0.551 | 100.0% | 0 |

And the decisive check — three **disjoint** 1,000-seed ranges:

| eval range | hand wrong | logistic wrong | boosted wrong |
|---|---|---|---|
| 1,000,000 +1000 | 0 | 0 | **1** |
| 1,100,000 +1000 | 0 | 0 | **2** |
| 1,200,000 +1000 | 0 | 0 | **1** |

## What it says

> **A provable gate's accuracy is a theorem. A learned gate's accuracy is a
> sample estimate, and the difference only becomes visible as the sample grows.**

At N = 400 the boosted gate scored 1.000 and looked lossless. At N = 1,200 it is
0.999. Across 3,000 seeds it is wrong four times — an error rate near 0.13%,
stable, and **not removable by more held-out evaluation**, because it is a
property of the model rather than of the measurement. The hand gate's two
conditions cannot be wrong at any N: if the demand site is unreachable no vehicle
can serve it, and if every qualifying laden mass clears the lightest posted limit
no bridge can bind.

So the three arms are answering three different questions:

- **hand gate** — the most headroom obtainable with a *guarantee*: 14.5%.
- **logistic** — a learned gate tuned so conservatively that it happened to be
  lossless over 3,000 seeds, and paid 2.5 points of headroom for a safety it
  cannot promise: 12.0%.
- **boosted trees** — the most headroom obtainable while being wrong about one
  world in 750: 19.3%.

The middle row is the one worth pausing on. It is *worse than the proof on both
axes*: less headroom, and no guarantee. A conservatively tuned learner is not a
safe learner; it is an expensive one.

## What this does not change

The ceiling stands. The cheap answer is already correct on **55.1%** of worlds,
worth a 39% cost saving, and the best gate here captures 19.3% of it. The
explanation in the earlier note — that the residual is *coincidental* agreement,
which no cheap feature can distinguish from structural agreement because what
distinguishes them is the full answer — is untouched by this result and is what
the 30% falsification threshold was testing.

## What would have refuted it

- **The error being a fluke of one seed range.** Three disjoint 1,000-seed
  ranges, 1/2/1 errors, hand gate 0 throughout.
- **The boosted model being broken rather than better.** It solves XOR where the
  logistic model provably cannot, asserted as a test — which is exactly the
  interaction structure that lets it find headroom the linear model leaves.
- **The comparison mixing runs.** All rows in the first table are from one run;
  the cost baseline moves ~5% between runs under contention and has already
  nearly reversed one headline in this series.
