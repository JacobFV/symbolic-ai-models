---
title: A world carrying its ambiguity is never wrong and almost immediately useless — 4 worlds decide 76% of the fleet, 72 worlds decide 0%, and 2 worlds of the wrong kind decide less than 4 of the right kind
date: 2026-08-19
author: lead
status: provisional
tags: [reader, ambiguity, world-ir, critical-invariant, negative-result]
---

## The invariant under test

The programme's stated critical invariant, and its strongest argument for having
a symbolic world representation at all:

> Do not collapse ambiguity merely to obtain a single world. If the reader
> produces "entity may be A or B", the world should carry that, and downstream
> kernels may resolve it, branch over it, bound over it, or refuse.

It had never been measured. `read_signature` resolves its type-signature
ambiguities using **paragraph position** — a property of this generator's
template — so ablating position makes the ambiguity real:

```
(1 vehicle, 1 quantity)  ->  mass OR capacity
(1 region,  0 quantity)  ->  flooded OR depot OR needs
(0 entities, 1 quantity) ->  the pronoun capacity OR the demand
```

`link` vs `bridge_on` still resolves **structurally** — a bridge is a pair
carrying a limit — so what remains is bounded and enumerable.

Two policies on the same reading. **Collapse** picks one world and answers; it
may be wrong and cannot say so. **Bound** enumerates every consistent world, runs
the three kernels on each, and returns three sets: certainly in, certainly out,
undetermined.

## Collapse against bound, position fully ablated

| policy | result |
|---|---|
| collapse (pick one consistent world) | **0.250** exact-set accuracy |
| bound (72 worlds) | **1.000 sound**, decides **0.0%** of the fleet |

The bound is never wrong and says nothing. That is not yet a verdict on the
invariant — it is a *total* ablation. The useful question is the **regime**.

## The regime

`scripts/ambiguity_regime.py`. Each group is opened or closed independently; a
closed group is resolved from the true world — an oracle for that group only —
which isolates *how wide is the bound with k groups open* from *can the reader
close them*.

| open groups | worlds | sound | cert. IN | cert. OUT | open | **decided** |
|---|---:|---:|---:|---:|---:|---:|
| none (fully resolved) | 1 | 1.000 | 2.18 | 0.82 | 0.00 | **100.0%** |
| **vehicle** | **4** | 1.000 | 1.73 | 0.55 | 0.73 | **75.8%** |
| **bare** | **2** | 1.000 | 0.68 | 0.68 | 1.64 | **45.5%** |
| region | 9 | 1.000 | 0.91 | 0.18 | 1.91 | 36.4% |
| vehicle, region | 36 | 1.000 | 0.73 | 0.14 | 2.14 | 28.8% |
| vehicle, bare | 8 | 1.000 | 0.36 | 0.41 | 2.23 | 25.8% |
| region, bare | 18 | 1.000 | 0.09 | 0.05 | 2.86 | 4.5% |
| all three | 72 | 1.000 | 0.00 | 0.00 | 3.00 | **0.0%** |

**Every row is sound.** The invariant delivers what it promises: a world that
carries its ambiguity never produces a wrong answer.

### Two results

**1. Carrying ambiguity is always sound and rapidly vacuous.** A bound stays
useful — half the fleet decided — only up to **4 worlds**. At 72 worlds it
decides **exactly nothing**, and 72 worlds is computationally trivial. *The
bound's usefulness collapses long before the enumeration becomes hard*, so
"can we afford to enumerate" is the wrong question to ask about ambiguity.

**2. Decidedness is not a function of world count.** `bare` is **2** worlds and
decides 45.5%; `vehicle` is **4** worlds and decides 75.8%. Two worlds of the
wrong kind are worse than four of the right kind.

> **An ambiguity budget cannot be counted in worlds.** What matters is *which*
> distinction is left open, not how many readings survive.

The expensive one is `bare` — which number is the **demand**. That is the same
claim this session has repeatedly found critical: it is pronoun-stated, its loss
took the no-coreference arm to 0.000, and being merely *unsure* about it costs
more per world than any other ambiguity here.

## What this says about the invariant

The invariant is **right and not sufficient**. Never collapsing is free
soundness, and soundness alone is not actionable: a caller told "one of these
three vehicles, we cannot say which" has learned nothing. The design consequence
is not "carry ambiguity" but:

> **Carry ambiguity, and spend reader effort on the distinctions whose ambiguity
> is expensive** — which is measurable per group, before the reader is built,
> exactly as dependency size is.

## Two bugs the soundness check caught

Both would have produced a publishable-looking number.

- The enumeration chose which bare quantity was the demand and **dropped the
  rest**, so one vehicle had no capacity in *every* world. Truth outside the
  bound on 19 of 22 cases.
- It assumed exactly **one** flooded region and permuted the first three
  lone-region sentences. Seed 25 floods two, giving four such sentences, and the
  true assignment was unreachable. Sound on 21 of 22, which is exactly the kind
  of near-miss that reads as noise.

An unsound bound is a bug, not a finding. Soundness is now 1.000 on every row.

## What would refute it

- **One task, 3 vehicles.** The fleet is small, so "decided" is coarse — one
  vehicle is 33%. A task with more candidates would give a finer curve and might
  move the 4-world threshold.
- **Closed groups are closed by oracle.** This measures bound width at a given
  ambiguity level, not any reader's ability to reach that level.
- **Bounding is the weakest use of a carried ambiguity.** Kernels could branch,
  request more information, or return a ranked mixture. Only the bound is
  measured, and it is the least informative of those.

## Reproduce

```bash
uv run python -u scripts/ambiguity_vs_guessing.py
uv run python -u scripts/ambiguity_regime.py
```
