---
title: No accuracy closes the price gap — and that is a narrower claim than it sounds
date: 2026-08-19
status: measured
arm: break-even-accuracy
---

## A blocked comparison that was only half blocked

`state.yml` records the neural comparison as blocked on paid credentials. That
blocks measuring a language model's **accuracy**. It does not block its
**price**, which is published, and `cost.py` has `api_component` for exactly
that.

So the question that needs no credentials: **at what accuracy would a model match
us on $/solved?**

    a* = llm_usd_per_attempt × our_accuracy / our_usd_per_attempt

Accuracy cannot exceed 1. If `a*` exceeds 1, the comparison is decided without
measuring the model at all.

| domain | tok/answer | our $/attempt | small hosted (\$0.15/Mtok) | frontier (\$3/Mtok) |
|---|---:|---:|---:|---:|
| flood | 362 | 4.90e-08 | **1,109** | 22,174 |
| scheduling | 325 | 1.45e-07 | **337** | 6,748 |
| solvency | 150 | 3.36e-10 | **66,742** | 1,334,849 |

The smallest break-even across three domains and two price points is **337** — an
accuracy of 337, where 1 is answering every case correctly.

**Insensitive to our own accuracy.** These use the published-surface figures
(1.000). On the honest surface flood scores 0.500, which halves its break-even to
~554 and changes nothing. Two orders of margin absorb any accuracy assumption.

## What this does not establish

More important than the number, and stated first in the script's own output:

**Our systems work because a reader was hand-written for each surface.** The
model needs no such engineering — that is the entire reason anyone would pay
1,000× per answer. The ledger charges the reader's **runtime**; it does not charge
its **development**, and this repo's own rule is that cost is charged to the
system.

So the honest claim is narrow:

> Per answer, at inference time, on a task a reader already exists for, the
> symbolic pipeline is 337× to 1.3M× cheaper than a language model at published
> rates.

Every qualifier there is load-bearing. Strip one and the sentence becomes false
or unsupported. In particular it says nothing about a task nobody has written a
reader for, which is the case a general model is actually bought for.

## Why it is still worth having

Because the gap is not 2× or 10×. At **337× minimum**, a great deal of
engineering amortises: the reader has to be written once and answer many
episodes before the comparison turns. That is a statement about *when* the
symbolic route pays, and it is computable — the break-even episode count is the
development cost divided by the per-answer saving.

That number is not computed here, because development cost is not measured
anywhere in this repo. It is the obvious next thing and it is the missing half of
the argument, not a footnote to it.

## What would refute this

- Published list prices, not negotiated ones, and input tokens only. Output
  tokens and any reasoning tokens would raise the model's cost, so this
  understates the gap.
- Our token counts are whitespace words, which undercounts against a BPE
  tokenizer by roughly 1.3×. Same direction.
- The comparison assumes the model attempts the same episode. A model answering
  from a shorter prompt would be cheaper per attempt, and 337× leaves room for
  a great deal of that.
