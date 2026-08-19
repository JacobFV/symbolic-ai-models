---
title: The ground truth cost 2.7 million times more than the system it was checking
date: 2026-08-19
status: measured
arm: routing-traces / gate-prunes-the-exponential
---

## What happened

I went looking for execution traces to answer the routing directive — collect
cost per path before learning any policy — and the scheduling domain kept
hanging. Four hypotheses died on the way to the answer, which is the useful part
of this note.

`generate()` called `feasible_by_search()` on every instance, and that was an
exhaustive `itertools.product` over `n_machines ** n_jobs`. Its docstring said
so plainly: *"Exhaustive. 3^6 = 729 assignments"*. It was written for the default
`n_jobs=6`, where 729 is nothing, and nobody had run it anywhere else.

**Infeasible instances never short-circuit.** The loop returns early only when it
*finds* a packing, so the instances a negative slack is built to produce pay the
full price.

| n_jobs | seed 0 | seed 1 | seed 2 | space |
|---:|---:|---:|---:|---:|
| 18 | 0.008s | **53.06s** | 0.049s | 3.9e8 |
| 20 | 0.018s | 1.76s | 0.018s | 3.5e9 |
| 22 | 0.020s | 5.14s | — | 3.1e10 |

The ASP kernel settles those same worlds in **single-digit milliseconds**. The
ground truth cost roughly four orders of magnitude more than the system it
exists to check, and it — not the solver — is what had capped this domain at toy
sizes.

## The fix, and why it is not a weakening

The brute force's justification is sound and survives: a heuristic oracle that
occasionally missed a feasible packing would be indistinguishable from a kernel
bug. So the replacement is **exact**, and every branch it cuts provably cannot
complete:

- **The remaining-capacity bound** — if the jobs still to place need more hours
  than the machines still have, no completion exists. This is `capacity_gate`'s
  own argument applied at every node rather than only at the root, and it is what
  makes infeasible instances cheap. The gate I set out to study turned out to be
  the fix for the thing that stopped me studying it.
- **Symmetry** — two machines with equal remaining capacity and equal
  capabilities generate isomorphic subtrees, so only one is tried.
- **Hardest first** — longest jobs placed first, so it fails shallow.

`feasible_by_brute_force` is **kept**, as an executable specification, and
`tests/test_scheduling_oracle.py` (9 tests, 49 assertions over both sides of the
boundary) binds the two.

Same verdict, on the instances that were unaffordable:

| n_jobs | seed | brute | pruned | brute s | pruned s | speedup |
|---:|---:|---|---|---:|---:|---:|
| 18 | 1 | False | False | 51.946 | 0.00002 | **2,721,429x** |
| 20 | 1 | False | False | 1.738 | 0.00001 | 161,607x |
| 22 | 1 | False | False | 5.018 | 0.00001 | 602,016x |

What the domain now reaches, oracle included, per case:

| n_jobs | n_machines | s/case | search space |
|---:|---:|---:|---:|
| 20 | 3 | 0.0001 | 3.49e+09 |
| 30 | 3 | 0.0002 | 2.06e+14 |
| 40 | 4 | 0.0002 | 1.21e+24 |
| 60 | 5 | 0.0003 | 8.67e+41 |
| 80 | 6 | 0.0005 | **1.79e+62** |

## The test that had to change, and what it reveals

`test_the_oracle_is_exhaustive_rather_than_heuristic` asserted
`"itertools.product" in src`. It pinned the **implementation** as the evidence
for a property that is **behavioural**, which made the oracle unimprovable: a
change that strengthens nothing about correctness and costs 2.7 million times
less failed a test whose subject was correctness. It now checks agreement with
the brute force. The half of it that *is* a source property — independence from
clingo, `get_kernel`, `build_program` — stayed a source check, and now covers
both functions.

There is a second test next door, `test_the_expensive_kernel_really_is_the_
expensive_part`, and it was **passing throughout**. It was not wrong. It measures
cost *inside the flow*, and inside the flow the kernel genuinely is the expensive
node. The oracle sits outside the flow, in the harness that builds the case. The
test's scope ended exactly where the cost was.

## What this does to the routing question

Directive 13 wants a router choosing between execution paths on measured cost.
Before this, the largest cost in the scheduling domain was **not on any path a
router could choose between** — it was in the harness. Two of the four hypotheses
I burned here were about which kernel phase was unbounded (grounding vs solving;
`SCALE=100`'s weights vs the combinatorics). Both were wrong, and both were
wrong in the same way: I was looking inside the system for a cost that was
outside it.

The routing traces themselves are in
`2026-08-19-the-cheap-kernel-is-not-an-escalation-tier.md`.

## What would refute this

Any instance where `feasible_by_search` and `feasible_by_brute_force` disagree.
The test sweeps `n_jobs` 1-8 x slack {-0.30, -0.02, 0.0, 0.05, 0.40} x 6 seeds,
plus machine counts 1, 2 and 4, and asserts both verdicts actually occur — a
suite that only ever saw `False` would pass on `return False`.
