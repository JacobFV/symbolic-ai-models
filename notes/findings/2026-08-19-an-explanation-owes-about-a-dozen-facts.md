---
title: An explanation owes about a dozen facts, whatever the world
date: 2026-08-19
status: measured
arm: explanation-length-across-domains
domains: flood, scheduling, solvency
---

## The generality question the complete renderer left

The complete renderer costs +37% length on flood because only 38% of claims are
load-bearing. That is flood's number, and the finding said so. Does a short
honest explanation exist for the other two?

| domain | decision | claims | **load-bearing** | share |
|---|---|---:|---:|---:|
| flood | max-min over paths | 28.5 | **11.2** | 39% |
| solvency | sum vs threshold | 11.1 | **5.0** | 45% |
| scheduling | packing at exact fit | 48.9 | **12.4** | 25% |

All three admit one. Explanations run **5–12 facts** across worlds of **11–49**
claims — a 2.5× spread against a 4.4× spread in world size.

**The absolute count is flat; the share is not.** The share varies mostly because
the denominators do, and quoting it invites a story about redundancy the absolute
numbers do not support.

## Two structural predictions, both wrong

**First**: exact fit means no slack means everything matters, so scheduling
should need the *most*. It needs the **least by share** — 25%.

**Second**: then the small share must mean the obstruction is a small local
witness, a few conflicting jobs. It touches **10 of 20 jobs**. Not local either.

What actually drives scheduling's low share is its **denominator**: 48.9 claims,
most of them `has_capability` facts about machines that are individually inert.
Its explanation is 12.4 facts, the *largest* of the three in absolute terms.

With three points and two dead hypotheses, the flat count is a **description, not
a law**. It is recorded that way.

## What is worth carrying

- Every domain here admits a complete explanation of about a dozen facts, so the
  complete renderer is not a flood-specific trick.
- **Explanation length does not track decision difficulty.** Scheduling's
  decision is NP-hard and its explanation is the same size as flood's, whose
  decision is a widest path. That is a third axis independent of the two already
  measured — error concentrates where the signature is ambiguous, time where the
  decision is hard, and explanation length tracks neither.
- Quote the **absolute** count. The share is a ratio to a world size that is an
  artefact of how the generator was written.

## What would refute this

- Three generators, all written by the same hand, all with worlds under fifty
  claims. A domain with thousands of facts is where a flat count would be
  surprising rather than unremarkable, and none exists here.
- The measurement deletes **single** claims. A pair whose joint removal changes
  the answer while neither alone does would be invisible, and every number in
  this note would be a lower bound.
