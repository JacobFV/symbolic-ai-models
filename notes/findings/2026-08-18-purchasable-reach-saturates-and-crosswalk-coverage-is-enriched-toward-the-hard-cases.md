---
title: 2,383 rows answer 68.8% of $51.4T and 2,281,221 rows answer 75.0% — purchasable reach saturates, and crosswalk coverage is enriched 1.33x toward exactly the entities names cannot settle
date: 2026-08-18
author: lead
status: provisional
tags: [federation, reach, crosswalk, cost, retraction, refuted-mechanism]
---

## Where this sits

The programme's bottleneck is **reach, not reasoning**, and reach was split into
*purchasable* and *structural*. This measures the purchasable half and finds it
**saturates almost immediately** — which changes what acquiring data is worth,
and it does so in the direction of *less spending*, not more.

It also retracts a published negative. `notes/findings/2026-08-18-the-advantage-is-a-property-of-provenance-463x-filed-against-18x-derived.md`
asserted **"no file on disk links a CIK to an LEI"**. False; see the retraction
appended to that note and `notes/lessons/2026-08-18-i-searched-for-the-mechanism-and-the-file-was-named-after-its-purpose.md`.

## 1. The bridge exists, and it is enriched toward the hard cases

`data/sources/wikidata/.../idbridges_full_p0.parquet`: 69,679 `same-as` edges
out of the wikidata namespace, targeting **lei 53,198 / isin 9,936 / sec 3,660 /
asx 2,846 / ticker 39**. **2,113** wikidata entities carry both a `sec` and a
`lei` edge — an identifier join at both ends, not a name join.

`scripts/wikidata_bridge_cik_lei.py`:

| | | |
|---|---:|---|
| coverage, all SEC filers | 15.3% | 1,226/8,021 |
| coverage, **matched** filers | **24.9%** | 1,015/4,078 — the denominator that composes |
| ambiguity among **bridged** | **19.5%** | 198/1,015 |
| ambiguity among **unbridged** | 13.1% | |
| base rate (published) | 14.7% | 598/4,078 |
| **enrichment** | **1.33×** | z = 5.03, p = 4.8e-07 |

The published 14.7% is over *matched* filers, so coverage had to be measured over
matched filers too; the 15.3% over all 8,021 is a different denominator and
composing the two would have repeated this repo's oldest arithmetic error.

### The correction that generalises

`scripts/bridged_join.py` priced the composite as `f = (1 − coverage) × f_name`
— **the product of the marginals**, which assumes coverage is independent of
join difficulty.

| policy | `f` | advantage |
|---|---:|---:|
| name join alone | 14.66% | 6.8× |
| independence estimate (published) | 11.01% | 9.1× |
| **measured joint** | **9.81%** | **10.2×** (1.49× over names alone) |

> **Crosswalk coverage is enriched toward exactly the entities a name join
> cannot settle, so `(1 − coverage) × f_name` underprices a crosswalk** — here by
> 10.9% of itself. The mechanism is that a crosswalk's entities are selected for
> prominence and prominent corporations are precisely the ones with many GLEIF
> entities sharing a canonical name.

## 2. The first cross-validation of two joins in this repo

Both routes answer *"which LEI is this filer?"*, independently by construction:
one through identifiers via a third party, one through canonical names.

| | agreement |
|---|---:|
| all bridged **and** name-matched | **93.0%** (944/1,015) |
| the **ambiguous** subset, where the bridge *picks* | **90.4%** (179/198) |

Predicted 60–80%; it is 93.0%. The name join's failure mode is **over-generation,
not mis-identification** — it keeps the right candidate and adds wrong ones. That
is the best evidence yet that the alignment work is doing something real, and it
is evidence nobody had, because no two routes to the same answer had been
compared.

The residual 7% is unexplained. One of the two routes is wrong there and which
is not known; that is a live open question, not a rounding error.

## 3. Purchasable reach saturates — and the mechanism I predicted is not the one

