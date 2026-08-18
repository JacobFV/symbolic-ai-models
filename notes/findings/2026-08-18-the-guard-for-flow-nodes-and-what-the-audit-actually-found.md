---
title: The whole repo has exactly two places a node could fabricate a fact, and both are now gated — plus a guard that fires on the pre-fix code
date: 2026-08-18
status: provisional
tags: [soundness, flow, structural-test, kernel-abi]
---

## The question

Last wake-up fixed two generators that would have asserted "infeasible" from a
solver timeout, and closed by naming the gap: *the conformance table guards
kernels; nothing stops a new flow node from reading `.ok` and manufacturing a
claim the same way.*

**Prediction before auditing: 1–3 more sites where a kernel result drives a
claim or a decision without checking conclusiveness.**

## What the audit found

Exactly **two** more, and neither was a fabrication:

| site | what it was |
|---|---|
| `symbolic_ai_kernels/flow_ops.py` `_kernel_run` | the generic node every task uses. **Safe by construction** — it passes `result.claims` through, and a kernel that settles nothing returns none |
| `symbolic_ai_core/cli.py` `sched_decide` | a decision function feeding the margin profiler, returning `.ok` directly |

So the prediction was right on count and wrong on character: I expected more
fabrication and found none. The two real defects were the two I had already
fixed by hand, which is a more reassuring answer than the one I went looking
for.

## The two gaps that were real

**`_kernel_run` could not budget anything.** `budget_ns` and `budget_usd` were
never passed from node params into the `KernelRequest`, so no task using the
generic node could bound a kernel call at all — the field honoured by two
kernels was unreachable from the layer that runs them.

**Its report omitted the outcome.** A downstream node could only string-match
`refused`, which is precisely how the two generators came to read a timeout as
infeasibility. It now carries `outcome` and `settled`, so a node author has the
field to branch on before turning an absent positive into a negative.

**`sched_decide` now raises** rather than returning `None` for an unsettled
search. The margin profiler binary-searches for a decision flip, and `None`
reads as falsy — a corrupted margin instead of a crash. Nothing passes a budget
there today, so the guard is for the day something does.

## The structural guard

`tests/test_no_claim_from_an_unsettled_result.py` walks the AST of every module
in five packages and flags any function that **both** judges a kernel result
(`.ok` / `.refused`) **and** constructs a claim with a `polarity`, unless it
also mentions settlement.

It is narrow on purpose. A node that emits only what the kernel returned cannot
fabricate anything, so the check targets the single way a node can invent a
fact: reading an *absence of a positive answer* as a *negative one*.

Two properties keep it honest:

- **It asserts it still sees its own targets.** `test_the_check_finds_the_functions_it_is_meant_to_police`
  fails if `_check_loads` and `_solve` drop out of scope, because a structural
  test that matches nothing is not a guard, it is a comment.
- **It is checked against the bug it was written for.** The pre-fix shape is
  reconstructed inline and asserted to be caught — otherwise the guard's value
  rests on my memory of a defect rather than on the defect.

## What would refute it

- AST matching is shallow: `polarity` passed through a variable, or a claim
  built in a helper the function calls, both escape it. It catches the shape
  that occurred twice, not the class.
- The guard cannot see a node that decides something *other* than a claim from
  an unsettled result — a router that treats exhaustion as "cheap branch
  sufficed", say. `sched_decide` was that shape and was found by grep, not by
  the guard.
- Five packages are scanned by name. A sixth added later is silently
  unprotected, which is the same "add a thing, forget the contract" mechanism
  this whole line of work has been chasing.
