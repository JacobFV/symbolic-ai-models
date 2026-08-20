---
title: Three for three — cheap corpus statistics predict which fix pays, per relation
date: 2026-08-19
status: measured
arm: relation-readability
---

`parent` and `founder` are both classifier-bound. The four representation
families tried on `parent` all described a sentence's **contents**; none described
**where the sentence is**. A Wikipedia intro front-loads its defining facts, so
position is a prior the classifier has never been given.

| relation | arm | coverage | correct | precision | k/n |
|---|---|---|---|---|---|
| `parent` | baseline | 0.293 | 0.131 | 0.449 | 235/1788 |
| | + position | 0.306 | **0.131** | 0.430 | 235/1788 (**+0**) |
| `founder` | baseline | 0.161 | 0.088 | 0.549 | 90/1017 |
| | **+ position** | 0.166 | **0.096** | **0.580** | 98/1017 (**+8**) |

`founder` gains 8 articles with precision *up*; `parent` gains exactly nothing.

## The statistic said so in advance

P(a sentence states the relation) by sentence index:

| index | `parent` | `founder` |
|---|---|---|
| 0 | 0.218 | 0.097 |
| 1 | 0.185 | **0.149** |
| 3 | 0.133 | 0.089 |
| 5+ | 0.125 | **0.034** |
| **first/last ratio** | **1.7x** | **2.8x** |

`founder`'s prior is **1.6 times steeper** and peaks at the *second* sentence —
*"X was founded in 1975 by Y"* follows the defining sentence rather than being it.
`parent`'s is shallow, because an ownership fact appears anywhere in a corporate
history.

## Three for three

This is the third consecutive case where a statistic computable **before any
fitting** predicted which relation an intervention would help:

| statistic | said | intervention | measured |
|---|---|---|---|
| lexicon gap 0.416 vs ≤0.05 | `industry`, not `parent` | alias + proposer supervision | **3.9x** on `industry`, +0.001 on `parent` |
| alias count 142/93 vs 1/0 | `industry`/`country`, not `parent`/`founder` | induced aliases | **+0.124/+0.207** vs +0.004/+0.000 |
| positional prior 2.8x vs 1.7x | `founder`, not `parent` | sentence position | **+8 articles** vs **+0** |

Six predictions, six correct, across three unrelated statistics. The
generalisation is not about any one of them:

> **Which fix pays is a property of the relation, and it is legible in the corpus
> before a model is trained.** The four-factor decomposition says *which
> component*; these say *which intervention on it*.

That is the practical output of this arm, and it is worth more than any single
number in it. A new relation can be triaged in seconds — containment × proposal
for the ceiling, lexicon gap for whether it needs aliases, positional prior for
whether it needs position — and the work aimed at what the statistics name.

## What it does not claim

- **Six predictions on five relations in one genre.** The statistics are not
  validated as a general instrument; they are three-for-three here.
- `parent` remains the relation nothing helps. Its classifier is 0.351, its
  positional prior is flat, it induces one alias, and its lexicon gap is −0.008.
  **Every cheap statistic says there is nothing cheap left**, which is consistent
  and unhelpful — and is exactly the case the oracle measurement says is worth
  1.9x–6.6x to a better model.
- The `founder` gain is **8 articles in 1,017** and should be read as a direction.

## What would have refuted it

`parent` gaining from position. Its prior is 1.7x and shallow, so a gain there
would have meant the statistic does not govern the outcome. It gained zero.
