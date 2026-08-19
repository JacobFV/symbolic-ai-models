---
title: The cheap kernel is not an escalation tier, it is a discount on the expensive one
date: 2026-08-19
status: measured
arm: routing-traces / where-the-gate-fires
domains: flood, scheduling
---

## The question

Directive 13 asks for execution traces before any routing policy, and names the
rule to derive against: escalate when `p·L > c₁ − c₀`, for cheap cost `c₀`,
expensive cost `c₁`, cheap-arm error rate `p` and the loss `L` of a wrong answer.

That framing assumes a **tier structure** — the cheap path is a discount you buy
by accepting error, and the router's job is deciding when the discount is worth
it. Both domains say the structure is wrong, in the same way, for two different
reasons.

## Flood: dropping the cheap kernel made the flow more expensive

Four strategies over 40 cases, each a real configuration of the flow:

| strategy | success | success \| non-empty | $/case | ms | $ vs full |
|---|---:|---:|---:|---:|---:|
| full | **1.000** | **1.000** | 7.69e-09 | 7.64 | 1.00x |
| no ASP search | 0.925 | 0.864 | 6.42e-09 | 6.66 | 0.83x |
| **no datalog** | 0.675 | 0.818 | **1.37e-08** | 12.06 | **1.78x** |
| no SMT | 0.450 | 0.500 | 6.38e-09 | 7.33 | 0.83x |

Removing datalog reachability made the flow **78% more expensive and less
accurate**. Its escalation threshold is *negative* (−3.30e-08 USD): there is no
loss `L`, however small, at which skipping it pays. It is not a tier, it is
strictly dominated to skip. The cheap kernel shrinks what the expensive search
has to explore by more than it costs to run.

For the two arms that *are* genuinely cheaper, the derived thresholds are
2.63e-09 (no SMT) and 9.37e-09 (no ASP search) USD. A wrong answer would have to
cost less than about a hundredth of a microdollar for either to be worth taking.
Per-case cost spread is p50 1.08x, max 2.14x, with 2.5% of cases above 2x — so no
hidden regime where the aggregate conceals an opportunity. **Always take the full
flow.**

## Scheduling: the sound gate is aimed at the cost, 1.75x better than its rate

`capacity_gate` is **sound and one-sided** — total demand above total capacity is
infeasible whatever the assignment; the converse proves nothing. So escalating
past it costs *no accuracy at all* and the question is purely economic. The naive
expectation is that it saves in proportion to how often it fires.

120 instances, slack swept across the feasibility boundary, clingo budget-capped
at 3s:

| population | n | mean s | total s | share of cost |
|---|---:|---:|---:|---:|
| gate FIRES (solver skipped) | 60 | 0.378 | 22.68 | **87.7%** |
| gate passes (solver runs) | 60 | 0.053 | 3.18 | 12.3% |

**87.7% of solver time removed on 50.0% of instances.** Where the cost sits:

| slack | total s | share | gate fires |
|---:|---:|---:|---:|
| −0.20 | 0.04 | 0.2% | 20/20 |
| −0.08 | 6.39 | 24.7% | 20/20 |
| **−0.03** | **16.25** | **62.9%** | **20/20** |
| +0.03 | 0.04 | 0.2% | 0/20 |
| +0.08 | 3.10 | 12.0% | 0/20 |
| +0.20 | 0.04 | 0.1% | 0/20 |

I predicted the opposite, at 0.5 confidence, and wrote down why: the gate can
only fire below the boundary, hardness in packing concentrates *at* the boundary,
so a sound cheap check should be **anti-correlated** with cost and buy less than
its fire rate. It buys 1.75x more.

### Why, and this is the part that generalises

Cost concentrates at **barely infeasible** (−0.03), not at deep infeasibility and
not on the feasible side. Both easy regions are easy for the same reason and the
hard one is hard for a specific one:

- At slack −0.20 capacity is far below demand, machines fill immediately,
  per-machine `#sum` propagation hits contradictions within a few decisions, and
  clause learning cuts the space fast. 0.04s pooled.
- On the feasible side a witness exists and is found early. Search stops at the
  first model.
- At slack −0.03 **no single machine's constraint is violated by any partial
  assignment**. The contradiction only exists in the sum *across* machines, and
  clingo's propagators are per-constraint. So it must go deep before failing.

The gate computes that cross-machine sum in O(n) arithmetic. **It performs
exactly the inference the expensive kernel cannot express locally, and its value
concentrates precisely where the expensive kernel's local propagation is
weakest.**

## What this says about routing

Both domains, two different mechanisms, one conclusion: **the cheap symbolic
kernel is not a lossy tier to route around. It is a discount on the expensive
one.** In flood it shrinks the search space by more than it costs; in scheduling
it supplies a globally-scoped inference the solver has no local form of.

So the escalation rule `p·L > c₁ − c₀` is not the right model here, because it
prices the cheap arm as a *substitute* for the expensive one. In both domains the
cheap arm is a **complement**: `c₁` is a function of whether `c₀` ran.

The heuristic the directive asks for, until traces show otherwise: **run every
sound cheap check, always, and never route around one.** Their cost is
negligible, their value is large, and for the sound ones it is free of accuracy
risk by construction. A learned router has nothing to choose between yet — which
is the honest answer to "is the precondition met", and it is a *negative* answer
arrived at with numbers rather than assumed.

What would change this: an unsound cheap arm whose error rate is genuinely
predictable from pre-run world features, or a cost spread far larger than the
2.14x maximum measured here. Neither exists in these three domains today.

## Caveats

- Scheduling shapes are 20 jobs/3 machines and 30/4. **40/5 is absent because the
  ground-truth oracle cannot reach it, not the kernel** — see
  [[2026-08-19-the-ground-truth-cost-2.7-million-times-the-system-it-checked]].
  Even after a 2.7-million-fold speedup the oracle is what caps this domain.
- Slack exactly 0 is excluded for the same reason, and ±0.005 is affordable at 30
  jobs but not 40. The measured peak at −0.03 is therefore a peak *over the grid
  that could be afforded*, and the true peak may sit closer to the boundary. That
  would strengthen the finding, not weaken it: closer to the boundary is where
  local propagation is weakest and the gate still fires everywhere below 0.
- 4 of 20 instances at −0.03 hit the 3s budget, so 62.9% is a **lower bound** on
  that column's share. Censoring biases against the finding.
