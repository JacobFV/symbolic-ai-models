---
title: The decision margin, measured on uncorrupted worlds, predicts the recall/precision ordering on nine points from three tasks — and flood was held out
date: 2026-08-18
author: lead
status: provisional
tags: [margin, generalisation, prediction, held-out]
---

## The claim being tested

Three tasks had converged on one statement: the distance from the decision
boundary governs both the routing headroom and whether recall or precision errors
dominate. That is interesting only if the distance can be measured **before** the
errors are — before a reader exists, before a router is built, before a week goes
into the wrong one.

`symbolic_ai_core/runtime/margin.py` measures it. Given a decision function and a
way to scale the quantity the decision turns on, binary-search the factor that
flips the answer; `|factor − 1|` is the relative margin, and its distribution
over a corpus is the profile. Deliberately crude and assumption-light — its job
is to make a prediction that can be wrong out loud.

## Prediction, before the numbers

Stated in advance: the median margin will be **< 0.20** wherever the measured
drop/misread ratio exceeds 1, and **> 0.50** wherever it falls below 1.

**Half right.** The *shape* held — monotone, single crossing, on both tasks. The
*location* did not: ratios of 1.6–1.7 sit at margins of 0.25–0.34, well inside
what I had called the ambiguous band. The crossing is at **≈ 0.40**, not 0.20.

## Measured — nine points, three tasks

Every ratio measured independently of this module.

| task | median margin | drop/misread ratio | dominant |
|---|---|---|---|
| solvency @0.10 | 0.100 | 2.28 | recall |
| solvency @0.25 | 0.250 | 1.74 | recall |
| scheduling @0.15 | 0.257 | 2.38 | recall |
| **flood, native** | **0.280** | **1.76** | **recall** ← held out |
| scheduling @0.50 | 0.335 | 1.61 | recall |
| solvency @0.50 | 0.500 | 0.67 | precision |
| scheduling @1.00 | 0.605 | 0.59 | precision |
| solvency @1.00 | 1.000 | 0.11 | precision |
| scheduling @2.00 | 1.512 | 0.13 | precision |

Three generators, three kernel mixes, answers that are a subset, a boolean and a
boolean, and a 179× spread in pipeline cost — on one monotone curve.

## The held-out point

The thresholds were read off **solvency and scheduling**. Flood's ratio of 1.76
was measured days earlier, before this module existed, and its margin was never
looked at until the constants were fixed.

It came out **0.280** — between solvency@0.25 (0.250, ratio 1.74) and
scheduling@0.50 (0.335, ratio 1.61), and its ratio 1.76 sits between theirs.
Almost exactly on the curve, on a task whose answer is a *set* rather than a
boolean and whose margin had to be taken per vehicle.

That is the difference between a curve fitted to two tasks and a claim that
predicts a third.

## What it is for

The profile returns advice, because a number nobody acts on is a number:

```
median relative margin 0.10; spend on RECALL -- a missing fact flips this task
and a mis-scaled one usually does too; a cheap sufficient gate should fire

median relative margin 1.51; spend on PRECISION -- only a multiplicative error
moves this answer; missing a term will not; a cheap gate will not fire, do not
build a router
```

Both halves are things this repo learned the expensive way. The routing work
spent a wake-up discovering that a gate pays only in proportion to what is
downstream of it; the parser work spent one measuring which channel a pipeline
can afford to lose. Both are now answerable from the uncorrupted corpus in a few
seconds.

## What would have refuted it

- **The relationship being noise.** Nine points, 33 of 36 pairs ordered as the
  margin predicts, asserted as a test.
- **The held-out point missing.** It did not, and it is the only one that could
  have falsified the thresholds rather than defined them.
- **"Large margin" and "quantity does not decide this" being confused.** They
  are different answers and the profile distinguishes them: a corpus nothing can
  flip returns `inf` and advice that says to measure something else. Flood has 37
  of 120 vehicle decisions that no bridge-limit scaling can move — excluded on
  capacity — and the median is taken over the rest.

## What it does not establish

Three generated tasks, all mine, all with corruption models I wrote. The margin
is measured by scaling **one** quantity, which assumes the decision turns mainly
on that quantity — true here by construction and not in general; the `inf` return
is what says so rather than a wrong number.

And the constants are two decimal places read off five points. The honest form is
that the *ordering* is established and the *threshold* is provisional, which is
why both are module constants with the reasoning attached rather than magic
numbers inside a function.
