---
title: What the detection layer costs, in the repo's own currency
date: 2026-08-19
status: measured
arm: price-the-checks
---

## Accuracy is an input to the north star, not the north star

A day of work moved accuracy on the honest surface. The metric that decides
whether that was worth anything is `$ / solved answer above floor`. All rows
below are on `hard_distractors=True`, with **every stage charged** — the gate,
the reader and the kernel:

| system | acc | floor | gate share of time | $/correct | $/above floor |
|---|---:|---:|---:|---:|---:|
| flood | 0.669 | 0.000 | — | 1.124e-07 | 1.124e-07 |
| **flood + checks** | 0.915 | 0.000 | **0.5%** | 8.688e-08 | **8.688e-08** |
| scheduling | 0.790 | 0.645 | — | 1.381e-08 | 7.527e-08 |
| **scheduling + checks** | 1.000 | 0.645 | **4.9%** | 1.153e-08 | **3.249e-08** |
| solvency | 0.450 | 0.550 | — | 9.156e-10 | **inf** |
| **solvency + checks** | 1.000 | 0.550 | **44.0%** | 5.876e-10 | **1.306e-09** |

*(n = 152 non-empty for flood, 200 for the others; flood's answer is a set, so
its floor is 0 by construction and its two cost columns coincide.)*

## Three things

**1. One row changes kind, not degree.** Solvency's honest reader scores **below
its own floor**, so its cost per unit of capability is **infinite** — it has
bought nothing, and the ledger says so rather than printing a small number. The
checks take it to finite. That is the only qualitative move in the table and it
is the one the above-floor denominator exists to produce.

**2. The floor amplifies.** Scheduling's accuracy rises 1.27×, and its
`$/above floor` improves **2.32×**, because `(1.000 − 0.645) / (0.790 − 0.645)`
is 2.45. Quoting `$/correct` for that row would have shown 1.20× and understated
what the checks bought by half.

**3. The shared gate is not free where reading dominates.** It costs **0.5%** of
flood's pipeline, **4.9%** of scheduling's — and **44.0%** of solvency's, the
domain where reading is 96% of the wall clock. A regex pass over sentences is
nearly half the total cost there. I expected ~29% and under-called it.

The reason is structural and so is the fix: `filter_stale` **re-splits and
re-scans the same sentences the reader is about to split and scan**, so it pays
the tokenisation twice. Folding the cue check into each reader's own sentence
loop would bound its cost by the cue matching alone. That is not done, and it is
a genuine trade: the component's whole claim on attention is that it is the first
thing here that **transfers across domains unchanged**, and folding it in gives
that up. Named rather than taken.

## What would refute this

- Every rate is a measured CPU throughput on this machine, so the absolute
  dollars carry the price sheet's assumptions; the **ratios** are what to quote.
- The accuracies are the honest-surface numbers, which depend on distractors I
  wrote. Solvency's in particular carries its injection size — see the
  dose-response in the ownership-paragraph finding.
- Flood's 0.669 / 0.915 are over 200 seeds where the arm findings used 400
  (0.679 / 0.933). Same direction, same size, different n.
