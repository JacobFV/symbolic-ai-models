---
title: The detectable error is the harmless one
date: 2026-08-19
status: measured
arm: scheduling-hard-distractors
---

## The same defect, in the second domain, found the same way

Flood's disused-track distractor was inert only because the generator drew its
endpoints from **outside** the network. Scheduling's three distractors are inert
for the matching reason: the withdrawn machine and the cancelled job carry no
capability and no quantity, and *"No machine on this floor is set up for
anodising"* names a capability **outside the vocabulary**. All three are rejected
for free by a list that was declared for a different purpose.

Point one at a real entity with an in-vocabulary word — *"machine_0 was set up to
paint last shift, before the head came off"* — and the reader must admit it.

## The asymmetry, established before the run

Each job needs **exactly one** capability; a machine holds **one to three**. So
a spurious `needs_capability` violates arity and is catchable by the check built
for flood this morning, and a spurious `has_capability` is not. That much was
read off the generator. What follows was not:

| arm | accuracy | false FEASIBLE | false infeasible | arity fires |
|---|---:|---:|---:|---:|
| default distractors (published) | **1.000** | 0 | 0 | 0.000 |
| hard: machine only (`has_capability`) | **0.790** | **42** | 0 | **0.000** |
| hard: job only (`needs_capability`) | 0.965 | 2 | 5 | **1.000** |
| hard: both | 0.780 | 42 | 2 | 1.000 |

200 cases, default regime (6 jobs, 3 machines, slack 0.15).

**The damaging error is invisible and the visible error is harmless.** One
admitted sentence costs 0.210 accuracy, every single failure in the **unsound**
direction — an infeasible floor reading as feasible, because the reader granted a
machine a capability it does not have — and the arity check fires on **none** of
them. The catchable side costs 0.035 and fires on **every** case.

I predicted the job side would hurt *more* (0.25–0.50 against a measured 0.035),
on the reasoning that an extra requirement makes a job harder to place. It does
not: machines hold several capabilities, so some machine usually has both.
Direction predicted right on both arms, magnitude wrong by 6× on one.

## What this does to the audit

Scheduling is the domain `audit_surface` scores at **0.000 ambiguity mass** —
every claim kind separated outright by its signature, no coreference needed. That
number has been credited with predicting reader difficulty, where error
concentrates, payback and maintenance. It does not predict this. One sentence
takes the domain from 1.000 to 0.790, all of it unsound, and the audit says the
surface is clean.

The reason is exact and is the same one that made the audit blind to the
phantom-link channel this morning: **it measures ambiguity of the signature, not
fragility of the vocabulary.** `machine_0 was set up to paint` has the
`(machine, capability word)` signature, unambiguously, and is false. Signature
determinacy says a reader *can* type the claim; it says nothing about whether it
*should*.

That is now two things the audit cannot predict, both found in one day, both of
the same shape.

## The general statement

The pairing law says soundness is a property of (channel, check). This adds the
part that decides whether the pairing is worth having:

> **Detectability comes from redundancy, and redundancy is a property of the
> role's arity — which has nothing to do with how much damage an error there
> does.**

`needs_capability` is single-valued and therefore self-checking; `has_capability`
is multi-valued and therefore not. The generator did not arrange this and neither
did the reader. It follows from what the domain means, and it lands the wrong way
round in both domains measured today — flood's undetectable direction (flooding
misfiring onto depot) costs 0.655, its most detectable one (needs) costs 0.865.

So a system built to catch its own reading errors will, by default, catch the
ones it could most afford to make. Closing the gap needs a **second reading of a
multi-valued fact**, which nothing in this repo currently has.

## What would refute this

- Two domains, one distractor sentence each, hand-written by me. The rate at
  which a real corpus produces such sentences is not measured.
- The 0.210 is at the default regime. At `HARD_REGIME` the margins are tighter
  and a spurious capability may matter more or less; unmeasured.
- `hard_distractors` defaults to `False`, so every published scheduling number
  keeps its meaning. The honest setting is `True`, and the previously published
  1.000 reader accuracy is now a statement about the easy surface.
