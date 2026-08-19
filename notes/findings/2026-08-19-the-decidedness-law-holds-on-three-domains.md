---
title: The decidedness law holds on three domains, and the two estimators swap places
date: 2026-08-19
status: measured
arm: decidedness-cross-domain
domains: flood, scheduling, solvency
---

## Correcting my own scope note first

The previous finding recorded *"still one domain — scheduling and solvency cannot
test it because neither has an ambiguity worth carrying."*

**That was wrong.** The law is about the **deletion dependency of a claim kind**,
which every domain has and which needs no reader at all; only the *policy* needs
one. Solvency's `revenue` and `owns`, and scheduling's `duration`, `capacity`,
`needs_capability` and `has_capability`, are all deletable and all measurable.

## The law is cross-domain

Three domains, twelve claim kinds, on the non-degenerate population:

| | mean signed error | mean absolute error |
|---|---:|---:|
| **(1 − d̄)^n̄** | **+0.005** | **0.033** |

No free parameter — `d` and `n` are both measured. `decided = (1 − d)ⁿ` holds
across flood, scheduling and solvency to 3.3 points, essentially unbiased.

The extremes are worth naming because they are the mechanism showing through:
solvency's `revenue` decides **0.000** (every filing moves the sum, so nothing is
inert) while its `owns` decides **1.000** (ownership is recoverable from the
filings themselves, so nothing is load-bearing). Same law, opposite ends.

## The two estimators swap places, and I predicted the wrong swap

`decided = P(k = 0)` where `k` is the number of load-bearing claims. Two ways to
estimate it:

- **mean-d**: `(1 − d̄)^n̄`, pooling `d` across cases first.
- **per-case**: `E[(1 − d_case)^n_case]`.

| population | per-case signed | per-case \|err\| | mean-d signed | mean-d \|err\| |
|---|---:|---:|---:|---:|
| pooled | −0.040 | **0.040** | +0.183 | 0.183 |
| non-degenerate | −0.051 | 0.051 | **+0.005** | **0.033** |

I predicted per-case would win everywhere. It wins **only when pooling**, and
loses on the clean population.

**Why per-case wins pooled.** Averaging `d` before exponentiating over a bimodal
case mix fails by Jensen. That — not correlation between deletions — is what the
previous finding's +0.131 pooled residual actually was. The earlier explanation
(*"structural redundancy makes several claims inert at once"*) was a mechanism
invented to fit a number that had a simpler cause.

**Why per-case loses clean.** It **smooths a deterministic outcome**. Within a
case, `d` is measured from the very deletions being tested, so with `k` of `n`
load-bearing the truth is exactly 0 for any `k ≥ 1`, while `(1 − k/n)ⁿ` stays
positive. That is the systematic over-prediction visible in its signed error
(−0.040, −0.051 in both populations), and it is a property of the **estimator**,
not of the domain.

So: **use mean-d on a homogeneous population; use per-case only if you must
pool.** That is a more useful statement than either form alone, and it is why the
population split had to be reported rather than a single pooled comparison.

## What is established now

- Controlling variable: dependency under the carried perturbation.
- Functional form: `(1 − d)ⁿ`, derived, unfitted, **0.033** mean absolute error
  over twelve kinds in **three** domains.
- Both inputs computable from the world alone, so the decidedness of an
  emit-rather-than-collapse policy can be forecast before any reader exists.
- The one earlier failure is explained (Jensen over a bimodal mix) rather than
  excluded by a population rule.

## What is still not established

That this predicts a **reader's** decidedness. The law characterises the domain;
a policy enumerates over the *read* world, whose `d` and `n` differ. The
true-world flood link row reads 0.153 predicted / 0.000 observed on non-degenerate
cases while the read-world carrying experiment read 0.588 — different worlds, and
comparing them directly remains the next available mistake.

## Track record on this thread, since it is the point

Four formulations, three wrong: hypothesis size (wrong variable), collision cost
(right direction, wrong quantity — two numbers that agreed by accident),
correlation between deletions (a mechanism invented for a Jensen artefact). The
fourth survives, cross-domain, with no free parameter. Each was caught by
building the next experiment on the previous claim rather than by polishing it.
