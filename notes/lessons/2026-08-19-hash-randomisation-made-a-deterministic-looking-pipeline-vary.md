---
title: Hash randomisation made a deterministic-looking pipeline vary — and it varied by exactly one effect size
date: 2026-08-19
kind: lesson
---

## The mistake

Reporting a single-run delta from a pipeline that **looks** deterministic —
fixed seeds everywhere, no sampling, no shuffling inside the measurement — while
one function sorted a dictionary whose insertion order came from a **set union of
strings**. Python randomises string hashes per process, so that set iterates
differently every run, ties in the sort break differently, and the feature
buckets differ.

It was found by accident: the same arm, same code, same data, printed **213** in
one script and **207** in another. Chasing that showed the *baseline* is exactly
deterministic — 207 three times in one process — so the variation was in the one
component that groups words.

## What it hid

`PYTHONHASHSEED` sweeps of the three arms that use that grouping, against a
baseline that is a fixed **207/1788**:

| arm | seeds | range | verdict |
|---|---|---|---|
| label-aware lexical groups | 216, 217, 220, 223 | **all above 207** | small real effect, ≈ **+12 articles** |
| argument structure | 206, 207, 209, 210, 213 | **straddles 207** | **noise** |
| explicit conjunctions | 209, 211, 212 | overlaps the band | **noise** |

Two published deltas were single draws from these bands: `+0.003` for argument
structure and `+0.003` for conjunctions are **not distinguishable from zero**, and
`+0.005` for lexical groups was in the right place but by luck of the draw rather
than by measurement.

**The noise band is ±3 articles and every effect being reported was 5 to 12.**
That is the specific danger: the variation was the same order as the signal, so
it neither hid the one real effect nor prevented two false ones.

## Why it is easy to miss

Everything visible was seeded. `random.Random(31)`, `np.random.default_rng(19)`,
fixed fold assignment by `i % 4`. A reviewer looking for nondeterminism would
check exactly those and find them sound. The randomness entered through

```python
for w in set(pos) | set(neg):      # iteration order varies per process
    scores[w] = ...
order = sorted(scores, key=lambda w: scores[w])   # ties break by insertion
```

— two lines that contain no random call at all.

## The guard

**Sort with a total order.** A tie-break on the key itself costs nothing and
removes the whole class:

```python
order = sorted(scores, key=lambda w: (scores[w], w))
```

And for anything whose headline is a delta: **run it under two or three
`PYTHONHASHSEED` values before writing the number down.** It is one shell loop,
it takes as long as the measurement, and it distinguishes a 12-article effect
from a 3-article one — which is the difference between the two conclusions this
session drew from these arms.

## Where it does not apply

Deterministic pipelines with no dict-order-dependent sorting, which is most of
them — the generated-domain measurements repeat exactly. The trap needs a
collection built from a set of strings *and* an ordering that can tie.
