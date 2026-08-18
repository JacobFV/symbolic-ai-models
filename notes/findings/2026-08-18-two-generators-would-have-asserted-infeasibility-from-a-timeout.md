---
title: Two published tasks would have asserted "infeasible" from a solver timeout — the defect was latent until a budget existed to trigger it
date: 2026-08-18
status: provisional
tags: [soundness, generators, kernel-abi, latent-defect]
---

## The chain this closes

Three wake-ups ago `budget_ns` was found declared and read by nothing. Honouring
it in `smt@1` immediately exposed that `refused` conflated a *proof* of
impossibility with a *timeout*. Fixing that exposed the same conflation in
`asp@1`, where "no answer sets found" was reported as "unsatisfiable" regardless
of whether the search had finished.

This wake-up follows it one step further downstream, and that is where it gets
serious: **into the two tasks that produce published numbers.**

## What was wrong

`symbolic_ai_generators/scheduling/ops.py`:

```python
feasible = result.ok
claim = Claim("feasible_schedule", ...,
              polarity="positive" if feasible else "negative",
              modality="asserted", ...)
```

`result.ok` is False for *any* non-answer, so a solver that ran out of time
would have entered **"this schedule is NOT feasible", asserted, into the
world** — a fact the kernel had explicitly declined to establish.

`flood/ops.py` had the same shape with an extra wrinkle: `feasible = any(t["feasible"]
for t in tries)` over candidate routes. A single route whose search was cut
short is indistinguishable from a route the solver ruled out, so one unfinished
search could produce an asserted `can_serve: negative`.

**Neither could fire yet**, because nothing passed a budget. That is exactly the
shape of the ASP bug one layer up: latent, waiting for the first thing that
could interrupt a search — and the fix for that bug is what made this one
reachable.

## The fix, and the three-way logic it needs

Both now branch on `result.conclusive` rather than `result.ok`, and **emit no
claim at all** when nothing was established. Flood needs three cases, not two:

- a witness on **any** route settles it positive;
- a negative requires **every** route to have been settled against it;
- otherwise the vehicle is listed in `unsettled_vehicles` and gets no claim.

`missing can never become zero` has a sibling here: **unfinished can never
become false.**

Measured on a 14-job scheduling case:

| budget | outcome | settled | claims emitted |
|---|---|---|---|
| none | `proved_impossible` | True | 1 |
| 1 ns | `exhausted` | False | **0** |

## No published number moves

Every existing flood and scheduling test passes unchanged — 49 of them —
because with no budget the result is always conclusive and the behaviour is
byte-identical. The flood capability price and the scheduling task are
unaffected, which is the property that made this fix safe to make in place
rather than beside.

## A flaky test I nearly shipped

My first version asserted `outcome == "exhausted"` for a 1-nanosecond budget. It
passed standalone and failed under pytest, because **a budget the solver beats
is not exceeded** — clingo sometimes finishes inside a nanosecond window on a
warm cache. Correct behaviour, flaky assertion, and the same trap this repo hit
before with three timing-comparison tests asserting the sign of a difference
smaller than the noise.

The rewrite asserts the **invariant** instead: *a claim is emitted if and only
if the search settled*, and *no unsettled vehicle carries a claim*. It holds
whichever way the race resolves, and it is the property that was actually
broken. Stress-run three times, 49 passed each time.

## What would refute it

- The budget is passed as a node parameter and nothing in the flow builders
  sets it yet, so the guarded path is exercised only by tests. A planner that
  actually budgets these tasks is the real test and does not exist.
- `_check_loads` prices itself from the kernels it calls; an exhausted call
  still costs, so a budgeted run pays for searches that established nothing.
  Whether that cost should count against `$/solved-episode` is unresolved —
  it is real money spent on no answer, which argues yes, and it is not a
  capability, which argues the denominator is wrong.
- Nothing yet stops a *new* node from reading `.ok` and manufacturing a claim
  the same way. The kernel conformance table guards kernels; there is no
  equivalent for flow nodes.
