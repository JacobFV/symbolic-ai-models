---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-the-loss-was-committing-to-a-path-and-a-vote-does-not-commit,
          2026-08-17-verification-and-diversity-are-in-tension,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# The sharpness knob was measured "flat" and is a 0.049 lever — the earlier reading was flat only in the column it was ranked by

`vote_sharpness` was measured once before, on `frontier-soft`, and written up as
**flat**: bits spanning 6.959–6.984 across a sixteen-fold range, with sharper
slightly better. That was reported as "flattening costs 0.013 of accuracy and
buys nothing".

It is still flat on bits. Re-run on `frontier-pointsoft`, development split:

| sharpness | acc | bits | **renamed** | drop |
|---:|---:|---:|---:|---:|
| 8.0 | 0.4476 | 6.407 | 0.2559 | 0.1878 |
| 4.0 | 0.4376 | **6.392** | 0.2601 | 0.1787 |
| 2.0 | 0.4286 | 6.405 | 0.2754 | 0.1526 |
| 1.0 | 0.4187 | 6.429 | 0.2962 | 0.1217 |
| 0.5 | 0.4085 | 6.448 | **0.3048** | **0.1026** |

Bits span **0.056** and still favour sharp. **Renamed accuracy spans 0.049** — on
`frontier-soft` that same column spanned **0.0008**, sixty times less.

My prediction was that the bits curve would stop being flat. It did not.
Refuted, and the interesting thing was in a column I was not ranking by.

## Why the knob became a lever

The knob did not change; the **vote set** did.

| | single-symbol votes | median top-share | fires on |
|---|---:|---:|---:|
| `frontier-soft` | 0.5265 | **1.0000** | 2,287 / 3,497 |
| `frontier-pointsoft` | **0.2885** | **0.7894** | **3,497 / 3,497** |

With the pointer there is disagreement to reweight for the first time — and
because the disagreement is specifically between renaming-invariant `copy` votes
and memorising `map` votes, flattening shifts weight from the second to the
first. That is why the effect appears in the renamed column and nowhere else.

A knob inert in one column and a strong lever in another is
`a-ranking-is-a-property-of-a-metric` applied to a **parameter** rather than to a
model ranking, which is a use of that lesson this repo has not had before. The
old reading was not wrong; it was *complete only for the column it reported*, and
it was written as though it were general.

## `frontier-pointflat`, settled on dev and confirmed on evaluation

Three predictions carried from the development split to the evaluation seeds:

| | predicted | measured |
|---|---|---:|
| renamed pooled | ≈ 0.30 | **0.318** |
| `label_acc` | ≈ 0.41 | **0.411** |
| `label_bits` | ≈ 6.45 | **6.500** |

## The arc, on the bucket that carries it

`renamed acc | copyable` across this session's chain:

| model | | % of the 0.520 ceiling |
|---|---:|---:|
| `frontier-floortype` | 0.055 | 11% |
| `frontier-typepoint` | 0.306 | 59% |
| `frontier-point` | 0.340 | 65% |
| `frontier-pointsoft` | 0.371 | 71% |
| **`frontier-pointflat`** | **0.434** | **83%** |
| `corefer-001` | 0.492 | 95% |

From 65% to 83% of ceiling in two changes, neither of which touched what the
model can *represent* — both were about how it chooses among what it already
proposes. The gap to `corefer` is now **0.058**, from 0.186 when the pointer was
added.

## What this costs and what is still open

`label_acc` falls 0.4372 → 0.4110 and bits rise 6.457 → 6.500. So this is not a
free improvement: it is the accuracy/equivariance trade again, now steerable by a
continuous knob rather than by adding or removing a rule form. The honest table
still has more than one row, and which sharpness is "right" is a choice of what
the model is for.

Unexamined: the non-copyable bucket is **0.000** here, as it is for every model
under renaming, so none of this touches the finding that naming an absent symbol
requires vocabulary. And `corefer`'s remaining 0.058 is presumably its reranking
stage, which this pointer does not have.
