---
title: The model-class claim survives its own named limit — a canonical frame does not rescue the features
date: 2026-08-19
status: measured
arm: representation
---

Four representations on `parent` moved the number by two to seven articles in
1,788, and the conclusion drawn was about the **model class**. That finding names
its own untested limit: *"All four measured on `parent` only. `headquarters`
responded to frames earlier (+33% on the ranker), so a relation with a canonical
frame may behave differently, and the model-class claim is not tested there."*

This tests it. `headquarters` is the relation that should disagree — top-5 frame
share **0.274** against `parent`'s 0.179, one dominant realisation
(*headquartered in X*, *based in X*). If the missing operation is conditioning,
a relation whose conditioning is essentially *one frame* ought to be expressible
by a linear model. Gold for all 2,502 articles from the P159 fetch.

## Both relations, same four arms

| relation | arm | coverage | correct | precision | Δ articles |
|---|---|---|---|---|---|
| `parent` | baseline | 0.306 | 0.116 | 0.378 | 207/1788 |
| | + structure | 0.306 | 0.117 | 0.382 | **+2** |
| | + conjunctions | 0.306 | 0.118 | 0.386 | **+4** |
| | + lexical | 0.320 | 0.114 | 0.357 | **−3** |
| `headquarters` | baseline | 0.455 | **0.264** | 0.580 | 632/2394 |
| | + structure | 0.455 | 0.265 | 0.582 | **+2** |
| | + conjunctions | 0.455 | 0.262 | 0.576 | **−4** |
| | + lexical | 0.464 | 0.266 | 0.575 | **+6** |

**Predicted features would pay materially more on `headquarters`. They do not** —
the deltas are −4 to +6 on both relations, and the signs are not even consistent
between them.

## What the canonical frame does and does not buy

It buys a great deal, and it buys it *in the baseline*. `headquarters` reads at
**0.264** against `parent`'s 0.116 — **2.3x** — and its precision is 0.580 against
0.378. A relation stated one way is simply easier to read.

What it does not buy is **any return on additional features**. The baseline's
frame features already capture the canonical frame; there is nothing left for a
structural, conjunctive or lexical refinement to add. So the model-class claim
survives across a 2.3x difference in baseline difficulty and across relations
with very different frame concentration:

> No family of indicator features tried moves either relation by more than six
> articles, whether the relation has one dominant frame or fifty.

## A discrepancy to state rather than hide

The `+ lexical` arm reads **−3** here and **+7** in
`scripts/label_aware_groups.py`. They are **different arms with the same name**:
that script adds bucket features at the classifier *and* the ranker (`lgw`,
`lgmax`), this one adds them at the classifier only, to keep the four arms
differing in exactly one place each. The +7 is the stronger configuration and the
settled figure; the −3 says the classifier-only half of it is worth nothing.

Both are within the same few-article band, which is the point of the note either
way.

## What this settles

Twelve interventions were closed on `parent`. This adds a second relation, chosen
because it should have behaved differently, and it behaves the same. The claim is
now:

> The limit is the model class, on a relation with a diverse frame inventory
> **and** on one with a canonical frame, across a 2.3x range of baseline
> difficulty.

That is the strongest form available from inside the scope, and the remaining
route to testing it is the component the scope excludes.

## What would have refuted it

Features paying on `headquarters` — the claim would then have been about frame
diversity rather than about the model, and the fix would be inside reach. The
largest of six deltas across both relations is six articles.
