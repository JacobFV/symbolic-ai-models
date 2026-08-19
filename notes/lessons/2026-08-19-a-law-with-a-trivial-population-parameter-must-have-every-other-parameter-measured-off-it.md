---
title: A law with a trivial-population parameter must have every other parameter measured on the non-trivial population — I made this error twice
date: 2026-08-19
author: lead
status: provisional
tags: [lesson, theory, populations]
---

## The mistake, both times

`S = F + (1−F)q^k` has a parameter, **F**, that *is* a population: the cases whose
answer is already the degenerate one. Those cases have dependency zero by
construction. Any other parameter measured over the pooled set is therefore
diluted by them.

- **Flood.** Ablation gave mean dependency 6.95 and an implied exponent 5.76
  against a fitted 9.35. I printed **KILLED** and the verdict was wrong: 45% of
  cases had an empty answer. Split, the non-empty population gave 11.05.
- **Solvency, knowing all that.** Ablation gave mean 3.48 and an implied 2.06
  against a fitted 9.92. I printed **"k does NOT transfer"** at 381% error. The
  trivial population — 35 of 60 cases — has dependency **exactly 0.00**. Split,
  the non-trivial population gives 8.25, a 20.2% error.

## The tell I read past, twice

Both times the dependency distribution was **visibly bimodal** and printed in the
output. Solvency: *mean 3.48, sd 4.15, min 0, max 9*. A standard deviation larger
than the mean, with a minimum of zero, is not a distribution to take a mean of.

## The other thing that went wrong

Before finding the population, I hypothesised **interactions** — pairs that are
harmless alone and fatal together — and tested it: pair survival 0.589 against an
independence prediction of 0.606, gap +0.016. **No interaction effect.** Testing
the plausible mechanism instead of assuming it is what forced the right reading;
had I asserted it, the finding would have carried a mechanism that is not there.

## The guard

> **If a law has a parameter that names a population, every other parameter is
> conditional on the complement.** Measure them there, and say so in the code
> rather than in a note — a comment at the measurement site survives the next
> session's memory and this note may not.

It is now written into `scripts/theory_transfer_solvency.py` at the ablation
loop. And the general check: **before taking the mean of a per-case quantity,
look at its spread.** Both failures would have been caught by noticing that sd
exceeded the mean.

Related: `notes/lessons/2026-08-18-slices-invert-results-six-times.md`,
`notes/lessons/2026-08-18-a-validation-that-reproduces-its-own-definitions.md`.
