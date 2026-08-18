---
title: Precision errors hurt less than recall errors and conservative errors hurt more than permissive ones — I predicted the opposite of each, and then my own control refuted my explanation too
date: 2026-08-18
author: lead
status: provisional
tags: [kernels, parsing, cost, refuted-prediction, asymmetry]
---

## Two predictions, both wrong, both wrong the same way

The recall finding
(`2026-08-18-what-parse-fidelity-a-multi-kernel-pipeline-needs.md`) ended by
predicting that the **precision** channel would be harsher: *"a misread number is
a constraint that is wrong rather than absent, and the constraint slack that
protects this pipeline against absence gives no protection against error — I
expect that channel to be harsher."*

It is not. It is milder at every rate tried. And a second prediction inside the
same experiment — that **permissive** errors (limits read too high, masses too
low) would be more damaging than conservative ones, because they let vehicles
through that should be blocked — is also backwards.

One mechanism accounts for both, and it is measurable directly.

## Measured, 300 seeds

Recall = drop the claim. Precision = keep the claim, corrupt the number, with
realistic reader failures: a dropped or added digit, a transposition, a tonne
read as a kilogram, a ±20–30% slip.

| drop/error rate | recall exact | recall per-veh | precision exact | precision per-veh |
|---|---|---|---|---|
| 0.02 | 0.880 | 0.931 | **0.960** | **0.984** |
| 0.05 | 0.750 | 0.871 | **0.903** | **0.949** |
| 0.08 | 0.633 | 0.802 | **0.847** | **0.929** |
| 0.10 | 0.603 | 0.798 | **0.820** | **0.920** |
| 0.15 | 0.500 | 0.711 | **0.717** | **0.867** |
| 0.20 | 0.383 | 0.624 | **0.650** | **0.821** |

Strongest floor: 0.450 exact / 0.658 per-vehicle. Recall crosses it at
p ≈ 0.17; **precision does not cross it until roughly p ≈ 0.30.**

Direction of the error, at rate 0.10:

| errors are | exact | per-vehicle |
|---|---|---|
| conservative (limits down, masses up) | **0.763** | **0.889** |
| either | 0.820 | 0.920 |
| permissive (limits up, masses down) | **0.867** | **0.930** |

## The mechanism I proposed, and the control that refuted it

The first explanation I wrote down was this:

> Being admitted is under-determined. Being blocked is over-determined.

with the supporting count over 300 worlds at the default parameters:

| | n | median | mean | share at the margin |
|---|---|---|---|---|
| vehicles that can go — routes that work | 442 | 1 | 1.40 | 69.0% have exactly one |
| vehicles that cannot — violated limits across all routes | 354 | 2 | 1.82 | 22.3% freed by one flip |

The story: a qualifying vehicle usually has exactly one viable route, every
bridge on it must hold, so a conservative error is decisive; a blocked vehicle is
blocked several times over, so a permissive error usually is not enough.

**That story is wrong, and its own control says so.** If single-viable-route
fragility were the driver, the conservative-vs-permissive gap should be *largest*
where that share is highest. Sweeping the number of chords in the road network —
with the number of bridges **held fixed at 4**, because otherwise the sweep also
sweeps how many limits there are to misread and the two effects are inseparable:

| chords | single-route share | conservative | permissive | gap |
|---|---|---|---|---|
| 0 | **1.000** | 0.907 | 0.880 | **−0.027** |
| 2 | 0.699 | 0.840 | 0.867 | +0.027 |
| 4 | 0.401 | 0.760 | 0.900 | +0.140 |
| 6 | **0.167** | 0.747 | 0.913 | **+0.167** |

The gap is *nil* exactly where every qualifying vehicle sits on a single route,
and largest where almost none does. The proposed mechanism is refuted.

## The mechanism that survives

Reading the two columns apart rather than as a gap:

- **permissive damage is flat to slightly falling** (0.880 → 0.913) as
  redundancy rises;
- **conservative damage rises sharply** (0.907 → 0.747).

and the quantity that moves with them:

| chords | mean answer size | empty-answer share | mean viable routes |
|---|---|---|---|
| 0 | 0.59 | 0.700 | 0.62 |
| 2 | 1.44 | 0.340 | 1.57 |
| 4 | 2.23 | 0.107 | 3.05 |
| 6 | 2.43 | 0.047 | 4.83 |

> **A conservative error can only damage a positive, and positives get more
> numerous as the world gets more connected. A permissive error can only damage
> a negative, and negatives get more over-determined at the same time.**

Both halves push the gap the same way, and the second half is the surviving part
of the original story: a blocked vehicle at 6 chords must be blocked on every one
of ~5 routes, so relaxing one limit almost never frees it. What did *not*
survive is the claim about the admitting side — one viable route is not what
makes conservative errors bite; having more vehicles to break is.

The recall result's per-kind ordering — `mass` (0.733) and `capacity` (0.747)
worst to lose, `flooded` (0.960) mildest — is unaffected and has its own
mechanism, which the precision-vs-recall comparison also supports: **a recall
error can delete a domain element and a precision error never can.**

## What this changes about where parse effort goes

If it generalises to enumerate-then-filter pipelines — and the mechanism is
about conjunctions with no redundancy, which is not specific to bridges — then:

1. **Recall on entity and attribute mentions is worth more than precision on
   numbers.** A reader that hedges a number is far less damaging than one that
   drops the sentence naming the thing.

   > **Bounded later the same day.** The solvency task reproduces this ratio
   > exactly (1.74× against flood's 1.76×) — but only at a *moderate decision
   > margin*, and the ordering **inverts to 0.11×** at a large one, because a
   > missing term is a bounded additive error while a misreading is unbounded and
   > multiplicative. See
   > `2026-08-18-recall-beats-precision-only-in-the-middle.md`. The claim above
   > holds in the regime the flood task occupies and was generalised too far.
2. **A reader whose errors skew permissive is safer than one whose errors skew
   conservative**, at equal error rate. That is the opposite of the usual
   engineering instinct, and it is a property of the *task's* asymmetry, not of
   the reader.
3. **The effect strengthens with connectivity**, which was not the guess. At
   the default two chords the gap is +0.027; at six it is +0.167. So the more
   route redundancy a domain has, the more it matters that a reader's errors
   skew permissive rather than conservative.

## What would have refuted it

- **The metric.** Both columns are reported throughout; exact-set and
  per-vehicle agree on every ordering and on both crossings.
- **The corruption being unrealistic.** The five misread modes are digit-level
  and unit-level failures, not Gaussian noise, and `unit_confused` (×1000)
  produces the largest errors available.
- **The asymmetry being an artefact of the direction-flipping code.** The route
  and limit counts are taken in the *uncorrupted* worlds, independently of the
  injection.
- **The redundancy sweep being confounded.** It was, on the first run: more
  chords means more links means more bridges, so the sweep also swept how many
  limits there were to misread. Re-run with the bridge count pinned at 4, the
  pattern held and got cleaner — and in the process refuted the mechanism the
  first draft of this note asserted.

## What it does not establish

Nothing about real readers. This is still a template reader on generated text
with synthetic error injection, and the honest reading is that it tells you
**which errors a pipeline of this shape can afford**, not what any reader's
error profile actually is.
