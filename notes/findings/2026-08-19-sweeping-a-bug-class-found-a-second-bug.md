---
title: Sweeping a bug class found a second, worse bug
date: 2026-08-19
status: measured
arm: exact-fit-audit
---

## The sweep

`capacity_gate` compared summed floats and was unsound at exact fit. It was found
by accident. That is a bug **class** — *a decision made by comparing summed
floating-point quantities* — so rather than wait for another accident, I
constructed the exact-fit case in every domain and checked each decision against
exact integer arithmetic in its own smallest unit.

| domain | comparison shape | checked | flips |
|---|---|---:|---:|
| **solvency** | **sum vs threshold** | 200 | **39** |
| flood | one quantity vs one posted limit | 3000 | **0** |
| scheduling | sum vs sum (fixed earlier today) | 60 | 0 |

> solvency, seed 0: float total `618.3599999999999` against threshold `618.36`,
> short by **1.14e-13**

**The risk is summation, not floating point.** Comparing one measured quantity
with one posted quantity has nothing to accumulate; comparing a *sum* does. That
is a rule applicable by inspection rather than by testing every component, and it
is why flood — whose load check is one laden mass against one posted limit — is
clean across 3000 comparisons.

Solvency was **latent**, not broken: its threshold is a random multiple and lands
on the boundary with probability ~0. Fixed anyway, in cents, because it is this
repo's tunable-margin domain and any sweep to exact fit fires it — which is
exactly how the scheduling instance was found. A test confirms the fix changes no
verdict on the real distribution.

## And then the sweep found something worse

Writing the exact-fit test required re-implementing the decision rule, and my
helper disagreed with `decide`. The helper was wrong — but so was something else.

`decide` takes `max(seen, key=lambda p: p[1])` where `p[1]` is the **date**: the
**latest** filing. My solvency reader took `max(seen)` on values: the
**largest**. It even documented itself as *"the largest figure known on or before
the determination date"*.

Revisions in this domain go **down** as well as up:

> seed 69, `group`: files **198.80**, then revises to **188.36**

| | |
|---|---:|
| member-dates where latest ≠ largest | **62 / 948** |
| cases where the verdict flips | **9 / 400** |

**The reader was wrong on 2.25% of cases**, and it had been measured at **1.000
in all six cells** of the phrasing × arrangement grid — over **60 seeds**, with
tests using **30**. At a 2% error rate that is roughly one expected failure, and
it did not land.

Fixed to take the latest filing. Re-measured: **0 disagreements over 400 seeds**,
both as published and interleaved.

## What this corrects

The solvency reader's 1.000 stands — now at 6.7× the sample that was used to
claim it. The **structure-independence** conclusion drawn from it is unaffected,
because it compares grouped against interleaved with the same reader, and both
were wrong in the same way and are now both right.

What does not stand is the confidence: a number measured at 60 seeds cannot see a
2% defect, and I reported it as exact. **The sample size was chosen to run
quickly, not to bound the error it was asserting.**

## The compounding worth noting

Three bugs this week, each found by the previous one's follow-up:

1. `capacity_gate`'s float comparison — found while measuring end-to-end cost.
2. The exact-fit class sweep it prompted — found solvency's latent instance.
3. Writing that sweep's test — found the reader's wrong temporal rule, which was
   never about floating point at all.

None was found by testing the component in question. Each came from **building
the next thing on top of it**, which is the same pattern that produced every
correction on the ambiguity thread.

## What would refute this

- The summation rule is a heuristic, not a theorem: a single-quantity comparison
  could still be unsound if the quantity were itself derived by accumulation.
  Flood's limits are posted, not computed, which is why it is clean.
- 400 seeds bounds the reader's error at roughly 0.25%, not zero. That is stated
  rather than rounded away.
