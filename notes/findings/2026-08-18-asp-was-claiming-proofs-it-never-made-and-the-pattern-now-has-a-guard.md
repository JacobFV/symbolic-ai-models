---
title: ASP was reporting "unsatisfiable" for searches it merely ran out of time on — and the pattern behind three such defects now has a guard
date: 2026-08-18
status: provisional
tags: [kernel-abi, asp, soundness, conformance, negative-result]
---

## The pattern, which is the real subject

Three ABI contracts have now been found documented and never exercised:

| contract | state when found |
|---|---|
| `add_facts` delta-proportional cost | **false** by three orders of magnitude |
| `cost_estimator` | **absent** from all eight kernels |
| `budget_ns` / `budget_usd` | **read nowhere in the repository** |

Three is a pattern rather than three accidents. The mechanism is specific: a
field gets exercised thoroughly by the design discussion that invents it, and
then never again, because nothing downstream fails when it is ignored. Fixing a
fourth instance would have been the fourth instance.

## The soundness bug this turned up

`asp@1` reported "unsatisfiable: no completion of this world satisfies the
constraints" **whenever it found no answer sets** — including when the search
had been cut short. Once `budget_ns` was honoured, that became a live soundness
defect: a solver that ran out of time would report a **proof of impossibility it
had never made.**

clingo's `result.exhausted` is the only thing separating the two, and nothing
was reading it for this purpose. Measured on pigeonhole (n+1 pigeons, n holes —
unsatisfiable, and hard as n grows):

| n | budget | elapsed | outcome |
|---|---|---|---|
| 6 | none | 11.2 ms | **`proved_impossible`**, conclusive |
| 6 | 0.5 s | 3.0 ms | `proved_impossible` — a budget that does not bite must not weaken a real conclusion |
| 13 | 0.5 s | 502.5 ms | **`exhausted`**, retryable, **not** conclusive |

Before the fix the last row read "unsatisfiable". Same program family, same
kernel; the difference between a theorem and a timeout was invisible.

This is exactly the silent degradation the kernel-stack decision note forbids,
and it did not arrive with the budget — it was latent, waiting for anything that
could interrupt a search.

## The guard

`tests/test_kernel_conformance.py` enumerates every registered kernel against an
explicit table and **fails when a kernel is added without declaring what it does
about each contract**. Three properties make it a guard rather than
documentation:

- **No silent default.** A kernel either honours `budget_ns` or declines it with
  a *reason*, never a bare `False`. "No, because it terminates in time
  proportional to its input with no search" and "nobody has done it yet" are
  different states, and only one is a decision. `lean@1` and `egraph@1` both
  search, both take no budget, and are marked `NOT YET IMPLEMENTED -- this is a
  known gap, not a decision`.
- **The table is checked against the source.** Declaring conformance is not
  conforming, so the test reads each kernel's source and fails if the claim and
  the code disagree.
- **The gap list is itself asserted.** `test_the_gaps_are_listed_rather_than_forgotten`
  fails the day the list is emptied — by implementation *or* by quietly deleting
  an entry.

## Predictions, and what they were

Before surveying: **1 of 8 kernels honours `budget_ns`, 1 classifies outcomes,
3 have external toolchains.** First two exactly right. The third was wrong:
only **two** are external, because `lean@1` is a from-scratch native
typechecker with no dependencies — I had been carrying "Lean" as an external
toolchain in my head for days.

## What would refute it

- The conformance table is hand-written. It catches a *new* kernel that
  declares nothing, and a table entry that contradicts its source, but not a
  contract nobody thought to add a column for. The next such field will be
  found the same way the first three were.
- `budget_usd` is still read by nothing. It is not in the table, which means
  the guard as built does not cover it — an honest gap in the guard itself,
  named here rather than in a future finding.
- The ASP budget uses an asynchronous solve handle rather than clingo's
  `--time-limit`, because that option takes whole seconds and floors a
  sub-second budget to 0, which means *no limit* — the one wrong value that
  silently ignores the budget entirely. Sub-second budgets are now real, but
  grounding happens before the handle exists and is not covered by the budget.
