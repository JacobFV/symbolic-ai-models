---
title: Each fix moves the binding constraint rather than the number — and the query earns its place in the formalism
date: 2026-08-19
status: measured
arm: real-text-scale
---

The scale result named the ranker as the new binding factor: ten times the text
took classifier recall 0.256 → 0.395 and *dropped* role assignment 0.556 → 0.400,
capping the product at `0.594 × 0.400 = 0.238` however much text arrives. This
attacks the ranker and watches what becomes binding next.

## Two features, both document-level, neither a pattern

Role assignment had only sentence-local evidence: a candidate's index, the words
either side, the content-word path. What it could not ask is **what the document
is about** — and the entity a relation points at is never that one. An article
titled *Sony Music* states a parent, and the parent is not Sony Music.

1. **Document statistics.** Every mention in the intro with its frequency:
   `is.subject`, `docfreq`, `rank`, `hapax`. The subject is guessed as the
   commonest mention.
2. **The query.** `Reader.run(text, query=...)` already existed in the ABI and
   nothing used it. The title is passed through and the subject is *known*
   rather than guessed. It is document metadata, not an annotation, and every
   document has one.

| arm | classifier recall | **ranker** | correct | precision |
|---|---|---|---|---|
| sentence-local only | 0.395 | **0.400** | 0.175 | 0.365 |
| + document statistics | 0.395 | **0.467** | 0.179 | 0.373 |
| **+ the query** | 0.395 | **0.533** | **0.182** | **0.379** |

**Role assignment improves 33% relative**, and guessing the subject from
frequency recovers only half of what knowing it does — frequency picks *India*
over *India Post*.

This is the first place `Q` in `P(Y | Z, Q)` has paid rent in an implementation
rather than a note. It is not the task-quotient use the formalism was written
for; it is smaller and more useful: **the query names an entity, and naming an
entity is evidence about every role that could point at it.**

## And the number barely moves

`parent` correct: **0.175 → 0.182**. Ten times the text bought +55%; fixing the
ranker bought +4%.

The reason is in the same table: with the ranker at 0.533 the **classifier is
binding again** at 0.395. The constraint has alternated twice —

| | classifier | ranker | binding |
|---|---|---|---|
| 168 articles | 0.256 | 0.556 | classifier |
| 1,661 articles | 0.395 | 0.400 | **ranker** |
| + document and query features | 0.395 | 0.533 | **classifier** |

— and the product ceiling has moved 0.143 → 0.238 → **0.317**, which is what
actually improved. The measured 0.182 sits above the product because
document-level aggregation over several sentences recovers some of what any
single sentence loses.

## What this says about where effort goes

**Neither factor is the bottleneck; the alternation is.** A fix to whichever is
currently binding buys a few points and hands the constraint to the other, so
single-factor work has a low ceiling and the honest planning quantity is the
*product* — which is why it is reported here beside the accuracy.

To pass the hand reader's 0.393, with the ceiling fixed at 0.594, the product of
the other two must reach 0.66. From 0.395 × 0.533 = 0.21 that is a **3.1x** joint
improvement, and the extrapolated text requirement (1.54x classifier recall per
decade) is 10⁵–10⁶ articles *if the ranker holds*, which it did not last time
scale arrived.

## What would have refuted it

The query feature not helping — the subject is guessable from frequency, and if
that guess were as good as the title the ABI's `query` port would be decoration.
It recovers about half: 0.400 → 0.467 guessed, 0.533 known.

## Two more levers, both closed at scale

With the classifier binding again, the two cheapest remaining ideas were tested
on the 1,661-article corpus and both are dead.

**Class balancing.** The classifier abstains on most sentences and the negative
class outnumbers `parent` ten to one, so down-weighting `NONE` is the textbook
fix. Inner 3-fold cross-validation on the *training* articles chose a `NONE`
weight of **1.0 — no down-weighting — in every one of the four outer folds**, at
both corpus sizes. Tested twice, ten times apart in data; it is not the lever.

**Answer aggregation.** The measured accuracy sits above the factor product, so
document-level pooling recovers something and a better pool might recover more:

| rule | correct | precision |
|---|---|---|
| argmax belief | 0.185 | 0.385 |
| modal candidate | 0.183 | 0.380 |
| belief-weighted vote | 0.185 | 0.385 |
| **oracle over its own proposals** | **0.197** | 0.410 |

The oracle is only **0.012** above argmax, because the reader emits **0.60
proposals per document** — in most documents there is exactly one candidate and
nothing to aggregate. No selection rule can win more than a point here.

So the levers tried and closed on this arm now number six: multi-instance
pruning (worse), WordNet supersenses (nothing), frames on the classifier
(nothing), class balancing (nothing, twice), answer aggregation (0.012), and
frames on the ranker (+33% on the ranker, +4% end to end). The two that moved the
number were **ten times the text** (+55%) and **the query** (+4%).

What is left is the sentence representation itself: whether a sentence states a
relation, decided from features rather than from a model of the sentence. That is
the same conclusion the threshold arm reached from the other side, and it is now
supported by six closed alternatives rather than by preference.
