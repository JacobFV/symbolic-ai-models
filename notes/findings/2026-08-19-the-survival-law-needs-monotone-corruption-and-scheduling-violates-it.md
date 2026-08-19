---
title: The survival law has a precondition — every claim must be evidence in the same direction — and scheduling violates it, giving a U-shaped corruption curve a monotone form cannot fit
date: 2026-08-19
author: lead
status: provisional
epistemic_status: scope result; the law's referent survives, its functional form gains a precondition
tags: [theory, law-scope, monotonicity, scheduling, negative-result]
---

## Why a third domain, and why not just confirmation

`S = F + (1−F)q^k` had transferred once, with both parameters predicted from
structure. A third domain would mostly confirm. Scheduling is worth running for a
different reason: it has a **tunable decision margin** neither previous task had,
so the question becomes *what governs the parameters* rather than *does it hold
again*.

It turned out to answer a better question than that.

## F's referent survives

The degenerate answer — what the kernels return on an **empty world** — is `True`
here: no jobs, so every job is vacuously assignable. It was the empty set in
flood and `False` in solvency, so this is the referent's third distinct value.

At slack 0.60 the feasible share is **0.850**, and the corruption curve at full
corruption is:

```
p=0.50: 0.483   p=0.80: 0.500   p=0.90: 0.600   p=0.95: 0.692   p=1.00: 0.850
```

**Exactly the feasible share at p = 1.** `F = P(truth == degenerate answer)`
holds on all three domains.

## The functional form does not

The curve **dips and comes back**. `S = F + (1−F)q^k` is monotone decreasing in
`p` by construction, so it cannot represent that. Fitted to the U it reports
`F = 0.593` where the true value is **0.850**, and rmse rises to **0.08** against
solvency's 0.007.

### Why, measured

P(answer = `True`) as claims are dropped, by channel, at slack 0.30:

| channel dropped | 0.00 | 0.20 | 0.50 | 0.80 | 1.00 |
|---|---:|---:|---:|---:|---:|
| **jobs** (`duration`, `needs_capability`) | 0.575 | 0.883 | 0.992 | **1.000** | 1.000 |
| **machines** (`capacity`, `has_capability`) | 0.575 | 0.133 | 0.008 | **0.000** | 0.000 |
| all claims | 0.575 | 0.400 | 0.375 | 0.575 | **1.000** |

Each channel alone is **monotone, and they run in opposite directions**. A job
claim is a *demand* — dropping it makes the instance easier. A machine claim is
*supply* — dropping it makes the instance harder. The composite U-shape is their
superposition, with supply dominating in the middle and demand winning at the
limit.

> **The law's precondition is that every claim is evidence in the same direction
> for the answer.** Flood and solvency satisfy it: there, losing a claim only
> ever destroys the answer. Scheduling mixes demand and supply and does not.

## Why this is worth more than a third confirmation

The law now has a **stated scope and a task that falls outside it**, rather than
three domains of agreement and unknown limits. And the precondition is checkable
before any sweep: drop each claim kind alone and see whether the answer moves one
way. If two kinds move it opposite ways, the monotone form does not apply and
`F` read off a fit will be wrong — as it is here by 0.257.

This also connects to something the repo measured on the certificate arm — the
monotone/antitone distinction over noisy worlds — arrived at from the other end.

## What I predicted and got wrong

I predicted `F` would track the slack knob and be recoverable from the fit at
every setting. It tracks the knob **as a referent** (p = 1 agreement) and is
**not** recoverable from the fit, because the fit is of the wrong shape. My
prediction conflated the parameter with the fitted value, which is exactly the
distinction this result turns on.

I also predicted `k` would rise as slack tightens. It is not measurable here at
all — a fitted `k` on a U-shaped curve means nothing — so the question is
unanswered rather than answered negatively.

## What would refute it

- **One violating task.** The precondition is stated from one mechanism seen
  once. A second monotone-violating task should show the same U.
- **The channel split is mine.** `duration`/`needs_capability` as demand and
  `capacity`/`has_capability` as supply is a reading of the generator, though the
  measured curves are unambiguous about which way each moves the answer.
- **A two-sided form might fit.** Nothing here says the curve is unmodellable,
  only that a monotone one-parameter decay is the wrong family. A form with a
  demand term and a supply term is the obvious candidate and was not tried.

## Reproduce

```bash
uv run python -u scripts/law_parametric_scheduling.py
```
