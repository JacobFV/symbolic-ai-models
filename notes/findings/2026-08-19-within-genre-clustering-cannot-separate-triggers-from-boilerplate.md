---
title: Within-genre clustering cannot separate relation triggers from boilerplate — and that names what the fork actually needs
date: 2026-08-19
status: measured
arm: representation
---

Eight levers are closed on the real-text reader and supervision has been excluded
as the explanation, leaving the **representation**. The expensive form of that
hypothesis is a pretrained encoder, which the repo's scope keeps as a control.
This is the cheap form, and it needs nothing the repo lacks: **distributional word
clusters induced from the corpus itself** — co-occurrence over 2,502 intros, PPMI,
truncated SVD to 64 dimensions, k-means into 256 clusters, in numpy.

`runs/distributional_clusters.json`.

## It does not help

| arm | coverage | correct | precision | k/n |
|---|---|---|---|---|
| baseline (frames) | 0.306 | **0.116** | 0.378 | 207/1788 |
| + clusters | 0.300 | **0.109** | 0.362 | 194/1788 |

−0.007 on correct, and down on both other columns. Predicted a modest gain
(0.19–0.22 on the scale corpus's scale); measured a small loss.

## The cluster listing says why, and it is the same failure as WordNet

| word | cluster | its neighbours |
|---|---|---|
| **`subsidiary`** | 55 | `is, company, as, it, by, group, an, founded, corporation` |
| **`division`** | 55 | *(same cluster)* |
| **`owned`** | 55 | *(same cluster)* |
| `acquired` | 208 | `was, name, acquired, into, until, sold, assets, later, merged` |
| `unit` | 231 | `enterprise, unit, hp, newly, spun-off, lenovo, hewlett-packard` |

**The three highest-value triggers all landed in one cluster with `is`, `by`,
`an` and `company`.** Not with each other — *with the boilerplate*.

That is the **same failure WordNet produced, from the opposite end**. WordNet gave
`subsidiary` the category `noun.group` along with every group noun in the
language: too coarse because the resource is too general. Induced clusters put it
with `is` and `by`: too coarse because the *corpus* is too narrow. In company
intros, `subsidiary`, `owned`, `is` and `company` occur in near-identical
contexts — they are the genre's boilerplate, and distributional similarity is
exactly the thing that cannot separate words that share contexts by construction.

Two clusters *are* coherent — `acquired` with `sold`/`merged`/`assets`, `unit`
with `spun-off`/`hewlett-packard` — so the method works where the vocabulary is
varied. It fails precisely on the words that matter most.

## What this does to the fork

The fork has been stated four times as *"the evidence points at a learned
representation."* This narrows it:

> What is needed is not a learned representation. It is a representation
> **learned outside this corpus**.

Both cheap attempts failed for the same structural reason, at opposite ends of
the coarseness scale, and neither failure is fixable by tuning: WordNet cannot be
made corpus-specific and a 2.3 MB corpus cannot be made general. A pretrained
encoder is not merely a bigger version of what was tried here — it has seen
`subsidiary` in contexts where `is` does not appear, which is the one thing
neither of these had access to.

That is a sharper and more falsifiable claim than "we need an encoder", and it
carries a prediction: **any representation induced from this corpus alone will
fail the same way**, however it is induced.

## What would have refuted it

The clusters helping, or `subsidiary` clustering with `division` and `unit` rather
than with `is` and `by`. It clustered with the boilerplate, and the three most
valuable triggers landed together in the one cluster that cannot discriminate.
