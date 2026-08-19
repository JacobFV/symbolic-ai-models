---
title: Entropy was the wrong statistic, and the numbers said so
date: 2026-08-19
status: measured
arm: signature-bits-on-real-text
---

## The question, and the measurement that could not answer it

The signature-determinacy audit is this repo's most load-bearing instrument —
credited with predicting reader difficulty, where error concentrates, payback and
maintenance. It has only ever been computed on surfaces **built to make
signatures computable**: entities are `region_0`, `machine_3`, `sub_2`, and each
claim kind was given a shape of its own.

So: how much does a sentence signature tell you about English nobody here wrote?
I reached for **entropy**, because it needs no labels.

| population | sentences | distinct signatures | bits | top bucket |
|---|---:|---:|---:|---:|
| flood (generated) | 2,555 | 8 | 2.59 | 0.352 |
| scheduling (generated) | 1,836 | 5 | 2.26 | 0.261 |
| solvency (generated) | 1,194 | 8 | 2.61 | 0.276 |
| **abstracts (openalex)** | 36,223 | **482** | **3.65** | 0.442 |
| narrative (gutenberg) | 75,555 | 77 | 2.06 | 0.469 |

**Real abstracts carry more signature entropy than any generated surface.** That
was my stated refutation condition, and it fired.

It is also not the answer to the question. **Entropy says how much a signature
varies, not how much it determines.** Determinacy is a property of the *joint*
distribution of signature and predicate; a population can have arbitrarily high
signature entropy and zero determinacy. Entropy needs no labels — which is
exactly why it cannot answer the question labels are for. I reached for it
because it was computable, which is the wrong reason to choose a statistic.

## What survives, and it is exact where it can be

The quantity that matters is **how many predicates share a bucket**. On the
generated surfaces the spans carry their kind, so this is exact:

| generated surface | top bucket | kinds in it | ambiguity mass |
|---|---:|---:|---:|
| flood | 0.455 | **2** | **0.860** |
| scheduling | 0.291 | **1** | **0.000** |
| solvency | 0.509 | **1** | **0.000** |

*(flood's 0.860 is the known raw figure, reproduced here as a check.)*

**A bucket can be huge and hold one kind — that is what a determinate surface
looks like.** Solvency's biggest bucket holds half of all its claim spans and
still reads 0.000, because every sentence in it realises `owns`.

On real prose the same bucket is not like that. The largest signature in **both**
corpora is the **empty** one — no recognised entity, no number, no date — and it
holds **15,996 of 36,223** abstract sentences (44.2%) and **35,413 of 75,555**
narrative sentences (46.9%). Four of them, unedited:

> *This system has contributed to safe operation during two experimental
> campaigns…*
> *Thanks to the optimization, significant extension of the lifetime of the
> cameras has been realized.*
> *Improvements over PW91 include an accurate description of the linear
> response…*
> *To attack the first is not to assail the last.*

Those are `contributed_to`, `was_realised`, `includes`, `is_not`. If the largest
bucket holds more than one predicate then every sentence in it is ambiguous, so
**ambiguity mass on real prose is at least 0.44** — against the **0.000** that
scheduling and solvency post, and 0.000 is the reading the repo uses to argue a
content-free reader can work.

## The structural argument, which does not depend on my entity detector

The detector is crude in both directions: it over-counts ordinary capitalised
words and under-counts alphanumeric acronyms (`PW91`), lowercase entities,
definite descriptions and pronouns. A better one moves sentences between buckets.

It does not change the reason those sentences share a bucket. **A signature over
(entity counts, numbers, dates) never looks at the verb**, and the verb is where a
real predicate lives. No named-entity recogniser makes *contributed to*, *is
realized* and *include* distinguishable by shape. Signature determinacy is a
property of surfaces whose claim kinds were **given** distinct arities — which is
what these three were.

## What would refute this

- The 0.44 floor assumes the empty bucket holds ≥2 predicates. That is
  demonstrated by four sampled sentences, not proved, and it is the kind of claim
  a reader should check rather than accept.
- Two genres. A corpus of highly stereotyped text — a filings boilerplate section,
  a clinical report — could have far lower real ambiguity mass, and that is the
  interesting case for this repo because it is what the domains imitate.
- The generated rows use no value registry, so 0.860 is flood's *raw* mass; with
  its registry and the role-signature filter it reads 0.161. The comparison above
  is raw against raw.
