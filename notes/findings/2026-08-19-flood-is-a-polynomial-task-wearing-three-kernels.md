---
title: Flood is a polynomial task wearing three kernels
date: 2026-08-19
status: measured
arm: non-monotone-certificate
---

## How this was found

Chasing the last stated limit of the certificate work — that it covers only
**monotone** perturbations — I built a margin certificate for a misread bridge
limit. It is sound (0 unsound on 19 fires) but incomplete, missing 9 of 28
decided cases. I guessed the misses were edges lying on no depot→site path and
added a relevance test.

**It changed nothing**: 19 fires and 9 missed either way. Every bridge edge was
already on some path.

So the misses needed *route-level* reasoning — does the vehicle still have a
qualifying route — and that is a **widest-path** computation. Which raised the
uncomfortable question.

## The finding

`flood.flow.solve` answers with three kernels: datalog reachability, ASP route
enumeration, SMT load checking. The decision it computes is:

> maximise the minimum bridge limit from depot to site over non-flooded regions;
> a vehicle qualifies iff `capacity ≥ demand` and `mass + demand ≤ bottleneck`.

A max-min Dijkstra. **It agrees with the full flow on 200 of 200 cases.**

**Flood's decision is in P**, and its kernel stack is exponential machinery on it.

## What this does and does not overturn

**Reframed.** *"A certificate makes soundness free"* is true, and the mechanism
is not the elegant one I gave. The certificate is exact because it is **the same
computation as the decision** — of course a polynomial restatement can settle
insensitivity in one pass. The monotonicity argument is still correct and still
does real work in scheduling; it was not what made flood cheap.

**Reframed.** Flood's cost figures — `$/correct`, the kernel ablations, the price
of soundness — measure **the pipeline**, not **the task**. They are real costs of
the system actually built, and they are not evidence that heterogeneous kernels
are needed for this problem. They are evidence of what those kernels cost when
they are not.

**Untouched.** Everything about *reading*. The reader findings, the audit, the
closure result, the decidedness law, the honest milestone's reader/kernel
decomposition — none of that depends on how the answer is computed once the world
is known. The hard part of this pipeline was never the kernels, which is itself
the point the honest milestone made from the other direction.

**Untouched.** Scheduling. Its feasibility is bin-packing with capability
constraints, genuinely NP-hard, and the previous finding measured exactly that:
the monotone half transfers there and the structural half does not, *because* no
polynomial characterisation exists. Scheduling is where the kernels earn their
keep.

## The control that makes the equivalence non-vacuous

An equivalence could hold because both sides ignore the hard parts, so
`test_flooding_and_limits_both_bind` asserts that removing the flooding claims
changes the bottleneck on some case, and likewise for the bridge limits. Both
fire. The widest-path computation is genuinely doing the flooding and load work,
not skipping it.

## What I take from it

The certificate line produced three real results — soundness at 13.4×, then free,
then the monotone half generalising to scheduling — and one of them rested on a
property of the *benchmark* I had not checked. **The check cost twenty lines and
should have come first**: before pricing an expensive computation, ask what the
decision actually requires.

Recorded as a limit on flood as an instrument rather than as a defect: it remains
a good testbed for *reading*, which is what this programme is about, and a poor
one for arguing that multi-kernel reasoning is necessary.
