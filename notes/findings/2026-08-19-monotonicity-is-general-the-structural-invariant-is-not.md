---
title: Monotonicity is general; the structural invariant is not
date: 2026-08-19
status: measured
arm: certificate-generality
domains: flood, scheduling
---

## Testing a generality claim I made on one instance

The flood certificate replaced sixteen flow solves with one DFS and made
soundness free, and that finding claimed the pattern is *not flood-specific*. On
one instance. This thread has already made the generality-from-one-case error
three times, so the claim gets tested rather than repeated.

The pattern has two ingredients:

1. **Monotonicity** — the perturbation moves the answer one way only, so half the
   objects are safe with no work at all.
2. **A cheap structural invariant** standing in for the expensive computation —
   for flood, 2-edge-connectivity for *"a route survives"*.

Scheduling separates them. It **has** monotonicity: deleting a `has_capability`
claim removes assignments and never adds one, so an infeasible instance stays
infeasible. Its decision is bin-packing with capability constraints, so it may
lack the invariant.

## Only one half transfers

60 instances, perturbation = delete one `has_capability`:

| | fires | unsound |
|---|---:|---:|
| **monotone certificate** (infeasible is safe) | **43** | **0** |
| structural attempt (two capable machines per job) | 9 | **8** |

| policy | mean solves | |
|---|---:|---|
| enumerate every candidate | 6.6 | |
| **monotone half only** | **2.9** | **57% saving, sound** |
| plus the structural attempt | 1.8 | *not a saving — unsound 8 of 9* |

**Monotonicity transfers exactly.** 43 infeasible instances are safe for free
with zero unsound, the precise analogue of flood's non-qualifying vehicles, and
it alone is worth 57%.

**The structural invariant does not.** The closest analogue to two edge-disjoint
routes — *every job has at least two machines capable of it with room to hold it*
— is **wrong on 8 of the 9 instances it fires on**. Two capable machines
guarantee the *capability* survives a deletion and say nothing about whether the
**packing still fits**, which is exactly where bin-packing bites.

## The general statement

**The certificate pattern's reach is set by the complexity of the underlying
decision, not by anything about readers or ambiguity.**

- Reachability characterises *"a route survives"* in polynomial time, so flood
  gets a complete certificate and soundness becomes free.
- Nothing characterises *"a feasible packing survives"* without solving it, so
  scheduling gets only the monotone half.

That is a sharper and more useful claim than "the pattern is not flood-specific",
and it says where to look next in a new domain: **ask whether the kernel's
decision has a polynomial structural characterisation.** If it does, expect a
free certificate. If it does not, expect the monotone half and budget for
enumeration on the rest.

## The half that is free everywhere

Worth stating separately, because it needs nothing from the domain: **the safe
side of a monotone perturbation costs zero.** A vehicle that cannot qualify, an
instance already infeasible — neither can be flipped by a perturbation that only
removes. Any pipeline carrying a deletion-shaped ambiguity gets that half without
a structural insight, and here it is worth 57% on its own.

## A number in the table that is not a saving

The combined row reads 1.8 mean solves and 73%, and it is **wrong**. It is shown
only to price the temptation: an unsound certificate looks like the best row in
the table, and the whole point of the policy is never being wrong when it
answers. The script labels it in place so the number cannot be lifted out of
context.

## What would refute this

A cheap sufficient invariant for scheduling feasibility that fires often enough
to matter — something stronger than the capability condition tried here, perhaps
combining it with capacity slack. That was the stated way to change my mind and I
did not find one; NP-hardness argues against it existing in general, but a
sufficient condition need not be complete, so this is not a proof.
