---
title: A backtest that ignores publication lag gets 47.8% of early decisions wrong; ignoring revision alone costs 10.4% — the dominant term is existence, not revision
date: 2026-08-18
author: lead
status: provisional
tags: [economy, kernels, temporal, second-task, refuted-prediction]
---

## What was built

`economy@1`, the last named tier-6 kernel, and `symbolic_ai_generators/solvency/`
— the **second generated task**, chosen to be structurally the opposite of the
flood one. No routing, no discrete search, no subset answer: one boolean per
group per decision date, *did it clear its revenue covenant*, and the whole
difficulty is that the figures were revised after the decision.

It is the first thing to exercise the two-times machinery the world IR has
carried since it was written. `valid_time` is the quarter a figure is about;
`transaction_time` is when it could have been known. `economy@1` **requires**
`as_of` and refuses without it, because the only available default is "now" and
using it is the bias itself. An observation missing either time is discarded by
name.

## Prediction, before the numbers

Stated in advance: as-of and latest-vintage decisions differ on **15–30%** of
cases.

Measured **11.3%** on the default task — below the range. And the sweep found
that a single number was the wrong thing to predict.

## Measured, decision date swept, 500 cases per row

| decide at | incomplete | **disagree** | from missing | from revision |
|---|---|---|---|---|
| +20d | 1.000 | **0.478** | 0.478 | 0.000 |
| +40d | 1.000 | **0.478** | 0.478 | 0.000 |
| +55d | 0.942 | 0.452 | 0.448 | 0.004 |
| +70d | 0.414 | 0.268 | 0.198 | 0.070 |
| +90d | 0.000 | 0.104 | 0.000 | **0.104** |
| +120d | 0.000 | 0.090 | 0.000 | 0.090 |
| +180d | 0.000 | 0.032 | 0.000 | 0.032 |
| +300d | 0.000 | 0.000 | 0.000 | 0.000 |

First filings land at +30 to +75 days; revisions at +60 to +200. The sweep
separates the two effects almost perfectly, because they occupy different
windows.

## What it says

> **The dominant term in look-ahead bias is not revision. It is existence.**

A backtest that carefully uses first-vintage figures — the usual careful thing —
but ignores publication *lag* still gets **47.8%** of early decisions wrong.
Nearly half. Revision alone, isolated at +90d where everything has filed and
nothing has yet been restated, costs **10.4%**.

That is a 4.6× ratio in favour of the effect that a "use the first vintage"
heuristic does not address at all, and it is the effect only a full
`transaction_time` model catches. The two-times design is usually justified by
revisions; on this task revisions are the smaller half.

The decay to **0.000 at +300d** is the sanity check: once every revision has
landed, as-of and latest agree by construction, and a non-zero number there would
mean the measurement was picking up something else.

## Two ways this could have been circular, and what was done

**The covenant bar knowing the answer.** The first version set the threshold from
the group's *final* total — look-ahead in the generator of a task about
look-ahead, which would have made the threshold aware of which way the revisions
went. It is drawn from the **first-vintage** total instead, which is what a
lender writing the covenant would have had, and a test asserts it stays within
±7% of that and never of the final one.

**The oracle sharing the kernel's code.** `decide` is a direct search over the
filing list and its source is asserted to contain no reference to `economy@1`,
`get_kernel`, `project_world` or `as_of_value`. The kernel matches it on 80/80
cases and on 400/400 in the wider run.

## What would have refuted it

- **A degenerate task.** Both outcomes occur across seeds, asserted; and the
  covenant is close by construction, since a bar nobody is near flips on no
  revision at all and would report zero for the wrong reason.
- **An unfiled figure counting as zero**, which would make every early total look
  like a collapse and manufacture the missing-data effect. The kernel emits *no
  claim* when nothing has been published, asserted, and reports `reported: 0`.
- **The revision model being tuned to produce this.** 35% of filings are revised
  and the revisions are 2–9% either way — mild on purpose, and symmetric: the
  default task's disagreements split 13 one way and 13 the other over 400 cases.

## What this does not establish

The lag and revision distributions are invented, not fitted to any real filing
calendar, so the *magnitudes* are properties of the generator. What is not a
property of the generator is the **ordering** — missing data dominates revision
wherever first filings are still arriving, and that follows from an absent figure
moving a total by its whole value while a revision moves it by a few percent.

It is also still a generated task. The substrate now has two of them, which is
one more than it had this morning and the minimum needed to tell a substrate
property from a flood-logistics property.
