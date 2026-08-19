---
title: Purchasable reach saturates at 96.9% for 13F dollars and 27.3% for GitHub events — saturation is a property of the workload, not a law, and one cheap statistic decides whether to buy the small file
date: 2026-08-18
author: lead
status: provisional
tags: [reach, acquisition, refuter, self-refutation, decision-rule, denominators]
---

## Running my own refuter

`notes/findings/2026-08-18-purchasable-reach-saturates-...md` claimed that
acquiring reach is cheap and then abruptly stops being worth anything: **2,383**
curated crosswalk rows reach **68.8%** of $51.4T of 13F holdings while
**2,281,221** filed rows reach 75.0%. It named its own refuter in one clause:

> *"13F holdings are top-heavy by construction. A uniform workload would show
> saturation far later, and the shape of the value curve is the claim, not the
> constant."*

`scripts/saturation_across_workloads.py` runs it on six workloads already on
disk. The deciding statistic is the **share of mass in the top 7.5% of
entities** — 7.5% being the count-coverage of the curated crosswalk, so the
number answers *"could a small acquisition have covered this?"* directly.

| workload | entities | **top 7.5%** | top 1% | top 25% | gini |
|---|---:|---:|---:|---:|---:|
| 13F holdings, by **$ held** | 33,656 | **96.9%** | 72.8% | 99.8% | 0.976 |
| patent assignees, per assignee | 572,495 | 85.6% | 69.5% | 93.2% | 0.892 |
| 13F holdings, by **position count** | 33,656 | 77.7% | 30.6% | 97.4% | 0.894 |
| caselaw citations, per cited case | 4,513,529 | 56.1% | 30.0% | 79.1% | 0.716 |
| patent citations, per cited patent | 8,407,184 | 55.6% | 25.0% | 80.5% | 0.723 |
| **github events, per repo** | 3,902,511 | **27.3%** | 8.7% | 53.2% | **0.373** |

**Spread: 27.3% to 96.9%, a 3.5× span.** Gini spans 0.373 to 0.976.

> **Saturation is not a law. It is a property of the workload**, and ordinary
> relational workloads differ enough that the same acquisition decision comes out
> opposite ways.

## The outlier is real, and it carries the conclusion

GitHub was verified directly rather than trusted, because a single flat workload
is what decides this: **7,730,712 events over 3,902,511 repos, mean 1.98, median
1, 57.3% of repos with exactly one event, maximum 1,043.** There is no head to
concentrate in. Five days of GH Archive is dominated by pushes and creates spread
across millions of individual repositories.

I predicted 70–85% for GitHub, on the assumption that activity concentrates the
way value does. It does not, and that was the substance of the error rather than
its magnitude.

## The decision rule this buys

> **Before acquiring a crosswalk, measure the workload's top-7.5% mass share.**
> At 96.9% (13F dollars) buy the small file and stop — 957× more rows bought
> 6.2 more points. At 27.3% (GitHub-like) a small acquisition buys almost
> nothing and breadth is the only lever.

One cheap statistic, computable before spending anything, that predicts whether
the 878×-per-row result will reproduce on a new workload. That is the
economically consequential half, and it is stronger than the original claim
because it is conditional and testable rather than universal.

## What survives, and what does not

**Does not:** the generality. "Purchasable reach saturates" as an unqualified
statement is refuted by a workload on this repo's own disk.

**Does, untouched:** the *mechanism*. Both crosswalks attain about two thirds of
the value achievable at their own size (69.8% curated, 66.0% filed), so neither
is better targeted and the raw dollar/count ratio remains an artefact of `k`.
That result was about the crosswalks; this one is about the workloads, and they
are independent.

**And the denominator trap fires again, inside one edge set.** The same 13F
holdings are **96.9%** concentrated by dollar and **77.7%** by position count.
That is the fourth time in this repo that a single relation has given materially
different answers under different denominators, and it is a reminder that "the
workload" is not defined until the mass is.

## What would refute it

- **Six workloads, all from one vendored snapshot.** Concentration may be an
  artefact of how each source was sampled into `data/sources/` — GH Archive is
  five days, 13F is one quarter. A longer GitHub window would concentrate more as
  active repos accumulate events, and that direction is known, not guessed.
- **Top-7.5% is one point on a curve.** Two workloads with the same top-7.5%
  share can differ at the knee that matters for a given budget. The full curve is
  in the run file; the single statistic is a screening test, not a substitute.
- **Mass is not always value.** A GitHub event and a dollar are not comparable
  units, and for a question about *security* rather than *activity* the relevant
  mass on GitHub might be far more concentrated (a few widely-depended-on repos).
  The claim is about the mass the workload actually weighs.

## Reproduce

```bash
uv run python -u scripts/saturation_across_workloads.py
```

`runs/saturation_across_workloads.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `is-saturation-general-or-13f`.
