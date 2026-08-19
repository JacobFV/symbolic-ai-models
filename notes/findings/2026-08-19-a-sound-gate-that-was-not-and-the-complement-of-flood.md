---
title: A sound gate that was not, and the complement of flood
date: 2026-08-19
status: measured
arm: hard-regime-milestone
---

## Pushing the benchmark into the hard regime broke a component

Every scheduling pipeline number in this repo came from the easy default, where
clingo answers in 0.6 ms. Running the milestone at `HARD_REGIME` (20 jobs, slack
0.0) produced a ceiling of **0.867** — the kernel disagreeing with ground truth on
4 of 30 cases, with no budget exhaustion to explain it.

Adjudicating took three steps, and the first two were wrong guesses:

1. **`SCALE=100` rounding?** No — total demand and capacity matched to the
   integer.
2. **The pruned oracle's `1e-9` tolerance?** No — an exact integer re-implementation
   agreed with the oracle on all four: **feasible**.
3. The kernel itself, called directly, also said **feasible**.

Oracle right, kernel right, answer wrong. The culprit was the thing in between.

## The bug

`capacity_gate` — documented as *"provably sufficient"*, and cited in this repo as
removing **87.7% of solver time at zero accuracy cost** — summed hours as
**floats** and compared `demand > capacity`.

At `HARD_REGIME` total demand equals total capacity *by construction*. Summation
order made demand exceed capacity by **1.4e-14**:

> seed 8: demand `77.04`, capacity `77.03999999999999`

**The gate refused a schedule that provably exists, on 4 of 30 instances.**

A one-sided check that is sometimes wrong is worse than no check, because
everything downstream trusts it. And the 87.7% figure was measured far from the
boundary, where a comfortable margin hides the defect entirely — the claim was
true where it was measured and the component was broken anyway.

**Fixed** by summing in integer centihours, the same units `build_program` uses,
so the gate and the ASP encoding now agree on what the numbers are. Two tests:
the gate never refuses a feasible schedule at exact fit, and it still fires 20/20
below the boundary.

## The corrected milestone, and the complement of flood

| system | claim R | task acc | $/correct | ms/case |
|---|---:|---:|---:|---:|
| oracle world (ceiling) | 1.000 | **1.000** | 9.49e-08 | 17.5 |
| signature reader, as published | 1.000 | 1.000 | 8.76e-08 | 15.9 |
| signature reader, **interleaved** | 1.000 | **1.000** | 8.58e-08 | 15.6 |

The ceiling rose 0.867 → 1.000 with the gate fixed, the gate now settles 2/30
rather than 8/30, and solve time roughly doubled because the wrongly-refused
cases actually run.

**Reader loss is 0.000, and unchanged by interleaving.** Scheduling audits at
0.000 ambiguity mass — `job_`/`machine_` prefixes fix the predicate — so
destroying arrangement costs nothing, exactly as the structure-dependence law
predicts.

Set against flood's honest milestone, measured the same way:

| | flood | scheduling (hard regime) |
|---|---|---|
| decision | widest path (**P**) | bin-packing (**NP-hard**) |
| reader loss | **0.500** | **0.000** |
| $/correct | 3.69e-08 | **9.49e-08** |
| where the cost is | **reading** | **solving** |

**One domain where reading is the whole cost, one where solving is** — and the
contrast is the point. Either number alone invites the wrong conclusion about
where effort belongs.

## What this says about the method

The bug was invisible for as long as the benchmark stayed in the comfortable
regime. It took **constructing the hard regime and running the pipeline there**
to surface it, and the surfacing was accidental — I was measuring cost, not
auditing the gate.

That is an argument for pushing benchmarks to their boundary as a matter of
course: **the margin that makes a component look sound is the same margin that
hides its unsoundness.**

## What would refute this

- The 87.7% claim needs re-reading, not retracting: it was measured across a
  slack sweep dominated by comfortable margins, where the gate's verdicts were
  correct. The gate's *value* stands; its *soundness* did not, and now does.
- `HARD_REGIME` sits at exact fit deliberately, which is where floating point is
  least forgiving. Any other component comparing summed quantities there deserves
  the same look — `feasible_by_search`'s own `1e-9` tolerance was cleared here,
  but only for these instances.
