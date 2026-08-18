---
title: A reader losing 1 claim in 6 leaves the three-kernel pipeline no better than a non-reasoning floor — and the fragility is in the domain facts, not the constraints
date: 2026-08-18
author: lead
status: provisional
tags: [kernels, parsing, cost, flow, refuted-prediction]
---

## The question

The multi-kernel finding priced *reasoning given a world* and said the next arm
was to put a parser in front of it. This is the cheap version of that arm, and it
asks something the expensive version cannot:

> **How much parse fidelity does a multi-kernel pipeline actually need?**

It matters for the cost argument specifically. If the pipeline degrades
gracefully, a cheap approximate reader serves it and the reader's price is a
rounding error against what the symbolic side saves. If it falls off a cliff, the
reader has to be near-perfect and *its* price is the system's price — which is
exactly the misreading `symbolic_ai_core/cost.py` was written after.

## The instrument

`symbolic_ai_generators/flood/read.py` recovers the world from the report with
regexes. **It is a template reader and proves nothing about parsing**: it matches
the phrasings this repo's own generator emits and a human-written report would
defeat it. Its recovery is exact — 300 of 300 worlds round-trip to the same
answer — which is the property that makes it useful here: fidelity can then be
turned *down on purpose* and nothing else changes.

Corruption drops each claim of a named kind with probability *p*. That simulates
a **recall** failure, the failure a real reader has most of — a sentence it did
not match. Precision failures (a claim invented, a number misread) are a
different channel and are not simulated, so every number here is a *lower bound*
on how badly a real reader would hurt.

## Prediction, before the numbers

Stated in advance: steep and asymmetric; `flooded` and `load_limit` losses hurt
most because they open routes and admit trucks; `link` losses hurt least because
the ring-plus-chords network is redundant; the aggregate crosses the floor around
p = 0.10–0.15.

**The ordering prediction was wrong, and wrong in an informative way.**

## Measured, 300 seeds

| drop rate | exact-set | per-vehicle |
|---|---|---|
| 0.00 | 1.000 | 1.000 |
| 0.02 | 0.880 | 0.931 |
| 0.05 | 0.750 | 0.871 |
| 0.08 | 0.633 | 0.802 |
| 0.10 | 0.603 | 0.798 |
| 0.12 | 0.530 | 0.728 |
| 0.15 | 0.500 | 0.711 |
| 0.20 | 0.383 | 0.624 |
| 0.30 | 0.370 | 0.582 |
| 0.50 | 0.333 | 0.513 |
| **strongest floor** | **0.450** | **0.658** |
| always-none floor | 0.347 | 0.509 |

±0.029 on the exact-set column at N = 300.

**The pipeline crosses its strongest floor at p ≈ 0.17 on both metrics.** A
reader losing more than about one claim in six leaves three kernels, a flow DAG
and a brute-force-verified 1.000 no better than a rule that ignores the road
network entirely. At 95% recall (p = 0.05) it still holds 0.750 / 0.871, so the
practical requirement is roughly **≥ 90% per-claim recall**.

## The prediction that failed, and why it is the interesting part

Per kind, at p = 0.20 (so most worlds lose one claim of that kind):

| dropped | agreement | predicted rank |
|---|---|---|
| `mass` | **0.733** | not predicted to matter |
| `capacity` | **0.747** | not predicted to matter |
| `link` | 0.800 | predicted mildest |
| `demand` | 0.900 | — |
| `load_limit` | 0.907 | predicted second worst |
| `flooded` | **0.960** | **predicted worst** |

The two I predicted would dominate are the two that matter least, and the
mechanism is general rather than a quirk of this task:

> **The fragility is in the facts that define the answer's domain, not in the
> facts that constrain it.**

Losing a constraint is usually survivable because constraints are often
non-binding — most worlds have slack, and a bridge limit that was never the
binding one costs nothing when it disappears. Losing a *domain element* is never
survivable, because the answer enumerates the domain: a vehicle whose mass or
capacity went missing drops out of the fleet entirely and can no longer be
named, whatever the constraints say.

That predicts something checkable elsewhere and worth chasing: in any
enumerate-then-filter pipeline, parse effort should be spent on the entity and
attribute layer rather than on the relational and numeric constraints, because
the constraints have redundancy and the entities do not.

## What would have refuted it

- **The metric doing the work.** Exact-set match over a ≤3-element answer is
  brittle by construction, so the whole curve was recomputed as per-vehicle
  accuracy — three independent binary decisions per case. Both metrics cross
  their respective floors at the same p ≈ 0.17, so the shape is a property of
  the pipeline and not of the scoring.
- **The reader being lossy to begin with.** It is not: p = 0 gives 1.000 on 300
  worlds, so every degradation below is attributable to the injected noise.
- **Degrading below the trivial floor**, which would suggest the corruption was
  doing something other than removing information. It asymptotes to 0.333
  against an always-none floor of 0.347 — it decays to the trivial answer and
  stops, which is what removing information should do.

## What this does not establish

It is a **recall** channel only. A real reader also invents claims and misreads
numbers, and a misread bridge limit is worse than a missing one — it is a
constraint that is wrong rather than absent, and the constraint slack that
protects this pipeline against absence gives no protection against error. The
next measurement is that channel, and I expect it to be harsher.

It also says nothing about whether ≥90% claim recall is *achievable* on text
anybody did not generate. This repo's best exact parse recovery is 0.016. Those
are different metrics over different corpora and cannot be compared directly —
but nothing here suggests the gap is small.
