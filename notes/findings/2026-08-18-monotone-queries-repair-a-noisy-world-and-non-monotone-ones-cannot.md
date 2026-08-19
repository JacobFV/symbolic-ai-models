---
title: Intersection raises a noisy extractor's precision from 36.5% to 95.1% — monotone queries repair an over-generated world, non-monotone ones cannot, and it is the same axis as the witness result
date: 2026-08-18
author: lead
status: provisional
tags: [extraction, metrics, monotonicity, composition, refuted-prediction, cost]
---

## The question

The previous finding measured that the extractor with the **worse** fact-level F1
builds the **better** world, and left an obvious hole: every query in it was a
set **union** over an inverted index, and unions reward over-generation almost by
construction. So "completeness wins" was either a general design rule or an
artefact of one query family.

Four classes chosen to punish over-generation, same two worlds, same 5,000 works,
same query instances handed to both.

## Result

| query class | | n | F1 | Jaccard | precision | recall | winner |
|---|---|---:|---:|---:|---:|---:|---|
| `works_at_both(A,B)` — **intersection** | v4 abstains | 3,000 | 0.309 | 0.176 | 98.7% | 18.3% | |
| | v4r high recall | 3,000 | **0.486** | 0.317 | **95.1%** | 32.6% | **completeness +0.177** |
| `common_institutions(w1,w2)` — intersection | v4 | 26 | 0.488 | 0.333 | 90.9% | 33.3% | |
| | v4r | 26 | **0.542** | 0.506 | 55.2% | 53.3% | completeness +0.055 |
| `institutions_unique_to(w1,w2)` — **difference** | v4 | 2,393 | **0.588** | 0.442 | 84.1% | 45.2% | **precision −0.117** |
| | v4r | 2,393 | 0.471 | 0.420 | 38.3% | 61.4% | |
| `is_single_institution(work)` — boolean universal | v4 | 3,000 | 71.7% acc | | | | floor 65.8% |
| | v4r | 3,000 | 75.1% acc | | | | floor 65.8% |

**I predicted precision would win on the intersective classes**, on the theory
that the noisy extractor's false positives are *correlated siblings* — the
thirteen University of Wisconsins — which would survive intersection. Wrong, and
wrong about the mechanism.

## Intersection is a noise filter, and it is a very good one

Track the high-recall extractor's precision as the query gets more constrained:

```
fact level   institutions_of(work)          36.5%
union        collaborators(institution)     44.0%
union        works_at(institution)          67.6%
INTERSECT    works_at_both(A,B)             95.1%     <-
DIFFERENCE   institutions_unique_to(w1,w2)  38.3%
```

**36.5% → 95.1%.** The false positives are uncorrelated enough between two
independently extracted sets that intersecting removes almost all of them. So the
**query performs the disambiguation the extractor refused to perform**, and
over-generation is close to free when the workload intersects.

That is a stronger and more useful statement than the one it replaces: it is not
that completeness is worth its precision cost, it is that **a constrained query
recovers the precision**.

## The exception names the axis

The one class where precision wins is the **set difference**, and it is not a
coincidence — it is the only non-monotone query in the set:

| query | monotone in its inputs? |
|---|---|
| `A ∪ B` | monotone |
| `A ∩ B` | monotone |
| `A − B` | monotone in `A`, **antitone in `B`** |
| `\|A\| == 1` | non-monotone |

A spurious member of `B` **deletes a true member of `A`**, and nothing downstream
can recover it — which is exactly what the numbers say: v4r's precision on the
difference is **38.3%**, essentially the raw fact-level rate, **unfiltered**.

> **Monotone queries tolerate and even repair over-generation. Non-monotone
> queries cannot.**

## Why this matters beyond the query family

This is **the same axis as the witness finding**, in a different part of the
programme. There: an existential, monotone claim (`a cover of size k exists`) had
a small stable certificate, and its universal complement (`no smaller cover
exists`) had none, and the gap was 95x. Here: monotone queries survive a
half-wrong world, and the antitone one does not.

Two unrelated arms, one axis. That is now worth treating as a property of the
substrate rather than as two observations.

**The design consequence, sharpened twice in two days:**

- not *"completeness wins"* (the previous finding),
- not *"completeness wins for existential queries"* (what I expected here),
- but **"the extraction operating point should be chosen by the monotonicity of
  the workload"** — and a system serving mixed workloads may genuinely need both
  worlds, which nothing in the architecture currently expresses.

## What would refute it

- **`common_institutions` has n = 26.** Random work pairs almost never share an
  institution. That row is reported because it agrees with the reliable
  intersection row, and it should carry no weight on its own.
- **The boolean universal is inconclusive.** 71.7% and 75.1% against a 65.8%
  majority floor. It is non-monotone and completeness won it, which is the one
  result inconsistent with the rule — at a margin that does not clear the floor
  by enough to argue with.
- **Two operating points, not a curve.** As before, v4 and v4r bracket a range
  and the interior was not searched.
- **One corpus, one extractor family, and the anchor is agreement with
  OpenAlex**, not truth.
- **The filtering claim assumes error independence between two sets.** It held
  here at 95.1%; a corpus where the same wording recurs across the works being
  intersected would correlate the errors and the filter would fail. That is a
  cheap experiment — intersect works that *share* an affiliation string — and it
  is the sharpest thing anyone could do to this finding.

## Reproduce

```bash
SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \
  uv run python -u scripts/completeness_limit.py
```

`runs/completeness_limit.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `where-completeness-stops-winning`.
