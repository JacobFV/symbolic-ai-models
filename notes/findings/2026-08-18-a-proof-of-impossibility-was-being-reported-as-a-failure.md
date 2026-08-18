---
title: A proof of impossibility was being reported as a failure, and the budget field had never been read
date: 2026-08-18
status: provisional
tags: [kernel-abi, smt, planning, negative-result]
---

## Where this came from

Last wake-up ended with a prescription: for a kernel whose cost is not ordered
by size, *"the honest interface is a budget: give it a timeout, treat exhaustion
as an outcome rather than an error."* The obvious next question is whether the
substrate can express that, and the answer was mostly no.

**Prediction: `KernelRequest` carries no budget, and `refused` conflates "I
cannot" with "I ran out of time".**

Half wrong, and the wrong half is worse. `KernelRequest` *does* carry
`budget_usd` and `budget_ns` — and grep finds them read **nowhere in the
repository**. That is the third field in this substrate to be documented and
never exercised, after `add_facts`' delta contract (false) and
`cost_estimator` (absent). Three instances is a pattern, not a coincidence: a
field added while designing gets tested by the design discussion and never
again.

## The defect that matters more

`refused` was carrying three outcomes a planner must tell apart:

| what happened | what it meant | what to do |
|---|---|---|
| **unsat** | no assignment exists — *the solver proved it* | this is the answer |
| **unknown** | the budget ran out | retry with more budget |
| malformed / no toolchain | cannot ever | retrying is waste |

The first is the serious one. **`smt@1` returned UNSAT as a refusal**, so
`result.ok` was `False` when the kernel had *proved* infeasibility. A proof of
impossibility is often the most valuable thing a solver produces — it is exactly
what a covenant check or a safety argument wants — and the ABI filed it under
failure.

## The fix I did not make

The tempting repair is to widen `ok` to include unsat. **That would have
silently inverted two published results.** `feasible = result.ok` appears in
`symbolic_ai_generators/scheduling/ops.py` and `flood/ops.py`, and those feed the
flood capability price and the scheduling task. Under the current semantics
their reading is correct — unsat *does* mean infeasible — so widening `ok` would
have flipped `feasible` on precisely the cases the tasks are about.

So the distinction goes in a **new field beside the old one**: `outcome`, with
`ANSWERED` / `PROVED_IMPOSSIBLE` / `EXHAUSTED` / `REFUSED`, and derived
properties `proved_impossible`, `exhausted`, `retryable`, `conclusive`. `ok`
keeps its meaning exactly. A kernel that sets no outcome — the other seven —
classifies from `refused` as before.

`conclusive` is the one a planner should branch on when it wants to know whether
the *question is settled*; `ok` answers whether a positive answer was produced.
Those are different questions and the ABI could previously only ask one.

## The budget now works

`smt@1` reads `request.budget_ns` and sets z3's timeout. Measured on a
1,800-constraint system:

| budget | elapsed | outcome |
|---|---|---|
| 1 ms | 84 ms | **`exhausted`**, retryable, not conclusive |
| none | 111 ms | `answered`, conclusive |

Same system, two outcomes, and the difference is legible as a statement about
the budget rather than about the problem.

## Two mistakes of my own worth recording

**My "hard" test instance was not hard.** I encoded random 3-SAT as quantity
constraints to get a phase-transition instance, and this kernel projects to
*reals* — so `x >= 0, x <= 1, sum >= 1` is a trivial LP satisfied by setting
everything to 0.5. The test hung for unrelated reasons and taught nothing about
budgets. The working test uses a system that is merely *large*, which is all the
budget mechanism needs to demonstrate.

**Twice I killed my own process with a pattern that matched too much.**
`pkill -f smt_pt.py` also matched `smt_pt2.py`; `pkill -f "pytest tests/..."`
matched its own parent shell, because `-f` reads the full command line including
the pkill invocation. This is the same prefix trap `CLAUDE.md` documents for
`str.replace`, in a different costume, and it cost two runs.

## What would refute it

- `budget_usd` is still read nowhere. `budget_ns` is honoured by exactly one
  kernel. The pattern that produced this finding is not closed, it is one
  instance in.
- z3's `timeout` is a soft limit on its own main loop; the 1 ms budget took
  84 ms of wall clock, most of it constraint construction that no timeout
  covers. A planner budgeting in wall clock needs the projection cost too, and
  that is not measured here.
- `PROVED_IMPOSSIBLE` is set only by `smt@1`. ASP has the same distinction
  (unsatisfiable program versus exhausted search) and has not been updated.
