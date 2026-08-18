---
title: A finer floor can be a weaker floor, and the sweep is the only way to know
date: 2026-08-18
tags: [lesson, floors, measurement]
---

## The mistake

I published `$8.46e-09 per solved episode above floor` against a floor of
0.2087 — "always guess the commonest country". The strongest available floor was
**0.7888**. The real number is `$4.99e-08`, 5.9x worse, and the honest value of
the geo kernel's precision on that task is **+0.119 over crude 555 km boxes**,
not +0.699 over a constant.

Twenty minutes earlier I had written *"this repo has been burned by a too-low
floor before"* into the same note, as a limitation, and committed it anyway.

## The second, less obvious half

When I did sweep the floor, I expected it to improve monotonically with
resolution and predicted ~0.88 at 1 degree. It **peaked at 5 degrees and
collapsed to 0.4711 at 1 degree**, because at that resolution 77% of grid cells
hold a single airport and leave-one-out empties them.

So: **a finer floor is a sparser floor.** Had I audited the floor by reaching
for the finest resolution — the natural instinct, since finer sounds stronger —
I would have measured 0.3053 at half a degree, concluded the floor was weak,
and made the method look four times better than it is *while believing I had
just been rigorous about it*.

## The mechanism

A floor is a **model with a capacity**, not a constant. Every knob on it trades
bias against variance exactly like the method's knobs do, and the strongest
floor sits at an interior optimum. Reporting the floor at one arbitrary setting
of that knob is the same error as reporting a method at one arbitrary
hyperparameter and calling it the method's performance.

The failure is worse than a normal tuning error because it is **asymmetric and
self-flattering**: a weak floor inflates every lift and every $/solved-above
floor number downstream of it, and nothing in the pipeline complains.

## The guard

- **Sweep the floor, do not pick one.** Report the strongest value found and the
  setting that produced it. One extra loop.
- **Never assume the floor improves with capacity.** Sweep both directions from
  wherever you start and expect an interior maximum.
- **Write the strongest floor into the code**, not just the note —
  `STRONGEST_FLOOR = 0.7888` beside the task, with the resolution, so the next
  quote cannot silently use the weak one.
- **A stated limitation is not a discharged one.** Writing "a stronger floor
  would cut this" and committing anyway is how the last two floor errors here
  shipped. If it is worth writing down, it is worth spending the twenty minutes
  before the number goes out.
