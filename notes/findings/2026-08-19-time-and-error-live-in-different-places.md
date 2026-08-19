---
title: Time and error live in different places
date: 2026-08-19
status: measured
arm: solvency-milestone
domains: flood, scheduling, solvency
---

## The third corner

Flood and scheduling had end-to-end milestone rows; solvency never did. It now
does, and it is the corner that makes the other two readable.

| system | filing R | task acc | ms/case | grounded |
|---|---:|---:|---:|---:|
| oracle (ceiling) | 1.000 | 1.000 | 0.0021 | 1.000 |
| signature reader, as published | 1.000 | 1.000 | 0.219 | 1.000 |
| signature reader, unsaturated | 1.000 | 1.000 | 0.214 | 1.000 |
| signature reader, **interleaved** | **1.000** | **1.000** | 0.214 | **1.000** |

Reader loss **0.000**, unchanged by interleaving, grounding intact. Bound at
n=200: 1.50%.

## And a gap in the metric it was measured with

Solvency's reader takes **0.219 ms** against a decision costing **0.0021 ms** — a
factor of a hundred. But the milestone's `$/correct` prices **kernel artifacts**,
so for solvency it prices almost nothing that happens.

Measured across all three:

| domain | read ms | solve ms | **read share of time** |
|---|---:|---:|---:|
| flood | 0.167 | 8.602 | **1.9%** |
| scheduling | 0.238 | 26.269 | **0.9%** |
| solvency | 0.061 | 0.002 | **96.1%** |

**`$/correct` captures 98% of flood's time, 99% of scheduling's, and 4% of
solvency's.** The omission is invisible where the kernel dominates and is the
entire cost where it does not — which is exactly the regime the programme's
thesis is about, since the argument is that symbolic reasoning is *cheap*.

If reasoning is cheap, then reading is what you are paying for, and a metric that
prices only reasoning will report a system as nearly free while missing 96% of
its work.

## Time and error are independent axes

Putting the three rows together, with error from the milestones and time from
the benchmark above:

| domain | decision | reader loss | read share of time |
|---|---|---:|---:|
| flood | widest path (P) | **0.500** | 1.9% |
| scheduling | bin-packing (NP-hard) | 0.000 | 0.9% |
| solvency | sum vs threshold | 0.000 | **96.1%** |

- **flood**: reading is 2% of the time and *all* of the error.
- **scheduling**: solving is 99% of the time and all of the error.
- **solvency**: reading is 96% of the time and there is no error.

So the two costs do not travel together:

> **Error concentrates where the signature is ambiguous. Time concentrates where
> the decision is hard.**

Both are properties the audit and the complexity of the decision predict
*separately*, before either is measured — flood's real ambiguity mass is 0.161
and the others' 0.000; scheduling's decision is NP-hard and the others' are not.
Neither predicts the other, and a system optimised on one will not be optimised
on the other.

## What should change

The milestone should report **reader time alongside kernel cost**, not because
reading is expensive in absolute terms — 0.06–0.24 ms is nothing — but because
its *share* is the diagnostic. A row showing 96% is telling you the kernel is
decorative, which is the same thing the widest-path result said about flood from
a different direction.

## What would refute this

- The timings are a single-machine measurement of Python, not of the algorithms;
  a compiled reader would shift every share. What survives that is the
  **ordering**, not the percentages: solvency's decision is O(members) against a
  reader that scans every sentence.
- Reader loss 0.000 for solvency is bounded at 1.50% by n=200, and at 0.75% by
  the separate 400-seed reader test. Not zero.
