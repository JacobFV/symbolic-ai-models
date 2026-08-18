---
title: Timing only the part you meant to measure, while the setup you did not mean to measure runs inside the same call
date: 2026-08-18
tags: [cost, measurement, mechanism]
---

## The mistake

`DatalogKernel.run_delta` is the incremental path: a `WorldDelta` arrives and it
computes only the delta's consequences. It was written as

```python
known = evaluate(program, facts)                       # the whole model
(added, full), ns = timed(lambda: add_facts_report(program, known, new_facts))
return ... cost=KernelCost(cpu_ns=ns, usd=price_cpu_ns(ns))
```

The `timed()` call wraps the incremental step. The full evaluation happens on the
line above it, inside the same method, and is not timed.

## What it cost

On a 120-node chain with a transitive-closure rule: **the method reported 5.3 ms
and actually did 213.7 ms of work.** A 40× understatement, and it understated the
number that the whole cost argument runs on.

Worse, it understated it in exactly the direction that flatters the design. The
claim being made about this kernel is *"the cost is proportional to what changed
rather than to the size of the world"*, and the measurement was constructed —
accidentally, but constructed — to report that claim rather than to test it. Had
this shipped, `$ per solved episode above floor` for anything using the
incremental path would have been wrong by the same factor, and nothing
downstream could have noticed.

## The mechanism, which is the reusable half

> **A timer placed around the operation you are interested in does not measure
> the call. It measures the operation.** If the call also does setup, the setup
> is free in the report and real on the clock.

This is the same shape as two mistakes already in this repo's ledger:

- a **floor fitted with the model's own features**, which measures what you
  meant to measure rather than what the baseline actually has;
- a **throughput number read as a capability price**, which measures the
  operations you happen to run rather than the system that would be useful.

All three are cases of the instrument being aimed at the intended quantity
rather than at the real one, and none of them fails loudly. The suite was green
throughout.

## The guard

**Time the boundary, not the interesting part.** Whatever a caller invokes is
what a caller pays for, so the timer goes around the whole public method — and
if that makes a number look bad, the fix is to move the expensive setup *out of
the call* (here: hand the base model in as a parameter, which is what an
incremental kernel's caller should have been doing anyway), not to move the
timer.

Concretely, in this repo:

- a kernel's `KernelCost` covers everything between entering and leaving its
  public method;
- when a method can avoid work if the caller supplies state, both paths are
  measured and a diagnostic says which one ran — `base_recomputed: true|false`
  here, so a reader of a cost table can tell a cached call from a cold one;
- `tests/test_datalog_kernel.py::test_run_delta_prices_the_base_evaluation_it_performs`
  asserts the cold path costs at least 5× the warm one, which is a property no
  amount of correct output would have revealed.

## The same mechanism, one week later, in a test

`test_routing_a_trivially_cheap_branch_is_a_NET_LOSS` asserted `usd_saved <= 0`
from a measured **−4e-12 USD**. It passed inside its own file and failed **8
times out of 8** when run alone, because process warm-up moves the first
`evaluate` call by far more than 4 picodollars.

The claim was true in the sense that mattered — routing something cheaper than
the gate cannot pay — and untestable in the form it was written. **Asserting the
sign of a difference smaller than the measurement noise is not a test; it is a
coin flip with a docstring.** It also *hid* rather than revealed, because passing
in-file made it look like a property that held.

The guard: when a test asserts a comparison of two measurements, first ask
whether the effect is larger than the run-to-run variation of the instrument.
If it is not, assert a **magnitude bound** or a **structural** property instead —
here, that the router is a priced node and the saving is bounded by the cost of
what it skipped. Both are true regardless of warm-up.

And run the test alone at least once. A timing assertion that only holds in the
company of other tests is one that will fail in CI on a quiet machine.
