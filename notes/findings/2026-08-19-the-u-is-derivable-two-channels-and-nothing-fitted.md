---
title: The U-shaped corruption curve is derivable from structure alone — two channels, no fitted parameter, 0.069 mean absolute error — and the first version was half the depth because it forgot a machine needs two claims
date: 2026-08-19
author: lead
status: provisional
epistemic_status: derived mechanistic model, unfitted, checked on two difficulty settings
tags: [theory, scheduling, derivation, monotonicity]
---

## The problem the last finding left

Scheduling's corruption curve is **U-shaped**: dropping job claims removes demand
and makes instances feasible, dropping machine claims removes supply and makes
them infeasible. `S = F + (1−F)q^k` is monotone by construction and cannot
represent it.

The temptation is to fit a two-term curve. The better move is to **derive** one,
because every quantity involved is structural.

## The derivation

An instance reads feasible iff every surviving job has a capable, usable
surviving machine.

- A job is a constraint at all only if **both** its claims survive — its
  `duration` and its `needs_capability`: probability `(1−p)²`.
- A machine is usable only if **both** its claims survive — its
  `has_capability` and its `capacity`: probability `(1−p)²`.
- A surviving job is unsatisfiable only if **all** `mⱼ` machines carrying its
  capability are unusable.

Assuming independence across jobs,

```
P(answer = True | p)  =  Π_j [ 1 − (1−p)² · (1 − (1−p)²)^mⱼ ]
```

**Nothing is fitted.** `mⱼ` is the capability multiplicity, counted from the
claims. The form is U-shaped by construction — it tends to 1 at `p = 0` because
nothing is lost and to 1 at `p = 1` because no job survives as a constraint.

## Measured, on originally-feasible cases

| | mean \|error\| |
|---|---:|
| slack 0.30, n = 29 | **0.070** |
| slack 0.60, n = 47 | **0.069** |

At slack 0.60 (`p` across the row):

| p | 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.8 | 1.0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| measured | 1.000 | 0.750 | 0.612 | 0.511 | 0.495 | 0.420 | 0.404 | 0.527 | 1.000 |
| **derived** | 1.000 | **0.751** | 0.553 | 0.431 | 0.386 | 0.407 | 0.491 | 0.799 | 1.000 |

Both endpoints exact, the trough located, and 0.751 against 0.750 at p = 0.1 —
from a formula with no free parameter.

## The correction, and why the first version was wrong

The first derivation had a machine survive with `(1−p)`, modelling only the loss
of its **capability**. That gives the right shape at **half the depth** — a
trough of 0.678 against a measured 0.336 — and a mean error of **0.234** and
**0.172** at the two slacks.

A machine also needs its **capacity** claim to be usable. Requiring both takes
mean error to **0.070** and **0.069**: a **2.5× improvement from one exponent**,
predicted from the structure rather than fitted to the residual.

> **The U is not a curve family chosen to match. It follows from two claims per
> job and two claims per machine, with `mⱼ` machines per capability.**

## What it does not cover

The unconditional curve is still badly predicted, because the model says every
case is feasible at `p = 0` and 42.5% of them are not — at slack 0.30 the
measured curve starts at 0.575 and the derived one at 1.000. **Capacity as a
binding constraint on the original instance is a separate term and is
co-dominant, not a correction**; conditioning on originally-feasible cases is
what isolates the mechanism this model captures.

That is a stated boundary rather than a fudge: the model predicts *how corruption
moves a feasible instance*, not *which instances are feasible*.

## What would refute it

- **Independence across jobs is assumed** and is false when jobs compete for the
  same machine. The residual is largest at `p = 0.8` (0.527 measured against
  0.799 derived), which is where few machines survive and competition is
  strongest — consistent with that being the assumption that pays.
- **Two slack settings, one generator.**
- **`mⱼ` is read from the uncorrupted world.** A reader would have to recover it,
  so this predicts the curve for an oracle-world corruption sweep, not for a
  reader.

## Reproduce

```bash
uv run python -u scripts/two_sided_form.py
```

`runs/two_sided_form.json`, `runs/two_sided_conditional.json`.
