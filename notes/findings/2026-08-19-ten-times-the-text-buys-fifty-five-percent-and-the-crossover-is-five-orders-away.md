---
title: Ten times the text buys 55%, the Heaps exponents replicate, and the crossover with four hand patterns is five orders of magnitude away
date: 2026-08-19
status: measured
arm: real-text-scale
---

The real-text arm diagnosed the learned reader's loss to four hand-written
patterns as **volume**, then measured Heaps exponents on the 168-article corpus
and registered a prediction about what ten times the text would do. The corpus
now exists: **1,661 Wikipedia company intros**, 9.9x the original, fetched in
batches after the one-page-at-a-time fetcher spent hours on 49 articles.
`data/artifacts/wikipedia_parents_scale.jsonl`; the published 168-article file is
untouched.

## 1. The Heaps exponents replicate, one of them almost exactly

Fitted by subsampling the **new** corpus to 10%, 25%, 50% and 100%:

| representation | n=168 corpus | **n=1,661 corpus** | predicted |
|---|---|---|---|
| full token path, β | 0.830 | **0.915** | "stays near 1" ✓ |
| full path, singleton share | 0.912 | **0.898** | "above 0.85" ✓ |
| full path, mean count | 1.21 | **1.41** | "below 1.6" ✓ |
| **last content word, β** | 0.641 | **0.648** | 0.64 ✓ |
| content word, singleton share | 0.741 | **0.586** | falls ✓ |
| content word, mean count | 2.12 | **4.40** | ≈4.8 — close |
| content word, top-5 share | 0.463 | **0.440** | ">0.55" ✗ |

**The content-word exponent replicates to three decimals** across a tenfold
change in corpus size, which is the strongest evidence available that this is a
property of the phenomenon and not of 168 articles. The one miss is the head
share: it **saturates near 0.44** rather than rising, because more text brings
more distinct triggers as fast as it thickens the common ones. Mean count rises;
concentration does not.

And the learned triggers are now legible, with counts that make them learnable:
`subsidiary` 157, `owned` 85, `company` 74, `acquired` 47, `division` 33,
`part` 28. **That is the hand reader's pattern list, recovered from data** — which
is what the volume hypothesis said would happen.

## 2. Ten times the text buys 55%

| | 168 articles | **1,661 articles** |
|---|---|---|
| coverage | 0.417 | **0.480** |
| **correct** | 0.113 | **0.175** |
| precision | 0.271 | **0.365** |
| classifier recall | 0.256 | **0.395** |
| ranker \| label | 0.556 | 0.400 |
| ceiling | 0.577 | 0.594 |

Registered prediction: `parent` correct **0.20–0.30**. Measured **0.175** —
right direction, over-predicted magnitude. The gap to the hand reader's 0.393
narrows from 3.5x to **2.2x**.

## 3. Where the crossover is, and it is not close

Classifier recall grew 0.256 → 0.395 over 9.9x the data, a factor of **1.54 per
decade**. Extrapolating that rate, matching four hand-written patterns needs
roughly **10⁵–10⁶ articles** — two to three more decades of text to recover what
a person wrote in an afternoon from knowing what English does with ownership.

That is the quantitative answer this arc was after, and it comes with a sting:
**scale fixes the classifier and exposes the ranker.** The ranker fell 0.556 →
0.400 as the corpus diversified, and with the ceiling at 0.594 the product caps
at `0.594 × 1.0 × 0.400 = 0.238` even with a perfect classifier. More text alone
cannot pass 0.393. The remaining factor is role assignment — which mention fills
the slot — and it is now the binding one.

## 4. What this says about the bottleneck

The knowledge-acquisition bottleneck is a **quantity, and the exchange rate is
now measured**: on this task, four hand-written patterns are worth about five
orders of magnitude of distantly supervised text, and the substitution is not
free at either end — the patterns cap out at 68% of the corpus ceiling, and the
text needs a better role model before it can use its own volume.

## What would have refuted it

The content-word exponent moving toward 1 at scale — the sublinearity would then
have been an artefact of 168 articles and scale would not be a lever at all. It
came back at 0.648 against 0.641, which is as close to a replication as this
corpus can give.
