---
title: The north star with a learned boundary — 25,600x to 112,400x, and the gap is not an accuracy question
date: 2026-08-19
status: measured
arm: pipeline-cost
---

`$ / solved episode above floor` is what this programme says it optimises, and
every previous computation of it had a **hand-written pattern set** at the front —
patterns written while looking at the surface they read. That priced a component
nobody could deploy. This prices the pipeline whose language boundary was
**fitted from examples**: one reader implementation, no domain lexicon in its
source, plus the kernels it feeds, costed as one system.

The reader is the **union fit** — original documents plus a per-document renaming
of every entity — because that is the only configuration measured to survive
renaming, and a reader that collapses to 0.000 when the names change is not a
component anyone can deploy at any price.

`runs/learned_pipeline_cost.json`, 120 held-out episodes per domain,
`$0.02`/core-hour.

## The number

| domain | accuracy | floor | read ms | kernel ms | **$/solved above floor** | dominant |
|---|---|---|---|---|---|---|
| solvency | 1.000 | 0.533 | 1.32 | 0.01 | **$1.59e-08** | reader |
| scheduling | 1.000 | 0.642 | 1.51 | 0.02 | **$2.37e-08** | reader |
| flood | 1.000 | 0.342 | 3.07 | 8.36 | **$9.65e-08** | **kernels** |

Floors are structural and stated: the commonest constant answer — `False`,
`False`, and the empty set.

## Against a priced API, and why accuracy cannot close it

A frontier API at $3/Mtok input costs **$8.3e-04 to $1.6e-03 per attempt** on the
same documents. The comparison that matters is not per attempt but per *solved
episode above the same floor*, and it does not need an accuracy measurement to be
decisive:

| domain | API $/solved-above-floor **at accuracy 1.000** | multiple |
|---|---|---|
| solvency | $1.78e-03 | **112,395x** |
| scheduling | $2.42e-03 | **101,809x** |
| flood | $2.47e-03 | **25,597x** |

**Even a perfect API is four to five orders of magnitude more expensive per
solved episode**, so no accuracy number can close this gap — the comparison is
not about capability at all. That is the strongest form the claim can take
without measuring an LLM, and it is falsifiable by anyone who prices one
differently.

## The fit is repaid before the first episode ends

A learned reader has a one-off cost the pattern reader hid in a person's
afternoon. It is in the ledger:

| domain | fit | repaid after, vs a free reader | vs the API |
|---|---|---|---|
| solvency | $1.24e-05 (2.2 s) | 1,672 episodes | **0.01 episodes** |
| scheduling | $1.44e-05 (2.6 s) | 1,696 episodes | 0.02 episodes |
| flood | $3.29e-05 (5.9 s) | 518 episodes | 0.02 episodes |

Against a hypothetical free reader the fit needs ~1,700 episodes to pay for
itself. Against the API it is repaid **before the first episode finishes** — the
fit costs less than 2% of one API call.

## Where the time goes, and a published claim that inverts

The repo has carried "reading is 96.1% of solvency's wall clock" since the regex
reader. With a learned reader it is **99.2%** for solvency and 98.7% for
scheduling — the claim strengthens where the kernel is trivial. In flood it
**inverts**: the kernels take 8.36 ms against the reader's 3.07, so 73% of the
bill is ASP and SMT. "Reading dominates" is a statement about the *kernel*, not
about reading.

## What an outside reader should hold against this

- **Generated surfaces.** The accuracy is 1.000 in distribution; the same reader
  scores 0.33–0.58 end-to-end on unseen phrasings and 0.000 under renaming
  without the augmentation used here.
- **A per-domain fit.** The API needs none. The break-even above prices that
  honestly, but it does not price the human judgement in choosing the three
  domains.
- **n = 120** per domain, one generator each.
- **Input tokens only** on the API row, which understates it, and a $0.02
  core-hour that a different price sheet would move.
- The pipeline answers a *bounded* query per domain. Nothing here shows the same
  economics on open-ended language, and the real-text arms of this session say
  the boundary is exactly where it gets hard.

## What would have refuted it

The learned reader costing enough to close the gap — it does not; it costs 1.3 to
3.1 ms per document. Or the kernels dominating everywhere, which would have made
the reader's cost irrelevant and the "price the whole system" rule moot. They
dominate in exactly one of three domains, which is why the rule is in the ledger.
