---
title: A verification-versus-solving ratio measured against your own solver is mostly a claim about your solver
date: 2026-08-18
tags: [lesson, measurement, cost]
---

## The mistake

I measured how much cheaper it is to *check* a datalog derivation than to
*produce* it, and got **2,702,920x**. The number is arithmetically correct and
it is 99.98% an artifact: my datalog engine indexes facts by predicate only, so
a recursive join rescans the whole relation and does quadratic work for linear
output. Against a purpose-written closure computing the identical result, the
ratio is **496x** at the same database size, and **23x** at a small one.

I caught it before publishing because the last three findings all turned on my
own method being the weak part — a trailing-only string rule, an "optimised"
certificate scan that was slower, a hand-written suffix list that a one-pass fit
beat. So the habit is now to ask, before quoting any ratio, *which side of it is
my code?*

## The mechanism

A ratio has a numerator and a denominator, and **only one of them is usually the
thing being claimed**. "Verification is cheap" is a claim about verification;
the denominator is whatever solver happened to be lying around. If that solver
is mine, the ratio silently reports my competence at writing solvers and
presents it as a property of the problem.

This is worse than an ordinary confound because it is **self-flattering by
construction and invisible in the units**. A slow denominator makes the finding
more impressive, the number is real, the code is correct, and nothing in the
measurement complains. Every incentive points the same way.

It also generalises past speed. Any *X-versus-Y* ratio — accuracy against a
floor, cost against a baseline, a lift over a control — inherits the quality of
whatever is in the denominator, and this repo has already been burned by the
same shape twice from the other end: a floor 0.58 too low, and a
"first-of-nineteen" lift measured against a floor that was under-fitted.

## The guard

- **Before quoting a ratio, name the denominator's provenance.** "Cheaper than
  solving" is not a claim until *whose* solving is stated.
- **Put the best available alternative in the denominator, not the convenient
  one.** Fifteen lines of purpose-written code was enough here, and it moved the
  headline by four orders of magnitude.
- **If the denominator is your own code, say so in the finding**, and report
  both numbers. The inflated one is still informative — it measures the cost of
  generality — but it is a different claim and must be labelled as one.
- **Suspect ratios that grow.** The overhead here went 495x → 5,446x with size,
  which is the signature of an asymptotic defect in the denominator rather than
  a property of the numerator.
