---
title: A relation frame occurs once and never again — 91% singletons, and five fixes that changed nothing
date: 2026-08-19
status: measured
arm: real-text-reader
---

The distant-supervision arm left `parent` at **0.101** correct against four hand
patterns at 0.393, and diagnosed the constraint as volume. This is the mechanism,
and it is arithmetic rather than intuition.

## 1. Five interventions, one number

| intervention | `parent` correct |
|---|---|
| n-gram features (baseline) | **0.101** |
| + multi-instance pruning | 0.042 |
| + WordNet supersenses | **0.101** |
| + frame features on the classifier | **0.101** |
| + negative-class down-weighting, chosen by inner CV | **0.101** |
| + frame features on the **ranker** | **0.101** |

Five feature and weighting changes, and `parent` does not move by one article in
168. The invariance is the evidence: whatever sets this number, none of these
touch it. Two of the five *did* move other relations — role frames took
`headquarters` from 0.173 to **0.198** with precision 0.412 → **0.500** — so the
machinery works and the relation is the difference.

The negative-class weight is worth noting separately: inner 3-fold CV on the
training articles chose **1.0**, no down-weighting, in every outer fold. The
reader emits 0.54 `parent` claims per document and its oracle over its own
proposals is 0.107 against an argmax of 0.101 — **it is not mis-ranking, and it
is not fixable by making it fire more.**

## 2. The mechanism: the surface forms are nearly all unique

Taking the token path between the gold filler and the mention before it, over
every distantly supervised sentence in the corpus:

| relation | instances | distinct frames | top-1 share | top-5 share | **singleton frames** |
|---|---|---|---|---|---|
| `parent` | 123 | 102 | 0.106 | 0.179 | **0.912** |
| `headquarters` | 73 | 58 | 0.110 | 0.274 | **0.948** |
| `country` | 110 | 86 | 0.182 | 0.264 | **0.942** |

**A frame appears once and never again in 91–95% of instances.** `parent`'s 123
examples are spread across 102 distinct realisations, of which the most common
non-adjacent one — `is a subsidiary of` — occurs three times. There is almost
nothing here to generalise from, whatever the feature set, and that is why five
different feature sets produce the same number.

It also explains the hand reader precisely. Its four patterns
(`is a subsidiary of`, `owned by`, …) sit at the head of a very long tail. A
classifier cannot find the head because in a 168-article corpus the head is three
occurrences and the tail is a hundred singletons; a person can, because they
already know which phrasings English uses for ownership. **That is what "prior
knowledge substitutes for data" means quantitatively.**

`headquarters` responds to frames where `parent` does not for the same reason
read forwards: its top-5 share is 0.274 against `parent`'s 0.179, because a
headquarters is stated in a near-canonical frame (*headquartered in X*, *based in
X*) and a corporate parent is stated fifty ways.

## 3. The prediction this makes, and how it will be checked

If frames are Zipfian, distinct types grow **sublinearly** in tokens (Heaps' law,
`V ≈ K·n^β` with β typically 0.7–0.8), so an order of magnitude more articles
should raise the head's share and drop the singleton fraction.

`data/artifacts/wikipedia_parents_scale.jsonl` is being fetched (~1,500 articles,
behind a Wikidata 429 backoff). Registered before it lands:

- `parent` singleton frame share **0.912 → 0.75–0.85**;
- `parent` top-5 frame share **0.179 → 0.30–0.45**;
- `parent` correct **0.101 → 0.18–0.28**.

**If the singleton share does not fall, more text will not help**, the frames are
not Zipfian at this granularity, and the whole "scale the corpus" direction is
wrong — which would be the most useful thing this corpus could say.

## What would have refuted the reading

Any of the five interventions moving `parent`. One moved `headquarters` and none
moved `parent`, which is the pattern a frame-sparsity explanation predicts and a
feature-quality explanation does not.
