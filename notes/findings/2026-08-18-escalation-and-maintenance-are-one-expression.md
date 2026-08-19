---
title: Escalation targeting and certificate maintenance are one expression — and the achievable ceiling is 1/f_needed, not §3b's 1/f_flagged, the two differing by the certificate's over-approximation
date: 2026-08-18
author: lead
status: provisional
tags: [certificates, cost, derivation, unification, near-miss]
---

## Status: this is a derivation, not a measurement

Stated up front because the first version of this note was not. The algebra
below is correct and the empirical content is **five rows that were already
`HANDOVER.md` §3b's**. See
`notes/lessons/2026-08-18-a-validation-that-reproduces-its-own-definitions.md`.

## The two forms

§3b established, on a real corpus update and verified on both axes:

```
advantage = min(compute/check, 1/P_hit)
```

where `P_hit` is the rate at which the certificate is **invalidated**.

This session produced, on a different arm, that escalation targeting obeys
`aim ≤ 1/(1 − accuracy)`, where `1 − accuracy` is the fraction of cases that
**actually need** the expensive path.

## They are the same expression

With `f_flagged = P(the certificate/model flags this case)`,
`f_needed = P(this case actually needs the expensive path)`,
`precision = P(needed | flagged)` and `recall = P(flagged | needed)`:

```
realised  =  recall / f_flagged   =   (1/f_needed) × precision
ceiling   =  1 / f_needed         attained iff precision = recall = 1
```

- A **sound** certificate has `recall = 1` and realises `1/f_flagged` — **§3b's
  law exactly**.
- A **model's abstention is not a soundness claim**, so `recall < 1`: it is also
  wrong on positions it voted on. `ilp-001` has `recall = 0.535`.
- An **oracle** has `precision = recall = 1` and attains `1/f_needed`.

> **§3b's `1/P_hit` is the sound case. The achievable ceiling is `1/f_needed`,
> and the two differ by exactly the certificate's over-approximation** —
> measured independently at **8.2×** for the symmetric-difference bound and
> **2.3×** for `|Δcount|`.

## What is actually confirmed

`scripts/certification_law.py` prints twelve rows and labels each. Seven are
**identities** — their "measured" value is computed from the same expression as
the prediction, so they cannot disagree. Five are **independent**: the measured
advantage comes from timings and USD, the prediction from invalidation counts.

| row | f_flagged | predicted | measured | error |
|---|---:|---:|---:|---:|
| §3b witness (the path's edges) | 3.4e-05 | 29,389.5× | 29,182.1× | 0.7% |
| §3b optimality, recorded frontier | 0.3061 | 3.27× | 3.27× | 0.0% |
| §3b optimality, minimal | 4.6e-05 | 21,788.8× | 21,534.3× | 1.2% |
| §3b full answer | 7.1e-05 | 14,120.1× | 13,987.1× | 1.0% |
| §3b maintenance, `min_filers_covering` | 1.0000 | 1.000× | 0.998× | 0.3% |

**No arm exceeds its ceiling of `1/f_needed`.** That is the one thing the whole
table could have falsified and did not — an advantage above `1/f_needed` would
mean certification bought more than the work it avoided.

The other three maintenance classes are limited by `compute/check` instead, so
the `1/P_hit` term is not the binding one and they cannot test it. That is why
only one of the four appears.

## Why the unification is worth having anyway

Because it says where to look. Two quantities decide any certification
opportunity, and both are measurable **before** building anything:

- **`f_needed`** sets the ceiling. If few cases need the expensive path, a
  certificate can be worth thousands; if most do, nothing can help.
- **`f_flagged / f_needed`** is what your mechanism wastes, and it is a property
  of the *answer's sensitivity* rather than of the recording mechanism — which
  is why a read set and a derived margin over identical inputs differ 79.8× and
  1.1×.

It also explains the session's whole 1.02×–131.6× spread without any new
measurement: the curriculum models are 7.7–32.9% accurate, so `f_needed` is
0.67–0.92 and no abstention policy can be worth more than 1.49×.

## What would refute it

- **An advantage above `1/f_needed`** on any arm. None found, over five
  independent rows spanning 1.0× to 29,182×.
- **The `compute/check` term.** This note is entirely about the other term of
  §3b's `min(...)`, and for three of four maintenance classes that other term is
  the one that binds. The unification says nothing about which term wins.
- **`recall` is inferred, not measured, for the escalation rows.** It is derived
  from the accuracy split rather than counted directly, so those rows are part of
  the algebra rather than evidence for it.

## Reproduce

```bash
uv run python -u scripts/certification_law.py
```

`runs/certification_law.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `is-the-ceiling-a-law`.
