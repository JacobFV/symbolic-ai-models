---
title: Intersection raises a noisy extractor's precision from 36.5% to 95.1% on independent errors and drops it to 8.1% on correlated ones — monotone queries repair uncorrelated over-generation only, which is free exactly where disambiguation is not needed
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

> **Read the CORRECTION below before quoting anything in this section.** The
> 95.1% holds only for *independent* errors. On registry-confusable pairs the
> same query gives **8.1%**, and this section as written overstates the result.

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
> queries cannot.** — *narrowed by the correction below to: monotone queries
> repair **uncorrelated** over-generation.*

## Why this matters beyond the query family

This is **the same axis as the witness finding**, in a different part of the
programme. There: an existential, monotone claim (`a cover of size k exists`) had
a small stable certificate, and its universal complement (`no smaller cover
exists`) had none, and the gap was 95x. Here: monotone queries survive a
half-wrong world, and the antitone one does not.

**ATTRIBUTION, corrected after the fact.** I wrote here that this was "two
unrelated arms, one axis … now worth treating as a property of the substrate
rather than as two observations". It is **four**, and two of them **predate this
session**:

- `2026-08-18-inspectability-is-asymmetric-the-witness-is-247x-cheaper-and-optimality-costs-double.md`
  — same route network, same framing: witness verification **247x cheaper** than
  solving, optimality certificate **2.0x more expensive** than re-solving.
- `2026-08-18-a-datalog-witness-verifies-flat-while-solving-grows-and-most-of-the-ratio-was-my-engine.md`

And `symbolic_ai_kernels/datalog/proof.py` poses as its **stated open question**
exactly what the witness finding answered: *"whether that shape is a property of
shortest path or of the existential/universal distinction itself"*.

So the axis is not new here and this finding does not discover it. What is new
is that it shows up **in a place with no proof and no certificate at all** —
plain set queries over a noisy world — which is evidence that it is a property of
the *claims*, not of the verification machinery. That is the better claim and it
is the one that answers the question `proof.py` asked. Lesson recorded at
`notes/lessons/2026-08-18-i-claimed-an-axis-was-new-and-the-repo-had-measured-it-twice.md`.

**The design consequence, sharpened twice in two days:**

- not *"completeness wins"* (the previous finding),
- not *"completeness wins for existential queries"* (what I expected here),
- but **"the extraction operating point should be chosen by the monotonicity of
  the workload"** — and a system serving mixed workloads may genuinely need both
  worlds, which nothing in the architecture currently expresses.

## CORRECTION, run immediately: the filter needs independent errors, and 8.1%

The section above names its own falsifier — *"the filtering claim assumes error
independence; a corpus where the same wording recurs across the works being
intersected would correlate the errors and the filter would fail"* — so it was
run rather than left for someone else.

Define **confusable**: two ROR ids that a single registry name maps to together.
That is exactly the correlation at issue, and **4,604 institutions have at least
one such sibling**. Partitioning `works_at_both(A,B)` by it:

| institution pair | n | **precision** | recall | F1 |
|---|---:|---:|---:|---:|
| co-occurring — **as published above** | 3,000 | **95.1%** | 32.6% | 0.486 |
| **CONFUSABLE** (correlated errors) | 800 (356 non-empty) | **8.1%** | 57.7% | 0.143 |
| unrelated | 800 (only 9 non-empty) | 30.0% | 27.3% | 0.286 |

**95.1% → 8.1%**, which is not merely a collapse but a fall *below* the 36.5%
fact-level rate. I predicted 40–70%.

**So the 95.1% is real and is not a property of intersection.** It is a property
of intersecting *independent* things. The pairs it was measured on were sampled
from institutions that **actually co-occur** — genuine collaborators, which are
overwhelmingly not registry siblings. On confusable pairs, intersection
**amplifies** the noise instead of filtering it, because the extractor puts all
thirteen Wisconsins on every Wisconsin work and every one of them then
co-occurs with every other.

> **Intersection repairs uncorrelated over-generation and amplifies correlated
> over-generation — and the extractor's noise is correlated with precisely the
> entities anyone would want disambiguated. Over-generation is close to free
> where you do not need disambiguation, and ruinous where you do.**

The monotonicity result stands; the *scope* of "repair" does not. Read the rule
as **monotone queries repair independent noise**, and check the correlation
structure of the workload before relying on it.

### A slip worth recording

My first attempt at this falsifier **tested the wrong query**. I partitioned work
pairs by shared affiliation *string* and measured `common_institutions(w1,w2)` —
intersecting two works' institution sets — when the 95.1% came from
`works_at_both(A,B)`, which intersects two institutions' *work* sets. Two
different intersections carrying the same word. It returned 43.7% against 33.8%,
a null, and I nearly recorded it as one. The partition that matters is registry
**confusability of the institution pair**, and it gives 8.1%.

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
- ~~The filtering claim assumes error independence.~~ **Run — see the correction
  above. It does, and the filter fails at 8.1%.**
- **The unrelated-pair row is uninformative**: only 9 of 800 pairs have a
  non-empty true answer, because two randomly chosen institutions almost never
  co-occur. It is reported to show that, not as evidence.

## Reproduce

```bash
SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \
  uv run python -u scripts/completeness_limit.py
```

`runs/completeness_limit.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `where-completeness-stops-winning`.
