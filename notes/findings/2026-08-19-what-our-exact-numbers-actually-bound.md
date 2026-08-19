---
title: What our exact numbers actually bound
date: 2026-08-19
status: measured
arm: exactness-audit
---

## The method failure, not the bug

The solvency reader was reported at **1.000 over 60 seeds** and was wrong on
2.25% of cases. That is not an isolated slip. By the **rule of three**, zero
failures in `N` cases bounds the true rate at roughly `3/N`, so:

| sample | excludes error rates above |
|---:|---:|
| 34 | **8.8%** |
| 40 | 7.5% |
| 95 | 3.2% |
| 400 | **0.75%** |

Several load-bearing findings here are asserted as exact on samples of 34–95.
**Both "exact over 34" and "exact over 400" read as 1.000 on the page.**

## Re-run at 400 seeds

| claim | orig N | bounded | now N | failures | now |
|---|---:|---:|---:|---:|---:|
| **flood signature+content, interleaved** | 34 | 8.8% | 252 | **3** | **1.19% measured** |
| flood insensitivity certificate | 95 | 3.2% | 252 | 0 | 1.19% bound |
| scheduling reader, interleaved | 40 | 7.5% | 400 | 0 | 0.75% bound |

**One of three broke.** The solvency reader was not unusual.

## What breaks, and why it is the failure I predicted at declaration time

`signature+content` is **0.988**, not 1.000, on the interleaved surface at V=4.
All three failures share one shape — **two** lone-region sentences that reach no
declared anchor in the same case:

> *"region_1 **went under** overnight and cannot be entered at all."* — flooding
> *"Vehicles are **dispatched** from region_0."* — depot

Both were named as anchor misses when the vocabulary was declared, before the
variants were read. With two unresolved regions and `depot` still open,
elimination assigns depot to whichever comes first — and interleaving randomises
that order, so it picks a flooded region as the depot.

So this is not a new defect. It is the **known coverage gap**, occurring when two
dodging variants coincide, at a rate of about 1.2% — invisible in the 34
non-empty cases it was measured on.

**The vocabulary will not be patched.** Adding *went under* and *dispatched*
would recover exactly these cases and demonstrate nothing; it is memorising the
generator one variant later, and the adversarial-variant finding already priced
that floor.

## What this corrects

[[2026-08-19-the-empty-cell-is-filled-by-five-words-of-flooding]] reports 1.000
in all four cells. The interleaved V=4 cell is **0.988 (3/252)**. The finding's
structure survives — the arm is still the only one invariant to both axes, and
the ablation showing content is load-bearing is unaffected — but the headline
number was measured on a sample that could not distinguish 1.000 from 0.99.

## The detectable part

In all three failures the reader **knew it was guessing**: `needs` was resolved by
adjacency, `depot` was open, and two unresolved regions remained. That is exactly
the condition under which this repo's own answer is to emit the ambiguity rather
than collapse it.

A refusing variant would convert 3 silent errors into 3 refusals at soundness
1.000, and the machinery exists. Named as the next step rather than built here,
because the finding worth having this turn is the **bound**, not another arm.

## The rule going forward

**State the bound, not the number.** A claim of exactness should carry the sample
that supports it, because `3/N` is what the reader of the note actually needs.
Where a number is load-bearing, 400 seeds costs seconds and buys an order of
magnitude in the bound.

## What would refute this

- The three failing seeds are 64, 83 and 92 out of 400; a different seed range
  would give a different rate, and 3/252 has a wide interval of its own —
  roughly 0.3% to 3.5%. The point is that it is **not zero**, not that it is
  precisely 1.19%.
- The certificate's 0/252 now bounds it at 1.19%, better than the 3.2% it had.
  Its necessity half remains measured rather than proved.
