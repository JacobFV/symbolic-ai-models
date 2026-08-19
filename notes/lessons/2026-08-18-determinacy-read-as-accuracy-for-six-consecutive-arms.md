---
title: I priced determinacy and called it advantage, for six consecutive arms, because the formula never asked whether the answer was right
date: 2026-08-18
author: lead
status: provisional
tags: [lesson, cost, floors, north-star]
---

## The mistake

Six arms in one session were priced with

```python
advantage(f) = MODEL / (f * MODEL + (1 - f) * OURS)
```

where `f` is *the fraction the system cannot settle*. Every published number —
6.8×, 8.3×, 10.2×, 12.2×, and the 1.22× / 1.49× / 1.80× lever decomposition —
came out of it. The formula is arithmetically fine and it **has no place to put
accuracy**, so accuracy was never measured and "settled" was read as "correct".

Against a floor that picks at random among the same candidate sets, the symbolic
resolver's accuracy contribution is **+0.9 points at entity level and −0.1 at
group level**, and `symbolic_ai_core/cost.py` reports its cost per unit of
capability as **infinite**.

## Why it survived six arms

Because each arm was *internally* consistent and each compared against the
previous one on the same basis. A wrong basis is invisible from inside a series
that shares it — every ratio moved sensibly, every control passed, every
permutation test failed as it should. **Nothing inside the series could detect
it.** The repo's own ledger could, in one call, and it had been recommended in
`HANDOVER.md` §7 item 10 the whole time.

## The general shape

> **A formula with no slot for a quantity is a claim that the quantity does not
> matter.** `advantage(f)` has no slot for accuracy, so using it is asserting
> equal accuracy — silently, and once per arm.

This is the same failure as quoting a lift with no floor, moved one level up: not
"I forgot the floor for this number" but "I chose an instrument that cannot
express floors, and then took six measurements with it".

## The guard

- **Before the second arm on a new instrument, run one arm through
  `symbolic_ai_core/cost.py`.** Not at the end of the session — after the first,
  when a basis error costs one arm instead of six.
- **Name what each variable in a hand-rolled formula is NOT.** `f` is
  determinacy, not accuracy; `M` is a list price, not a measured cost; `O` is
  marginal, not amortised. Written down once, the missing slot is obvious.
- **If a series of arms all agree, that is not evidence.** They share a basis.
  Agreement within a series tests consistency, never correctness.

Related: [[audit-the-floor-before-quoting-a-lift]],
[[price-capability-not-tokens]],
`notes/lessons/2026-08-18-a-ratio-whose-ceiling-depends-on-k-cannot-compare-two-ks.md`
— all three are the same disease: *the statistic, not the guess, was the problem.*
