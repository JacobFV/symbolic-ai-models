---
title: Precision errors hurt less than recall errors, conservative errors hurt more than permissive ones, and one asymmetry explains both — I predicted the opposite of each
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

## The mechanism, measured rather than argued

> **Being admitted is under-determined. Being blocked is over-determined.**

Directly counted over 300 worlds:

| | n | median | mean | share at the margin |
|---|---|---|---|---|
| vehicles that can go — routes that work | 442 | **1** | 1.40 | **69.0% have exactly one** |
| vehicles that cannot — violated limits across all routes | 354 | **2** | 1.82 | 22.3% would be freed by one flip |

A qualifying vehicle usually has exactly **one** viable route, and every bridge
on it must hold: a conjunction with no redundancy. Break any single limit on
that route and the vehicle is gone. A blocked vehicle is blocked by a median of
**two** violated limits across all routes, so relaxing one leaves it blocked 78%
of the time.

That explains both inversions at once:

- **Conservative errors** attack the conjunction that admits a vehicle, where a
  single break is decisive. **Permissive errors** attack the over-determined
  blocking, where a single relaxation usually is not enough.
- **Recall errors** can delete a *domain element* — a vehicle whose `mass` or
  `capacity` sentence was missed drops out of the fleet and can never be named.
  **Precision errors** never do; they leave the vehicle in the domain with a
  wrong number, and a wrong number is often not the binding one.

The second bullet is the same mechanism as the recall finding's per-kind result,
where `mass` (0.733) and `capacity` (0.747) were the most damaging kinds to lose
and `flooded` (0.960) the least. Two independent channels, one explanation:

> **The fragility is in domain membership, not in constraint values.**

## What this changes about where parse effort goes

If it generalises to enumerate-then-filter pipelines — and the mechanism is
about conjunctions with no redundancy, which is not specific to bridges — then:

1. **Recall on entity and attribute mentions is worth more than precision on
   numbers.** A reader that hedges a number is far less damaging than one that
   drops the sentence naming the thing.
2. **A reader whose errors skew permissive is safer than one whose errors skew
   conservative**, at equal error rate. That is the opposite of the usual
   engineering instinct, and it is a property of the *task's* asymmetry, not of
   the reader.
3. It is also a warning about this task specifically: 69% of qualifying vehicles
   sit on a single viable route, so the generator produces worlds with very
   little routing redundancy. A more redundant world would blunt the whole
   effect, and the number that would show it is the median-viable-routes figure
   above.

## What would have refuted it

- **The metric.** Both columns are reported throughout; exact-set and
  per-vehicle agree on every ordering and on both crossings.
- **The corruption being unrealistic.** The five misread modes are digit-level
  and unit-level failures, not Gaussian noise, and `unit_confused` (×1000)
  produces the largest errors available.
- **The asymmetry being an artefact of the direction-flipping code.** It is
  measured independently of the corruption, by counting viable routes and
  violated limits in the *uncorrupted* worlds.

## What it does not establish

Nothing about real readers. This is still a template reader on generated text
with synthetic error injection, and the honest reading is that it tells you
**which errors a pipeline of this shape can afford**, not what any reader's
error profile actually is.
