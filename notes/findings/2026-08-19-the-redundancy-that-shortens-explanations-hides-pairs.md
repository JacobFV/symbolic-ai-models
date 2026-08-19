---
title: The redundancy that shortens explanations is what hides pairs
date: 2026-08-19
status: measured
arm: joint-dependencies
---

## Testing the shipped objective at its named weak point

`omits_load_bearing`, shipped last turn as *the achievable objective*, tests
**single**-claim deletion. The finding that introduced it said so and called
every number a lower bound. That is testable.

| domain | cases | singly load-bearing | **joint pairs** | per case |
|---|---:|---:|---:|---:|
| flood | 12 | 11.2 | **30** | **2.50** |
| solvency | 24 | 5.0 | **0** | 0.00 |

**Joint dependencies exist**, and one is enough: a paragraph can cite every
singly-load-bearing claim and still omit a pair the answer depends on.
`omits_load_bearing` is a **lower bound, not a guarantee** — the fourth check in
this repo whose name promised more than it computes, and it is now documented on
the function.

## The mechanism is the one that buys brevity

The commonest kind is **`link`+`link`** (10 of 30): parallel routes. Delete
either and the other carries the traffic; delete both and it does not.

That is precisely the redundancy that makes flood's explanations short — only 39%
of claims are singly load-bearing *because* alternatives exist. **The property
that buys brevity is the property that creates the blind spot.**

Solvency has **zero**, which a sum predicts: every latest filing is already
individually load-bearing, so nothing is jointly-but-not-singly critical. A
decision with no redundancy has no hidden pairs — and no short explanation
either, relative to its world.

## A self-correction inside this finding

A first run over **6 cases** found 2 pairs and reported them as concentrated in
`flooded`, with links not involved. I wrote that into the script's verdict. At
**12 cases** it is 30 pairs and `link`+`link` is the largest group — my *original*
prediction, which the small sample had talked me out of.

Two data points, a mechanism story, and it was wrong. That is the exactness-audit
lesson arrived at from the other side: not a claimed-exact number this time, but
a claimed **mechanism** on a sample that could not support one.

## What I am not doing

Not extending the check to pairs. It is O(n²) solves — flood's 28 claims give 400
combinations against 28 — and the shipped `load_bearing_cheap` has no pairwise
analogue. The honest move is the one the previous three instances took: **name
the bound, carry the counter-example, and assert the gap in a test** so it cannot
quietly close.

## What would refute this

- 12 cases. The rate 2.5/case has a wide interval and the *existence* is the
  claim, not the rate.
- Triples are untested and would be O(n³). Every number in this note is itself a
  lower bound, for the same reason the last one was.
