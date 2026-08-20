---
title: A model-free screen can prove a relation impossible, never feasible — twice now
date: 2026-08-19
status: measured
arm: relation-readability
---

The prospective test named two omissions in the triage set — no floor, no base
guard on the positional ratio — and the result exposed a third the predictions had
not considered: `owned_by` has **containment 0.538**, as high as `parent`, and
reads at 0.058, below its floor. Its gold values are institutional shareholders
(`BlackRock`, `The Vanguard Group`) that appear in these articles for reasons
other than ownership. **False containment**: the string is present and the
sentence does not state the relation.

All seven relations, every statistic model-free:

| relation | floor | containment | stating sents | top-5 | positional | **clears floor?** |
|---|---|---|---|---|---|---|
| `parent` | 0.010 | 0.592 | 1843 | 0.436 | 1.7x | **yes** (0.144) |
| `country` | 0.298 | 0.579 | 2507 | 0.414 | 3.3x | **yes** (0.390) |
| `headquarters` | 0.045 | 0.551 | 1843 | 0.714 | 4.8x | **yes** (0.280) |
| `founder` | 0.006 | 0.424 | 604 | 0.368 | 2.8x | **yes** (0.096) |
| `industry` | 0.061 | 0.241 | 762 | 1.000 | 5.9x | **yes** (0.238) |
| `legal_form` | 0.116 | **0.050** | **113** | 0.714 | *(base too small)* | **no** (0.113) |
| `owned_by` | 0.060 | 0.538 | 1181 | 0.432 | 1.8x | **no** (0.058) |

## One comparison catches `legal_form`, and it needs no proposer

**`containment < floor` ⇒ the relation cannot clear its floor**, whatever the
model. `legal_form` states its value verbatim in **0.050** of articles against a
floor of **0.116**: even a perfect reader of every stated instance loses to
answering *joint-stock company* every time. One comparison, two model-free
numbers, decisive — and it fires on exactly one of seven relations, with no false
alarms among the five that clear.

The base guard fires on the same relation for the same underlying reason: 113
stating sentences is too few for a positional ratio to mean anything, and 113 is
small *because* containment is 0.050.

## And nothing catches `owned_by`

Its containment is 0.538, its proposal is fine, its base is 1181, and its frame
concentration is **0.432 — indistinguishable from `parent`'s 0.436**, which
achieves +0.134 above floor where `owned_by` achieves −0.002.

**Frame concentration does not detect false containment.** That statistic already
failed once as a predictor of readability; this is its second failure, on a
narrower claim, and it should not be tried a third time.

## The pattern across two diagnostics

The lexicon-gap diagnostic proved one-sided: a large gap proves a lexicon problem,
a small gap proves nothing, because suppletive derivations are invisible to
morphology. This screen is one-sided the same way:

> **A model-free screen can prove a relation impossible. It cannot prove one
> feasible.** `containment < floor` is a sound rejection; passing it means only
> that no cheap statistic objects.

That is a real and usable property — rejections are what save work — and it is
also the ceiling on the whole triage idea. Five of seven relations pass the screen
and clear their floor; one is correctly rejected; one passes and fails anyway, and
no model-free statistic in the set sees it coming.

## What is left for `owned_by`

The failure mode is a **stating rate far below the containment rate**, and the
only way found to measure that is to read the sentences — which is the thing being
screened for. A cheap detector would need to ask whether the *contexts* of the
gold occurrences look like statements of the relation, and frame concentration was
the obvious candidate and does not work.

## What would have refuted this

`containment < floor` firing on a relation that clears its floor. It fires once in
seven, on the one relation that does not.
