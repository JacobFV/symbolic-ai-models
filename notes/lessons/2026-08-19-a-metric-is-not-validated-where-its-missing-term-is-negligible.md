---
title: A metric is not validated where its missing term is negligible
date: 2026-08-19
status: lesson
---

## The mistake

Every milestone in this repo priced **kernel artifacts only**, while
`CLAUDE.md` says cost is charged to the *system* and `cost.py`'s `System` exists,
in its own docstring, because *"`sum` is not optional"*.

The omission survived because it was invisible in two of three domains: reading
is 1.9% of flood's wall clock and 0.9% of scheduling's. In the third it is
**96.1%**, and the ledger was pricing **4%** of what solvency runs — a 33.4×
error in the north-star number.

## Why that shape is dangerous

A missing term gets validated by every case where it is small. Flood and
scheduling agreed with the kernel-only figure to 1–2%, which reads as
confirmation. It is not: they agree because the *term is negligible there*, which
says nothing about a case where it is not.

Worse, the case where it is not negligible is the one the programme's thesis is
about. The argument is that symbolic reasoning is **cheap**. Wherever that is
true, reading is what you are paying for — so the metric fails exactly where the
claim is strongest.

## The guard

Two parts, and the second matters more.

1. **Make the omission visible at the point of use.** `Component` now carries a
   `stage` (`"read"`/`"solve"`/`"render"`), and `ledger()` emits a note when a
   system declares stages and none of them is `read`. The note carries the three
   percentages, because a guard that only says *missing* invites being ignored.

2. **Check a metric on the case where its missing term dominates, not on the
   cases where it is small.** No amount of agreement in the 1% regime would have
   found this. The finding came from adding a third domain whose kernel does
   almost nothing.

The guard has a real limit, recorded rather than hidden: it is **opt-in**. A
caller that declares no stages gets no check, because the alternative was a note
every existing caller would receive and could not act on. `System` still cannot
detect a component nobody handed it.

## Related

- [[2026-08-19-the-ledger-was-pricing-four-percent-of-solvency]]
- Same family as *state the bound, not the number*: both are cases where a
  measurement was reported as though it constrained something it never sampled.
