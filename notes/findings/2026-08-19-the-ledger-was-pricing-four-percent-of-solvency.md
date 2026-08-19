---
title: The ledger was pricing 4% of solvency
date: 2026-08-19
status: measured
arm: reader-in-the-ledger
---

## A stated rule, violated in the module written for it

`CLAUDE.md`:

> Cost is charged to the **system**: if a reasoner only works because something
> upstream produced a graph, that upstream component is in the ledger whether or
> not it exists yet.

`symbolic_ai_core.cost.System`, in its own docstring:

> The whole reason this type exists is that `sum` is not optional.

And every milestone in this repo prices **kernel artifacts only**. Reading is
1.9% of flood's wall clock, 0.9% of scheduling's, and **96.1% of solvency's** —
so the ledger has been pricing 4% of what solvency runs.

## Charging both components

Each domain's system built from a reader and a kernel, both priced from measured
throughput:

| domain | tok/answer | read tok/s | kernel tok/s | $/solved kernel only | $/solved **system** | × |
|---|---:|---:|---:|---:|---:|---:|
| flood | 362 | 1.79e6 | 4.3e4 | 8.480e-08 | 8.684e-08 | **1.02×** |
| scheduling | 325 | 1.25e6 | 1.3e4 | 4.048e-07 | 4.089e-07 | **1.01×** |
| **solvency** | 150 | 2.64e6 | 8.5e7 | **2.161e-11** | **7.218e-10** | **33.4×** |

**Flood and scheduling survive.** Their published cost figures are 1–2% low,
which is inside the noise of a single-machine Python timing and does not change
any conclusion drawn from them.

**Solvency's was 33× too low**, because its kernel is a sum against a threshold
and the ledger was charging for that alone.

**The ordering is unchanged** — solvency < flood < scheduling, both ways — so
cross-domain comparisons in this repo are *incomplete* rather than *wrong*.

## Why it lasted

Two of three domains barely move. That is the whole explanation, and it is worth
stating as a rule rather than an anecdote:

> **A metric is not validated by the cases where its missing term is
> negligible.**

The case where it is not negligible is the one this programme's thesis is about.
The argument is that symbolic reasoning is *cheap*; where that is true, reading
is what you are paying for, and a ledger that prices only reasoning will report
the system as nearly free while missing almost all of its work.

## What changed

The measurement is in `scripts/reader_in_the_ledger.py`, and `cost.py`'s module
docstring now carries the rule and the three numbers — that is where an author
adding a new domain will look, and the omission was never a bug in this module
but in every caller of it.

`System` still cannot detect the omission: `sum` is not optional over the
components it is *given*, and nothing forces a caller to hand it all of them.
That is a real limit and it is now written down rather than assumed away.

## What would refute this

- Single-machine Python timings. What survives is the **ordering and the
  magnitude of the gap**, not the percentages: solvency's decision is
  O(members) against a reader that scans every sentence, so the ratio is
  structural.
- The reader here is a hand-written signature reader. A learned reader would
  change every share, and probably in the direction that makes this worse.
