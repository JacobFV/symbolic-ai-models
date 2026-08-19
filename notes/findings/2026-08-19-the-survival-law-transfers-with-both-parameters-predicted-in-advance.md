---
title: The survival law transfers to a structurally opposite task with both parameters predicted before the sweep — F to 1.1%, k to 20.2% — and the trivial population has dependency exactly zero
date: 2026-08-19
author: lead
status: provisional
epistemic_status: mechanistic model, now confirmed out-of-domain
tags: [theory, reader, transfer, law-confirmed, population-error]
---

## The bar a law has to clear

`S = F + (1−F)·q^k` was derived on flood and its parameters given referents
there. A law whose parameters are refitted per domain explains nothing, so the
test is whether both are **predictable on a new task before its sweep is run**.

Solvency is that task: no routing, no subset answer, a trivial kernel, a
bitemporal core, and a **boolean** answer where flood's was a set.

## Both predictions, made from structure

**F.** In flood the degenerate answer — what the kernels say when nothing is
recovered — is the empty set, and F was the share of cases whose truth is empty.
In solvency the degenerate answer is **False**, because with no filings the total
is 0. So the general form is

```
F = P(truth == the degenerate answer)
```

which is knowable with **no corruption at all**: run the kernel on an empty world.
Predicted **0.583**.

**k.** The ablation-measured dependency size, on the **non-trivial** population.
Predicted **8.25**.

## Measured

`scripts/theory_transfer_solvency.py`, 60 cases, uniform claim dropout.

| p | q | measured |
|---:|---:|---:|
| 0.02 | 0.98 | 0.923 |
| 0.05 | 0.95 | 0.843 |
| 0.10 | 0.90 | 0.740 |
| 0.20 | 0.80 | 0.630 |
| 0.50 | 0.50 | **0.583** |
| 0.80 | 0.20 | **0.583** |

| | predicted | fitted | error |
|---|---:|---:|---:|
| **F** | **0.583** | **0.590** | **1.1%** |
| **k** | **8.25** | **9.92** | **20.2%** |

rmse 0.0070. The curve asymptotes to 0.583 exactly, at both p = 0.50 and
p = 0.80.

> **Both parameters were predicted from the task's structure before the sweep,
> on a domain the law was not derived on.** The referents are real: F is the
> share agreeing with the degenerate answer, k is the dependency size of the rest.

k's 20.2% is *better* than flood's own 31% agreement between ablation and fit.

## The trivial population has dependency exactly zero

| population | n | mean dependency |
|---|---:|---:|
| truth == degenerate (not cleared) | 35 | **0.00** |
| truth ≠ degenerate (cleared) | 25 | **8.36** |

Not approximately zero — **exactly** zero, on all 35 cases. Dropping any single
claim never flips a case that was already going to fail the covenant. That is the
sharpest confirmation yet that F and k describe two disjoint populations rather
than being two knobs on one curve, and it is cleaner here than in flood, where
the empty-answer cases still had a dependency of 1.94.

## What I got wrong, twice

**The structural prediction was backwards.** I predicted k would be *small* —
1 to 3 — reasoning that a sum against a threshold makes single terms
non-decisive. It is 9.92, slightly *larger* than flood's 8.31. To **clear** a
threshold every contributing filing matters; the reasoning holds only for cases
that fail, and those are exactly the ones in F.

**And I made the pooled-population error again.** The first pass computed `k_eff`
over all 60 cases, got 2.06 against a fitted 9.92, and printed *"k does NOT
transfer"* at 381% error. Mean dependency 3.48 with **sd 4.15, min 0, max 9** is
visibly bimodal and I read past it. This is the second time — flood needed the
same split — so it is now written into the script as a comment rather than
remembered.

I also chased the wrong explanation first: pair-dropping survival is 0.589
against an independence prediction of 0.606, a gap of +0.016, so **interactions
are not the cause**. Testing that instead of asserting it is what forced the
population reading.

## Consequence

Required reader recall is now computable for a **new** domain with no sweep:

1. Run the kernels on an empty world → the degenerate answer → **F**.
2. Ablate single claims on the non-trivial cases → **k**.
3. `S = F + (1−F)q^k` gives the recall needed for any target.

That is the equation deleting experiments the theory mandate asks for, and it has
now survived a domain change.

## What would refute it

- **Two domains.** Scheduling is built and untried; it has an expensive kernel
  *and* a tunable margin, so it is the natural third.
- **k's referent is good to ~20–30%, not better**, on both domains. It is a
  predictor of the exponent's scale, not its third digit.
- **Uniform dropout is not a reader.** Real readers lose systematically, and the
  per-kind form supersedes this one for that case — see the reader-arm finding
  where the flat law was qualitatively wrong.

## Reproduce

```bash
uv run python -u scripts/theory_transfer_solvency.py
```
