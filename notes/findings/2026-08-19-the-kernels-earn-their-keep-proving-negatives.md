---
title: The kernels earn their keep proving negatives
date: 2026-08-19
status: measured
arm: does-hardness-bite
---

## The question the last finding forced

Flood's decision turned out to be a widest path — in P, behind three kernels.
Solvency's is a sum against a threshold, openly polynomial. I asserted scheduling
was the genuinely hard one because feasibility is bin-packing with capability
constraints.

But **NP-hard in principle is not hard on this distribution**, and I had not
checked. If a polynomial procedure settles scheduling too, then no domain in the
suite supports "heterogeneous kernels are necessary" on its own instances.

## A two-sided polynomial procedure, neither half of which can be wrong

- `capacity_gate` proves **infeasible** when total demand exceeds total capacity.
- Greedy placement — longest job first onto the capable machine with most room —
  proves **feasible** when it succeeds, since it exhibits an assignment.

Both are one-sided sound, which is what makes the inconclusive band meaningful
rather than a measure of a weak heuristic. Tests assert both directions.

| shape | slack | gate proves | greedy proves | **inconclusive** | true feasible |
|---|---:|---:|---:|---:|---:|
| 6×3 | −0.02 | 1.00 | 0.00 | **0.00** | 0.00 |
| 6×3 | +0.00 | 0.27 | 0.00 | **0.73** | 0.00 |
| 6×3 | +0.02 | 0.00 | 0.00 | **1.00** | 0.02 |
| 6×3 | +0.15 | 0.00 | 0.27 | **0.73** | 0.28 |
| 6×3 | +0.40 | 0.00 | 0.50 | **0.50** | 0.58 |
| 20×5 | +0.02 | 0.00 | 0.02 | **0.98** | 0.32 |

**Scheduling genuinely exercises search.** At the default settings the
polynomial pair settles only **26.7%**; 45.6% averaged across the grid. My
prediction was 85–95% settled, and it was wrong in the better direction — the
suite does have one honest hard domain.

## What the search is actually buying

**Only 15.5% of the inconclusive band is feasible.**

At 6×3 slack 0.15: 0.28 of instances are feasible and greedy proves 0.27 of them.
Greedy exhibits an assignment for **nearly every instance that has one**. So what
no polynomial method provides is a **certificate that no assignment exists**.

> The kernels earn their keep proving **negatives**.

That unifies three results that had been sitting apart:

- ASP's UNSAT side is the expensive one, because a negative requires exhausting
  the space while a positive needs one witness.
- `capacity_gate` removes 87.7% of solver time on 50% of instances precisely by
  proving infeasibility cheaply where the arithmetic happens to settle it.
- The certificate work's monotone half made *infeasible* instances free in
  scheduling and *non-qualifying* vehicles free in flood — the same asymmetry.

## Where the suite now stands

| domain | decision | needs search? |
|---|---|---|
| flood | widest path | no — polynomial |
| solvency | sum vs threshold | no — polynomial |
| **scheduling** | bin-packing + capabilities | **yes, on the infeasible side** |

Two of three domains are decorative with respect to kernel necessity, and that is
worth saying plainly. But scheduling is not, and the finding is sharper than
"scheduling is NP-hard": it is hard **asymmetrically**, and the asymmetry says
what a solver is for.

## Where to sample if the question is what search buys

The inconclusive band is widest **just above slack 0** — 100% at 6×3/+0.02, 98%
at 20×5/+0.02 — where total capacity is sufficient but the capabilities do not
line up. That is the regime a generator should sample to study search, and it is
not the default.

## What would refute this

- A stronger polynomial heuristic collapsing the band. Greedy is deliberately
  simple; a better packer would prove more instances feasible, but it cannot
  prove any infeasible, so the 84.5% of the band that is infeasible is
  untouchable by that route.
- A polynomial *infeasibility* certificate stronger than the capacity bound —
  a capability-counting argument, say. That would shrink the band from the other
  side and is exactly the shape the scheduling certificate attempt failed to
  find.