`scripts/curated_vs_filed_crosswalk.py`, over 26,850 distinct securities and
**$51.4T** of 13F positions.

| crosswalk | rows | coverage by count | **coverage by dollar** |
|---|---:|---:|---:|
| **filed** — GLEIF ISIN→LEI | 2,281,221 | 27.9% | **75.0%** |
| **curated** — wikidata→ISIN | 2,383 | 7.5% | **68.8%** |

> **A crosswalk 957× smaller answers 92% as much of what the workload weighs.**
> Per row acquired, the small file delivers **878×** more answered value.

### The mechanism is saturation, not curation — and my own control killed my hypothesis

I predicted **curation** was doing this: wikidata entities exist because somebody
judged them notable, and notability tracks size. The raw statistic agreed —
dollar/count ratio **9.21× curated against 2.68× filed**, 3.43× apart, in the
predicted direction.

**That ratio cannot compare crosswalks of different size**, because its ceiling
is `1/coverage_by_count`. Against an oracle picking the best k securities at each
crosswalk's *own* k, with a random draw at the same k as the floor:

| crosswalk | random | actual | oracle | **attained** |
|---|---:|---:|---:|---:|
| filed | 26.7% | 75.0% | 99.9% | **66.0%** |
| curated | 8.3% | 68.8% | 95.0% | **69.8%** |

**1.06× apart. Neither crosswalk is better targeted than the other.** Both
capture about two thirds of the value achievable at their own size, and the
878× per-row figure is a pure **saturation** effect: value concentrates so
steeply that the first few thousand rows carry most of the workload and the next
two million carry the tail.

My pre-registered refutation criterion named the raw ratio and would therefore
have *confirmed* a mechanism that is not there. See
`notes/lessons/2026-08-18-a-ratio-whose-ceiling-depends-on-k-cannot-compare-two-ks.md`.

## What this means for the programme

**Acquiring reach is cheap and then abruptly stops being worth anything.** The
acquisition decision is not "which crosswalk is best maintained" but "how far
down the value curve does this workload go" — and for a concentrated workload the
answer is *a few thousand rows*. The 68× cliff at the first identity boundary is
**not** going to be closed by buying more mappings, and this is now measured
rather than argued: the largest freely available mapping in its category reaches
75.0% of the value and a file 957× smaller reaches 68.8%.

What that leaves is **structural** reach — the entities no crosswalk covers
because no one has had a reason to relate them — and that is where the remaining
`f` lives.

## What would refute it

- **One workload, and a famously concentrated one.** 13F holdings are top-heavy
  by construction. A uniform workload — every registered security equally — would
  show saturation far later, and the *shape* of the value curve is the claim, not
  the constant. Measuring a second, flatter workload is the obvious next test.
- **Coverage-by-dollar assumes the uncovered tail does not matter.** For a
  question about *small* holdings it is exactly the tail that matters and the
  ranking inverts. The saturation claim is about aggregate exposure, not about
  every query.
- **The 1.33× enrichment is one crosswalk against one name join.** It is highly
  significant (p = 4.8e-07) and it is a single pair. Whether *every* crosswalk is
  enriched toward ambiguous entities is unmeasured; the mechanism predicts yes.
- **The 7% cross-validation disagreement** could be the bridge rather than the
  names. If wikidata's `sec`→`lei` pairs are wrong at that rate, the 24.9%
  coverage is really ~23% correct coverage and the composite `f` moves slightly.

## Reproduce

```bash
uv run python -u scripts/wikidata_bridge_cik_lei.py
uv run python -u scripts/curated_vs_filed_crosswalk.py
```

`runs/wikidata_bridge_cik_lei.json`, `runs/curated_vs_filed_crosswalk.json`;
predictions and outcomes in `notes/autonomy/predictions.jsonl` under
`wikidata-bridge-cik-lei` and `curated-vs-filed-crosswalk`.
