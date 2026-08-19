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

---

## From ordinal to cardinal (same day)

The limit this note recorded — *"it measures collisions, not consequences"* — was
the next thing to fix, and it turned out not to need dependency weighting at all.

**Two of the three collisions are settled by a rule that costs nothing to
compute.** A sentence-signature collision is real ambiguity only if the colliding
kinds also share a **role signature**:

| collision | spans | span share | permutable cases | cost |
|---|---:|---:|---:|---:|
| depot+flooded+needs | 141 | 0.124 | 40 | **0.625** |
| **bridge_on+link** | **520** | **0.456** | **0** | **—** |
| capacity+load_limit | 43 | 0.038 | 40 | **0.550** |

`link` carries `(a, b)` and `bridge_on` carries `(a, b, via)`. They are
indistinguishable in **text** — two regions, no number — and are flood's largest
collision, 456 of every thousand claim spans. They cost nothing, and not as a
measured accident: **there is nothing to permute.** A reader that recovers the
roles already has them apart, and the flow rebuilds bridges from the crossings
carrying limits.

That is worth stating precisely: the zero in that row is **structural, not
empirical**. The permutation never fires, which is why the table reports
`permutable = 0` rather than a cost of 0.000 measured over 40 cases. Reporting it
as a measured zero would claim evidence that was never gathered.

With the role-signature filter applied, flood reads **0.617 raw → 0.161 real**,
and the two remaining collisions are exactly the ones that hurt.

### Span mass is the wrong weight, and badly

The largest collision by mass costs nothing; the second smallest costs 0.550. Any
weighting by how *often* kinds collide would have ranked these exactly backwards.
`capacity`/`load_limit` is 3.8% of spans and over half the answer, because both
are answer-critical quantities and swapping them corrupts the load check.

### What this did not need

I expected to reach for the ablation-measured dependency sizes this repo already
computes. They were not necessary: **role signature** settles which collisions are
real, and direct permutation in the true world settles what the real ones cost.
Both are computable from the world and the surface with **no reader**, which is
the property that makes the audit worth having — an instrument that needed a
reader could not speak before one existed.

---

## The blind spot, closed (same day)

This note recorded that the audit *"sees only claim spans"*, and that solvency's
covenant threshold and determination date — prose the answer depends on — were
checked **by hand**, which is exactly what an instrument exists to stop.

Scoring every sentence, not only the ones realising claims, surfaces a second and
different failure: **prose that shares a signature with a real claim kind**. That
is not ambiguity between kinds, it is a false positive waiting to happen, because
a reader typing sentences by shape cannot see the span table.

Three flags across the three domains, and they resolve three different ways:

| domain | flagged prose | signature reads as | verdict |
|---|---|---|---|
| flood | *"A disused track once ran from X to Z"* | link, bridge_on | **real defect** |
| scheduling | *"machine_90 is withdrawn for maintenance"* | has_capability | neutralised |
| flood | *"The relief operation covers 6 districts"* | load_limit | false alarm |

- **Real.** Flood's reader admits **one spurious link in every one of 20 cases**
  — the disused track. That defect was found by hand earlier; the audit
  rediscovered it from the surface alone, without being told.
- **Neutralised.** Scheduling's reader admits **0 of 20**. Its capability
  vocabulary doubles as the distractor filter, exactly as flood's value registry
  does. That symmetry is worth naming: **in both domains the declared external
  knowledge does double duty — it settles signature collisions and it filters
  distractors.**
- **False alarm.** The audit counts any bare number; flood's reader requires the
  unit (`\d+ kg`), so it never sees "6 districts". **The audit's notion of a
  number is coarser than the reader's**, and it over-flags accordingly.

So the prose scan is a **risk register, not a defect list**. Each flag costs one
check against whatever declared knowledge the reader holds. That is a
substantially better position than the alternative, which was me reading the
generator and hoping I had noticed everything — and it caught a defect I had only
found the hard way.

Solvency, as predicted, collides with nothing: its threshold is *(no entity, one
money, no date)* and its determination date *(no entity, no money, one date)*, and
no claim kind occupies either. That is *why* reading them by shape works, and the
audit can now say so.
