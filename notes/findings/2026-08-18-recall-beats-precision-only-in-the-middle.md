---
title: The flood task's "fragility is in domain membership" generalises only in a middle regime — at large decision margins the ordering inverts from 1.74× to 0.11×
date: 2026-08-18
author: lead
status: provisional
tags: [second-task, generalisation, refuted-prediction, correction]
---

## Why this was run

Every substrate finding until today came from one generated task. That is the
single-task confound this repo's own lessons warn about, and the flood work
produced one claim I generalised explicitly and confidently:

> The fragility is in the facts that define the answer's **domain**, not in the
> facts that constrain it… If it generalises to enumerate-then-filter pipelines
> — and the mechanism is about conjunctions with no redundancy, which is not
> specific to bridges — then recall on entity and attribute mentions is worth
> more than precision on numbers.

The solvency task is structurally opposite — aggregate-and-compare rather than
enumerate-and-filter — so the claim can be tested rather than asserted.

## Prediction, before the numbers

Stated in advance: the same ordering holds; at rate 0.20, dropping costs
0.35–0.55 error and misreading 0.10–0.20.

Measured at the default covenant: **dropping 0.31, misreading 0.21** — both below
the predicted bands, and a ratio of 1.46× against flood's 1.76×. Close enough to
look like confirmation, which is exactly why it was worth pushing on.

## Measured — the decision margin is the variable

Sweeping how far the covenant bar sits from the group's first-vintage total,
corruption rate 0.20 throughout. N = 300 for the first two rows, **N = 1,200**
for the rest, because the rates get small:

| slack | drop error | misread error | **ratio** |
|---|---|---|---|
| 0.00 | 0.383 | 0.273 | 1.40 |
| 0.10 | 0.243 | 0.107 | 2.28 |
| **0.25** | **0.138** | **0.079** | **1.74** |
| 0.50 | 0.039 (47/1200) | 0.058 (70/1200) | 0.67 |
| 1.00 | 0.006 (7/1200) | 0.052 (63/1200) | **0.11** |

The flood task measured **1.76×**. The solvency task reproduces **1.74×** — at
slack 0.25, and nowhere else.

## What it says

> **Whether recall or precision errors dominate is set by the ratio of the
> decision margin to the size of a typical error — not by the kind of fact.**

Missing a term is a **bounded, additive** error: it moves the total by about 1/n
of it, always. Misreading a value is **unbounded and multiplicative**: a digit
slip or a units confusion moves it by a factor. So:

- **no margin** — everything flips, both channels converge, ratio → 1.4;
- **moderate margin** — a missing term still clears the bar while most
  misreadings do not, so additive-but-certain beats multiplicative-but-rare;
- **large margin** — a missing term can no longer move the total far enough at
  all, and only the multiplicative error survives. Ratio **0.11**: 7 flips from
  dropping against 63 from misreading.

The flood task sat in the middle regime. Its bridge limits gave moderate slack
and its precision channel was digit-level, so recall won — and I read a property
of that regime as a property of pipelines.

The corrected claim keeps what was right and names the boundary. It also explains
the flood result rather than merely restating it, which the original did not.

## What would have refuted it

- **The inversion being noise.** Re-measured at N = 1,200 with counts shown:
  7 against 63 at slack 1.00 is not a coincidence, and the trend is monotone in
  the ratio across five slack levels.
- **The corruption channels being unequal in strength.** The solvency misreading
  set (×0.1, ×10, ±10%, ±25%) is *milder* than the flood one, which included a
  ×1000 units confusion — so if anything this understates the precision channel
  and the inversion is conservative.
- **The kernel disagreeing with the oracle.** It matches the independent
  brute-force answer on 400/400 uncorrupted cases, so the errors measured are the
  corruption's and not the kernel's.

## What this does not establish

Both magnitudes are properties of two generated tasks with invented corruption
models. The **ordering and its dependence on the margin** are the transferable
part, because they follow from additive-versus-multiplicative error structure
rather than from either generator's parameters.

And two tasks is two. The claim now has a stated regime, which is the honest
form, but a third task in a different regime again is what would test the regime
boundary itself rather than its existence.
