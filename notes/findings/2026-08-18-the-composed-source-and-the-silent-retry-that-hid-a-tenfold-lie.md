---
title: The composed WordNet+CSKG source gains a section on 17.9% of topics — matching the 16.9% predicted before it was built — and a silent TypeError retry first reported 92.7%
date: 2026-08-18
author: lead
status: provisional
tags: [knowledge-source, federation, composition, lesson]
---

## What was built

`symbolic_ai_kg.composed.ComposedGraph`: WordNet supplemented by CSKG through a
lemma join, behind one accessor set. Three of this repo's standing rules stop
being abstract in it at once.

**Identity is a claim, not a merge.** The join is an `Alignment` with relation
`possibly_same` and confidence 0.6 — not `exact_match`, because `dog` in WordNet
is a *synset* and in this CSKG projection is a lemma-collapsed concept that
already merges senses. Node ids stay in the primary's space throughout, so
nothing downstream ever sees two id spaces.

**CSKG contains WordNet 3.0**, so an edge in both is one observation seen twice.
Every accessor deduplicates the supplement against the primary and counts what it
dropped.

**A composed source is an artifact**, and its licence closure is `share_alike`:
CSKG is CC-BY-SA-4.0 and WordNet is not.

## Prediction, before it was built

Measured in advance from the raw join and recorded in
`notes/questions/2026-08-18-the-composed-source-would-gain-a-section-on-17-percent.md`:
**16.9% of WordNet's rich topics gain a section**, and the drawn rate matches the
pool rate because sampling is uniform.

## Measured, over WordNet's own 1,074 rich topics

| section | wordnet | composed | delta |
|---|---|---|---|
| placement | 0.141 | 0.274 | **+0.133** |
| varieties | 0.706 | 0.714 | +0.008 |
| composition | 0.088 | 0.102 | +0.015 |
| substance | 0.009 | 0.010 | +0.001 |
| membership | 0.003 | 0.003 | +0.000 |
| **qualities** | **0.000** | **0.070** | **+0.070** |
| **behaviour** | **0.000** | **0.054** | **+0.054** |
| contrast | 0.967 | 0.972 | +0.005 |

**Gain at least one section: 0.179**, against 0.169 predicted. The two sections
WordNet populates *nowhere* are now populated, which was the point.

Composite double-count rate: **5.1%** — against my stated prediction of 20–50%.
The guard fires and the effect is small, and the reason is specific: the vendored
CSKG here is a **selectional projection** that kept ConceptNet's relations rather
than WordNet's, so the two barely overlap even on shared lemmas. The warning on
`catalog/sources/cskg.yaml` is right in principle and this instance is mild. That
says nothing about the full CSKG, which genuinely does contain WordNet 3.0.

## The bug, which is the more useful half

Before the fix, the same measurement reported **composition 0.088 → 0.988** and
**92.7% of topics gaining a section**. Both were fictional.

`essay.gather` calls its accessors as `acc(topic, inherited=False)` — the
difference between a *directly stated* fact and one inherited down the hypernym
chain, and `gather`'s own docstring explains that drawing from the inherited set
makes the essay state the very fact its synthesis paragraph claims is unstated.
My wrapper took only `(self, n)`. So `gather` raised `TypeError`, **swallowed it,
and retried without the keyword** — and the composed source silently answered a
different question from the source it stands beside, returning the inherited
closure and reading as a tenfold improvement.

Two things made it invisible and only one of them is mine:

- the wrapper did not forward keywords (mine);
- `gather` has a bare `except TypeError` retry, which is precisely the *silent
  fallback* this repo's engineering rules forbid — "one correct path per
  operation; a silent fallback is how a broken component reads as a working
  one". It was written to tolerate sources with narrower accessors, and it
  tolerated a broken one instead.

Not every accessor takes the keyword — `hypernyms(n)` does not, `parts_of` does —
so the fix is signature-aware forwarding against the **primary**, so the composed
source accepts exactly what the primary accepts and no more.

## The invariant that catches it, now a test

> **An unaligned topic must produce exactly what the primary produces.**

655 of the 1,074 rich topics have no CSKG counterpart at all. With nothing to
supplement, any difference is the composition changing the *question* rather than
enriching the answer. Before the fix, all 655 disagreed; after it, none do.

That check costs one comparison and would have caught the bug the moment it was
written. It is the composition analogue of the substrate's other identity guards,
and the general form is worth carrying: **for any wrapper that supplements, the
no-op case must be exactly the identity.**

## What would have refuted it

- **A prediction registered after the fact.** The 16.9% was measured and written
  down before the class existed, in a question note, from the raw lemma join.
- **The gain coming from the bug.** The 0.179 is post-fix; the pre-fix number was
  0.927 and is reported above as the error it was.
- **Losing what WordNet had.** Asserted monotone over 200 topics and all eight
  sections through `gather`.
