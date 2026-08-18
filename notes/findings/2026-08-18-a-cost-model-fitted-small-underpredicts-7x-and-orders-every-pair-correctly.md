---
title: A cost model fitted at small scale under-predicts the full corpus by 7x and orders every pair correctly — which makes it useless for budgeting and perfect for routing
date: 2026-08-18
status: provisional
tags: [kernel-abi, cost, routing, calibration, real-data]
---

## The hunt this came from

Yesterday's fix ended on a general lesson: **a claim nothing exercises is a
claim nothing checks.** `add_facts` had promised delta-proportional cost in a
docstring, every design decision cited it, nothing ran it, and it was false by
three orders of magnitude.

So I went looking for the same shape somewhere higher-stakes. `KernelManifest`
has carried `cost_estimator` since the ABI was written, and the entire cost
programme — `$/solved-episode`, the advantage curve, the routing work — rests on
knowing what a kernel costs.

**Prediction: zero of the eight kernels supply one and nothing compares an
estimate to a measurement.** Confirmed exactly: `grep` finds `cost_estimator` in
one place in the repo, its own declaration. Not wrong, like the delta contract —
**absent**, which is the same defect one stage earlier.

## What a router actually needs, which is not accuracy

A router chooses between options, so what matters is whether an estimate
**orders** them correctly. An estimator uniformly 3x low is useless by relative
error and perfect for routing; an unbiased but noisy one is the reverse.
`Calibration` therefore reports both, and the finding is that the distinction is
not academic.

## Predictions

Fitting `cost = a·size^b` on measured datalog closures:
1. Interpolation (fit alternating sizes, predict the rest): **median relative
   error < 25%**, ordering **> 0.90**.
2. Extrapolation (fit the five smallest, predict the five largest):
   **median error 40–80%**.

## Measured, GLEIF ownership closure, 250 to 124,460 edges

| | fitted exponent | median error | p90 | **ordering** | bias |
|---|---|---|---|---|---|
| interpolation | 1.326 | **22.8%** | 42.1% | **1.000** | 0.92x |
| extrapolation from the small end | 1.039 | **71.3%** | 85.8% | **1.000** | **0.30x** |

Prediction 1 held on error (22.8%, just inside 25%) and understated ordering,
which was perfect rather than merely good. Prediction 2 held squarely.

The extrapolation failure is **systematic and monotone**:

| edges | predicted | actual | ratio |
|---|---|---|---|
| 8,000 | 41.9 ms | 70.2 ms | 0.60x |
| 16,000 | 86.2 ms | 224.9 ms | 0.38x |
| 32,000 | 177.2 ms | 617.0 ms | 0.29x |
| 64,000 | 364.1 ms | 1,523.9 ms | 0.24x |
| **124,460** | 726.8 ms | 5,109.8 ms | **0.14x** |

**Seven times too low at the size that matters, and every single pair ordered
correctly.**

## The mechanism, and why the exponent is not a complexity class

The fitted exponent depends entirely on where you fit it: **1.04** over 250–4,000
edges, **1.33** over the whole range, **1.56** over the large end alone. At small
scale fixed overhead dominates and flattens the apparent slope, so a law fitted
there is a law about the overhead. Extrapolating it under-predicts, and because
the true cost is monotone in size the ordering survives untouched.

This is the same shape as two earlier findings and I now think it is one
mechanism: **a measurement taken in the cheap regime describes the cheap
regime.** The floor audit found the strongest floor at an interior grid
resolution; the sensitivity work found amplification unpredictable from
aggregate statistics; here a small-scale fit describes constant overhead.

## What was built

`symbolic_ai_core/runtime/estimate.py` — `Observation`, `PowerLawCost`,
`fit_power_law`, and `Calibration` reporting median error, p90, **ordering** and
geometric bias separately. `Observation` refuses a zero rather than taking its
log. `calibrate` refuses to score on the fitting points.

`datalog@1` is now the first kernel in the stack whose manifest actually carries
an estimator, with its calibration published beside it and the docstring saying
plainly: **use it to order candidate plans, not to budget one.**

## What would refute it

- One kernel, one rule shape, one relation. A kernel whose cost is genuinely
  non-monotone in its input size would break the ordering result, and that is
  the case to look for next — SMT is the obvious candidate, where a slightly
  larger problem can be dramatically easier.
- The whole-range fit over-predicts at the top of its own range (9.3 s against
  5.1 s measured, 1.8x high) while the small-end fit under-predicts. Both are
  "wrong by about 2x in opposite directions", and no single power law fits a
  cost curve whose slope changes.
- Ordering was measured on runs differing by 2x or more in size. Two candidate
  plans of nearly equal cost are the case where ordering fails, and they are not
  in this sample.
