---
title: Cancellation, not tense — and it fails where the predicate is a negation
date: 2026-08-19
status: measured
arm: staleness-gate
---

## The gap it was built for

The channel that costs the most in both domains is **multi-valued** — flood's
`flooded`, scheduling's `has_capability` — so no arity constraint checks it, and
nothing else in either document *knows* those facts. There is no second **source**
to corroborate them. What remains is a second reading of the **same sentence**:
not what it says, but whether it takes it back.

Every real phrasing in both domains is present tense; every distractor is past
tense **with** a cancelling clause. Those two signals are confounded by the
generators, so the gate was built twice — `stale_by_tense` (the past) and
`stale_by_cancellation` (the taking back) — and separated by a third arm: real
claims rephrased in the past **but still true**.

Both cue lists are **closed-class and domain-independent**, which is what makes
this different from a role vocabulary: adding a domain does not add words.

## Measured

**scheduling** (200 cases, default regime)

| surface | no gate | tense | cancellation |
|---|---:|---:|---:|
| clean (default distractors) | 1.000 | 1.000 | 1.000 |
| **hard distractors** | 0.790 | **1.000** | **1.000** |
| clean, real claims in the PAST | 1.000 | **0.645** | **1.000** |
| hard, real claims in the PAST | 0.790 | 0.645 | **1.000** |

**flood** (400 seeds, 252 non-empty, interleaved)

| surface | no gate | tense | cancellation |
|---|---:|---:|---:|
| clean (default distractors) | 0.988 | 0.881 | **0.933** |
| **hard distractors** | 0.679 | 0.659 | **0.933** |
| clean, real claims in the PAST | 0.988 | **0.317** | **0.933** |
| hard, real claims in the PAST | 0.679 | 0.552 | **0.933** |

## Three things

**1. Cancellation is the signal; tense is a coincidence of the generator.** Both
gates repair the scheduling distractor, so catching it decides nothing. The
past-tense arm decides it: the tense gate takes scheduling to 0.645 and flood to
**0.317** on claims that are true, and the cancellation gate does not move at
all. The flood distractor also shows the catch side — *"A disused track **once
ran**…"* carries no past auxiliary, so the tense gate misses it outright.

**2. One shared component repairs the hardest channel in both domains.** On the
honest surface, scheduling 0.790 → **1.000** and flood 0.679 → **0.933**. It is
the first thing in this repo that transfers across domains **unchanged** — no
per-domain word list, no per-domain tuning — and it works on the one channel that
arity, adjacency and enumeration all miss.

**3. It is not free, and the way it fails is the interesting part.** On flood's
clean surface it costs **0.055**, because it deletes a *true* claim:

> Water rose through region_2 during the night and it is **no longer** passable.

`no longer` is a cancellation cue, and the sentence's whole job is to assert that
something **has been** cancelled. **The gate cannot distinguish a sentence that
withdraws its own claim from one asserting that something was withdrawn** — and
flood's `flooded` predicate *is* a cancellation, so the one domain whose damaging
multi-valued channel is a negation is exactly the domain where the gate misfires
on the truth.

That is a property of the predicate, not of the cue list, and no amount of adding
words fixes it. It is also mild here — deleting a `flooded` claim merely fails to
help, where admitting a phantom link destroys the answer, which is the same
asymmetry the reader's own elimination comment records — so the net on the honest
surface is **+0.254**.

## What would refute this

- Two domains, one distractor family each. The cue list is closed-class, but
  "closed-class" is an argument about how the risk *grows*, not a measurement
  that it is small.
- The past-tense arm is four rephrasings per domain, written by me. They are
  natural, and they are mine.
- 0.933 on flood is a ceiling set by the deleted flooding claims; a domain with
  more negation-shaped predicates would pay more, and none was tested.
