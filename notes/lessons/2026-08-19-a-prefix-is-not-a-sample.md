---
title: A prefix is not a sample — corpus files carry their construction order
date: 2026-08-19
kind: lesson
---

## The mistake

Subsampling a corpus with `docs[:n]` and treating the result as a smaller version
of the same corpus. It is not: **the file's order encodes how it was built**, and
every prefix inherits that.

Two instances, an hour apart, both on headline numbers.

- **The composed-query sweep.** `wikipedia_parents_closed.jsonl` is the
  1,661-article scale corpus followed by the 841 **closure** articles — parent
  companies, hubs, the articles both readers are worst on. So `docs[:n]` adds
  hubs *only at the largest size*, and the union's gain rose 2.1% → 3.8% → 6.3% →
  **22.7%** in a clean monotone curve that was mostly the hubs arriving. Shuffled:
  **−9.3% → +17.0% → +18.9% → +19.8%** — a floor and a plateau, not a trend.
- **The Heaps exponents.** Both the 168- and the 1,661-article fits subsample by
  prefix, and both files are in **CirrusSearch relevance order** — prominent
  companies first, whose frames are more canonical and repeat sooner. Shuffled,
  the content-word exponent is 0.669 / 0.728 / 0.701 against a published
  **0.648**; the sampling spread is ±0.03 and the published figure sits below the
  whole shuffled range.

## What it cost

One headline withdrawn ("the union's gain grew sevenfold") and one over-precise
claim corrected ("replicates to three decimals" — the agreement was inside a band
three times wider than itself). Both were caught by the same control, run once and
then applied to everything that shared the pattern.

## Why it is easy to miss

A prefix *looks* like a sample. It has the right size, it is reproducible, and it
needs no seed — which is exactly why it gets used. The order is invisible in the
code: `docs[:500]` says nothing about what determined the first 500, and the fact
lives in whichever fetch script wrote the file, often written days earlier and by
a different concern.

The two orderings here were both **meaningful and different**: append-order from a
second fetch round in one case, search-relevance in the other. Neither was
random, and neither was chosen with subsampling in mind.

## The guard

**Shuffle with a fixed seed before any prefix, and say so at the call site.** One
line, reproducible, and it removes the whole class:

```python
order = list(docs)
random.Random(20260819).shuffle(order)   # the file is in fetch order
sub = order[:n]
```

And when a size sweep is the *result*, **run both orderings and report both** —
the difference between them is a measurement of how much the file's construction
is doing, which is worth knowing on its own. Here it was worth 22.7% against
19.8% in one case and 0.05 of an exponent in the other.

## Where it does not apply

Cross-validated folds by `i % k` are fine — they interleave, so every fold
inherits the same order-mix. Generated corpora indexed by seed are fine, since
the seed is the sample. The trap is specific to **files written by a fetch**,
where the order is a fossil of how the data was collected.
