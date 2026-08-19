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

## 3. The representation was the problem, not only the corpus

Heaps' law fitted on the corpus itself, by subsampling to a quarter, a half and
all of it. Distinct frame *types* against frame *instances*, `V ≈ K·n^β`:

| relation | representation | types | singletons | top-5 share | mean count | **β** |
|---|---|---|---|---|---|---|
| `parent` | full token path | 102 | 0.912 | 0.179 | 1.21 | **0.830** |
| | last 2 tokens | 67 | 0.776 | 0.390 | 1.84 | 0.700 |
| | **last content word** | 58 | **0.741** | **0.463** | **2.12** | **0.641** |
| | content bag | 96 | 0.927 | 0.244 | 1.28 | 0.847 |
| `headquarters` | full token path | 59 | 0.966 | 0.260 | 1.24 | 0.933 |
| | **last content word** | 29 | 0.793 | **0.658** | **2.52** | **0.702** |
| `country` | full token path | 86 | 0.942 | 0.264 | 1.28 | 0.920 |
| | last content word | 74 | 0.905 | 0.355 | 1.49 | 0.921 |

**β near 1 means the inventory grows as fast as the data**, so no corpus makes
those frames repeat — for `parent`'s full paths, reaching a mean count of five
would need on the order of 10⁹ instances. A typical word vocabulary has β ≈ 0.5.
Dropping to the **last content word before the mention** takes `parent` from 0.83
to **0.64** and `headquarters` from 0.93 to **0.70**: same corpus, same
sentences, a representation that repeats and therefore one that scale can help.

`country` does not improve, and the reason is visible in the data: a country is
usually written adjacent to a city — *New Delhi, India* — so there is no lexical
trigger to key on at all.

Rebuilding the frame features on content words, in the classifier and the ranker:

| relation | correct | precision |
|---|---|---|
| `parent` | 0.101 → **0.113** | 0.246 → 0.271 |
| `headquarters` | 0.173 → **0.216** | 0.412 → **0.507** |
| `country` | 0.145 → **0.163** | 0.375 → 0.403 |

Every relation up on both columns, +12% to +25% relative. The first movement in
six interventions, and it came from measuring the repeat rate rather than from
adding another feature source.

## 4. The prediction this makes, and how it will be checked

If frames are Zipfian, distinct types grow **sublinearly** in tokens (Heaps' law,
`V ≈ K·n^β` with β typically 0.7–0.8), so an order of magnitude more articles
should raise the head's share and drop the singleton fraction.

`data/artifacts/wikipedia_parents_scale.jsonl` is being fetched (~1,500 articles,
behind a Wikidata 429 backoff). §3 **supersedes the prediction registered before
it was measured**, which was that full-path singletons would fall to 0.75–0.85 at
ten times the data. With β = 0.83 they will not: types grow 10^0.83 = 6.8x
against 10x the instances, so the mean count rises only 1.21 → 1.47. That
prediction is expected to fail and is left on the record.

The corrected one, from the fitted exponents:

- **full-path** frames stay sparse — `parent` singleton share above 0.85, mean
  count below 1.6. Scale does not rescue this representation.
- **content-word** frames do scale: types grow 10^0.64 = 4.4x against 10x the
  instances, so mean count rises 2.12 → **≈4.8** and the top-5 share should pass
  0.55.
- `parent` correct with content-word frames **0.113 → 0.20–0.30**, and
  `headquarters` **0.216 → 0.30–0.40**.
- `country` moves least, because its frames are adjacency rather than lexis.

If the content-word exponent also comes out near 1 on the larger corpus, the
sublinearity is an artefact of 168 articles and scale is not the lever.

## What would have refuted the reading

Any of the five interventions moving `parent`. One moved `headquarters` and none
moved `parent`, which is the pattern a frame-sparsity explanation predicts and a
feature-quality explanation does not.
