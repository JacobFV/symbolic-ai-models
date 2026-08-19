---
title: An instrument that predicts where a reader will break, before the reader exists
date: 2026-08-19
status: measured
arm: signature-determinacy-audit
domains: flood, scheduling, solvency
---

## Turning three findings into a tool

Three measurements had converged on the same statement — structure is
load-bearing exactly where a sentence's **signature** does not determine its
**predicate**; the residual no content-free observable settles is exactly the
group the signature leaves open; and the content a reader needs is only for the
many-valued role inside that group.

That implies an instrument. For a **new** domain, do not build a reader and see
what breaks: compute, from the surface alone, which claim kinds share a sentence
signature. `symbolic_ai_generators/audit.py` does that in one pass over a
generated corpus.

## It reproduces both known answers

| domain | kinds | spans | ambiguity mass | measured behaviour |
|---|---:|---:|---:|---|
| flood | 9 | 1141 | **0.617** | collapses under interleaving, 1.000 → 0.000 |
| scheduling | 4 | 826 | **0.000** | immune, 1.000 → 1.000 |
| solvency | 2 | 437 | **0.000** | *prediction, no reader existed* |

Flood's mass decomposes into four collisions, and only one is irreducible:

| spans | signature | kinds | resolved by |
|---:|---|---|---|
| 520 | `(2x region; 0 num)` | bridge_on, link | structure — a pair carrying a limit is a bridge |
| **141** | `(1x region; 0 num)` | **depot, flooded, needs** | **nothing: the measured residual** |
| 43 | `(1 num; in capacity)` | capacity, load_limit | adjacency |
| *(raw only)* | `(1x truck; 1 num)` | capacity, mass | the value registry |

The last vanishes once the audit is given the reader's declared value
vocabularies, which is why it takes them: **a collision the reader can already
settle is not ambiguity.** Raw mass 0.860 → 0.617 with the registry supplied, and
the irreducible part is **141/1141 = 0.124** — exactly the group that breaks
under interleaving.

So the instrument is honest at the **ordinal** level and over-counts at the
cardinal one. Judging which collisions a declared mechanism resolves is still
human; ranking them by span mass, which is what the report does, is what makes
that judgement cheap.

## The prediction, and its test

Solvency audited at 0.000 **when it had no reader at all**. The instrument's
claim was therefore falsifiable: a signature reader should type every sentence
from its shape, and destroying arrangement should cost nothing.

`symbolic_ai_generators/solvency/read_surface.py` is that reader — the module the
domain had been missing, its published 1.000 having come from a script.

| V | as published | unsaturated | interleaved |
|---:|---:|---:|---:|
| 1 | 1.000 | 1.000 | **1.000** |
| 4 | 1.000 | 1.000 | **1.000** |

Answer accuracy and filing recall are both 1.000 in all six cells. **The audit
predicted structure-independence from the surface alone, and it held.**

## The result I nearly published instead

The first version of that reader scored **0.583** in all six cells. Identical
across V and across arrangement, which is exactly the signature of
structure-independence, and I had a prediction saying to expect it.

0.583 is solvency's **majority-class floor**. The reader was answering `False` on
all 60 cases.

The cause: solvency names its parent entity `group`, with **no number**, breaking
the `name_number` convention the other two generators use. An entity pattern
requiring the suffix silently dropped all 78 parent filings, so the consolidated
total was always short and the covenant always failed. The same bug was in the
audit's generic pattern, so solvency's 0.000 had been computed with one of its
two entity types invisible.

**Accuracy alone could not have caught this.** A constant predictor scores the
floor, and 0.583 reads as a plausible weak reader. What caught it in one line was
the **output distribution**: 60 `False`, 0 `True`, against a truth distribution of
35/25. That check is now `test_the_reader_is_not_answering_a_constant`.

Fixed, the reader reaches 1.000 with a distribution matching the truth exactly.

## Limits worth stating

- **The audit sees only claim spans.** Solvency's covenant threshold and
  determination date are prose, not claims, and the answer depends on both. They
  happen to have distinct signatures, so nothing was missed — but the audit would
  not have told me that, and I checked by hand.
- **It assumes a naming convention** unless given an entity pattern, which is how
  the `group` bug entered. The pattern is now an argument.
- **It measures collisions, not consequences.** A collision between kinds the
  flow treats identically (link/bridge_on) costs nothing; one on an
  answer-critical kind costs everything. Weighting by the ablation-measured
  dependency size, which this repo already computes, would turn ordinal into
  cardinal. Untried.

## What would refute this

A domain auditing at 0.000 whose reader nonetheless breaks under interleaving —
that would mean something outside sentence signature carries the reading, and the
instrument is incomplete. Solvency was the first real test of that and passed;
two confirmations and one prediction is not a law.
