---
title: The expensive negatives are the easy negatives
date: 2026-08-19
status: measured
arm: hard-regime
---

## Correcting the previous finding's headline, and my own constant

The last finding concluded that *the kernels earn their keep proving negatives*,
on the strength of a polynomial procedure settling only 26.7% of scheduling at
the default. I added a `HARD_REGIME` at 6 jobs / slack +0.02, the cell where the
band was 100% inconclusive.

**That was the wrong measurement.** Clingo settles that cell in **0.6 ms** — it
is the *cheapest* in the grid. The inconclusive band measured the weakness of my
greedy heuristic, not the hardness of the instance. At 6 jobs the space is
3⁶ = 729 and nothing there is hard for a real solver.

## Where the solver is actually expensive

| nj × nm | slack | mean ms | max ms |
|---|---:|---:|---:|
| 6×3 | +0.02 | **0.6** | 0.8 |
| 20×3 | −0.02 | **198.6** | 1200.4 |
| 30×4 | −0.05 | **1047.5** | — |
| 40×5 | −0.05 | **1502.5** | 3004.5 |
| 20×3 | +0.02 | 1.2 | 1.3 |

Cost needs **size** and sits at **negative** slack. But that is the whole
problem:

| nj | slack | mean ms | **gate fires** | ms when gate silent |
|---|---:|---:|---:|---:|
| 20 | −0.02 | 198.6 | **6/6** | — |
| 30 | −0.05 | 1047.5 | **6/6** | — |
| 30 | **0.00** | 490.9 | 4/6 | **168.7** |
| 20 | **0.00** | 19.6 | 3/6 | **15.7** |
| 20 | +0.02 | 1.2 | 0/6 | 1.2 |

**Every expensive negative-slack cell is settled 6/6 by the capacity gate** — one
pass of O(n) arithmetic. The regions where clingo is slowest are exactly the
regions where nobody needs to run it.

So the previous headline needs refining. The kernels *are* spending their time on
negatives, but **the expensive negatives are the easy ones.** What survives the
gate is cheap for the solver, and what is expensive for the solver is free for the
gate.

## The one cell where the solver is both necessary and expensive

**Slack ≈ 0** — exact fit. The gate cannot fire (demand does not *exceed*
capacity), and the packing is maximally tight: 15.7 ms at 20 jobs on the
gate-silent instances, 168.7 ms at 30.

And that cell has a cost of its own: it is where `feasible_by_search` degenerates,
because the capacity bound is tight and prunes nothing — **0.027 s per case at 20
jobs, 1.60 s at 30**. So:

> The only regime where the solver is both necessary and expensive is the one
> where establishing ground truth is itself expensive.

That is a real constraint on the benchmark, not a defect to fix. `HARD_REGIME` is
now 20 jobs / 3 machines / slack 0.0 — the intersection where the gate is silent
on half the instances, the solver is non-trivial, and the oracle stays affordable.
Raising `n_jobs` raises solver cost and raises the oracle's cost faster.

## What still stands

Scheduling remains the only domain in the suite whose decision is not polynomial
— flood is a widest path, solvency a sum against a threshold. That is unchanged.
What is corrected is *where* in scheduling the difficulty lives and *how much* of
it a one-line arithmetic check removes.

## The pattern in these three turns

Three corrections, each from building on the previous claim rather than polishing
it: flood's kernels were overkill for a polynomial decision; scheduling's
inconclusive band was heuristic weakness, not instance hardness; and the
expensive cells are gate-settleable. **Each was found by asking what the
measurement actually measured**, which is the same question that has produced
almost every correction on this thread.
