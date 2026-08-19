---
title: A ratio whose ceiling depends on the sample size cannot compare two samples of different size — and pre-registering the direction does not save you
date: 2026-08-18
author: lead
status: provisional
tags: [lesson, metrics, prediction-ledger, floors]
---

## The mistake

Comparing two crosswalks — one of 2,383 rows, one of 2,281,221 — on
**(coverage by dollar) / (coverage by count)**, to test whether the small
*curated* one was better targeted at what a workload weighs.

| crosswalk | rows | by count | by dollar | ratio |
|---|---:|---:|---:|---:|
| filed, GLEIF ISIN→LEI | 2,281,221 | 27.9% | 75.0% | **2.68×** |
| curated, wikidata→ISIN | 2,383 | 7.5% | 68.8% | **9.21×** |

3.43× apart, in the predicted direction, with a plausible mechanism already
written down. It reads as a clean confirmation.

**It is an artefact of the metric.** That ratio has a hard ceiling of
`1 / coverage_by_count` — a crosswalk covering 7.5% of securities *cannot*
score above 13.3×, and one covering 27.9% cannot score above 3.58×. The smaller
crosswalk scores higher for being smaller, before any question of targeting.

Normalised against an **oracle picking the best k securities at each crosswalk's
own k**, with a random draw at the same k as the floor:

| crosswalk | random | actual | oracle | **attained** |
|---|---:|---:|---:|---:|
| filed | 26.7% | 75.0% | 99.9% | **66.0%** |
| curated | 8.3% | 68.8% | 95.0% | **69.8%** |

**1.06× apart.** The mechanism is not there.

## What it cost, and what caught it

Nothing published, because the repo's standing rule — *audit the floor before
quoting a lift* — was applied out of habit to a number heading for a finding.
This is the first time that rule has caught something the **prediction ledger
could not**, and that is the reusable half.

## The new failure mode for the ledger

I pre-registered a refutation criterion: *"if the curated ratio is not clearly
above the filed one, the enrichment is a property of bridging or of size in
general."* The criterion was honest, stated before the run, and **would have
confirmed a mechanism that does not exist** — because it named the wrong
statistic.

> **Pre-registering the direction is worth nothing if the statistic is not
> comparable across the arms it is comparing.** A prediction ledger checks
> whether you guessed the number right; it cannot check whether the number
> means what you think it means.

## The guard

Before registering a prediction on a ratio, derive its **ceiling as a function
of the arms' parameters**. If the ceiling differs between arms, the ratio is not
the statistic — the **fraction of the span between a floor and a ceiling
computed at each arm's own parameters** is. Both endpoints, not just the floor:
this repo already knew to floor a lift, and the ceiling is the half that was
missing.

Related: [[audit-the-floor-before-quoting-a-lift]],
`notes/lessons/2026-08-18-magnitude-predictions-over-optimistic-thirteen-to-nil.md`.
