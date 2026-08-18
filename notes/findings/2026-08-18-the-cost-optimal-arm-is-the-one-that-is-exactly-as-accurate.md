---
title: Lossless routing saved 4.5%, and the arm that was 3.4× cheaper came out 1.7× worse on $ per solved episode above floor
date: 2026-08-18
author: lead
status: provisional
tags: [routing, cost, kernels, flow, refuted-prediction]
---

## What was built

Router and chooser nodes (`flow.route@1`, `flow.choose@1`), and an **escalation**
policy for the flood task: run the cheap arm when it is *provably* sufficient,
run the three solvers otherwise. Two gates, both arithmetic over facts already on
the table:

* the demand site is not reachable from the depot, so no vehicle can serve it
  whatever the loads are;
* every capacity-qualifying vehicle's laden mass clears the *lightest* posted
  limit, so no bridge can bind and the answer is capacity alone.

The mechanism is the flow layer's existing absence propagation: the router emits
a present artifact on the branch it selects and an absent one carrying the reason
on the branches it does not, so every downstream node is skipped **with that
reason in the trace**. Nothing new in the evaluator, and the decision is auditable
rather than buried in a predicate.

## Prediction, before the numbers

Stated in advance: routing is lossless by construction (accuracy exactly 1.000);
it saves roughly 10%; and the cheap arm falls *below* the 0.440 floor, so its
cost advantage buys nothing.

**Two of the three were wrong, and the first was wrong because of a bug in my own
code** — which is the part worth recording.

## The bug the prediction caught

The routed arm measured **0.870, with 39 disagreements in 300**, on a path whose
docstring called itself provably lossless. The cheap op read reachability from
`params.get("reachable", True)`, the node carried no params, and so it answered
"capacity clears it" on every *unreachable* world.

The fix is the interesting part: reachability is now read from the world the node
was handed, not from a parameter. The gate binds that input to the
**post-datalog** world, so the `reach` claims are already present — asking for
them is both correct and free. A cheap arm that recomputed the closure would not
have been cheap.

After the fix: **0 disagreements in 300.**

## Measured, 300 seeds, floor 0.440

| arm | acc | lift | $/episode | **$/solved above floor** |
|---|---|---|---|---|
| baseline (always all three) | 1.000 | 0.560 | 1.213e-08 | 2.166e-08 |
| **routed (lossless escalation)** | **1.000** | **0.560** | **1.158e-08** | **2.068e-08** |
| cheap only (datalog + capacity) | 0.537 | 0.097 | 3.518e-09 | 3.639e-08 |
| no-SMT ablation | 0.537 | 0.097 | 1.069e-08 | 1.106e-07 |

The gate fires on 46/300 = 15.3%.

## The three things this says

**1. The cost-optimal arm is the one that is exactly as accurate as the most
expensive one.** That is the measured form of the argument
`symbolic_ai_core/cost.py` was written after: *cheap-and-incapable is not a point
on the cost curve.* The cheap arm is **3.4× cheaper** and **1.7× worse** on the
metric that matters, because its cost fell by 3.4× while its lift fell by 5.8×.
A cost saving that costs capability is a loss, however large the saving, and the
denominator is what makes that visible.

**2. Lossless routing saved 4.5%, not the 10% predicted.** The gate fires on
15.3% of cases but only ASP and SMT sit downstream of it — datalog and the
reconcile step run unconditionally on every case. **Routing pays in proportion to
what is downstream of the gate**, and pushing the gate earlier is not free,
because the reachability condition *needs* datalog's output.

> **Corrected, later the same day: 13.1%, not 4.5%.** The missing two thirds was
> the gate's own implementation. Its policy called `WorldSnapshot.from_dict`,
> rebuilding every Entity and Claim so that two `if` statements could read six
> fields — which made the router the **third most expensive node in the routed
> pipeline at 10.4% of its cost, above datalog itself**, and only 6.5× cheaper
> than the solvers it decides on. Reading the serialised world directly instead
> takes it to 1.3% and 56.5×, and lossless routing then saves **13.1%** at
> accuracy still 1.000. `$/solved above floor` goes 2.469e-08 → 2.145e-08.
>
> So the principle needs its second half, and I stated the first and then
> violated it in the same file: **routing pays in proportion to what is
> downstream of the gate, and in inverse proportion to what the gate itself
> costs.** The two gates are asserted to decide identically on every case, so the
> saving is a pure speed change.

**3. The cheap arm and the no-SMT ablation land on identical accuracy (0.537)
at 3× different cost.** Two unrelated ways of dropping the load check agreeing
exactly is a reassuring cross-check that they are doing the same thing; the
ablation is then strictly dominated, which is what an ablation should be — it is
a diagnostic, not a deployable arm.

## What would have refuted it

- **The gate never firing**, which would make losslessness true for the wrong
  reason. It fires 15.3%, asserted by test.
- **The router costing more than it saves.** On a *cheap* branch it buys
  essentially nothing, which is the guard against "route everything".
  **Correction, added after the fact:** the first version of that check asserted
  the *sign* of the difference, from a measured −4e-12 USD. That assertion
  passed inside its own file and failed 8 times out of 8 when run alone —
  process warm-up is far larger than the effect. Asserting the sign of a
  difference smaller than the measurement noise is not a test. The check now
  asserts the robust property instead: the gate is itself a priced node, and the
  saving is bounded by the cost of the identity op it skipped. The *direction*
  of the effect on a trivially cheap branch is not measurable here and this note
  should not be read as having measured it.
- **The floor moving.** 0.440 is the strongest of the seven floors from the
  earlier flood finding, and every arm here is scored against the same one.

## What this does not establish

Nothing is *learned*. This is a hand-written policy over two provable
conditions, which is the right first step — a heuristic gate trades accuracy for
cost and cannot be evaluated without a utility model, and now there is one:
`$/solved above floor` ranks the four arms and puts the lossless router first.
The next arm is a gate that is allowed to be wrong, scored on that ranking.
