---
title: task_success = F + (1−F)·q^k fits the flood pipeline with k = 9.35 and rmse 0.015 — so the reader needs 98.3% per-claim recall, not the ≥90% the sweep was read as saying
date: 2026-08-18
author: lead
status: provisional
epistemic_status: empirical scaling law (two free parameters, ten points, one domain)
tags: [reader, text-to-world, theory, law, correction]
---

## The move

`notes/findings/2026-08-18-what-parse-fidelity-a-multi-kernel-pipeline-needs.md`
swept a claim-drop rate through the three-kernel flood pipeline and read the
resulting curve **qualitatively** — *"crosses its floor at p ≈ 0.17"*,
*"the practical requirement is roughly ≥ 90% per-claim recall"*. It never fitted
a form.

The standing theory mandate names the candidate: `P(success) ≈ q^k` for `q` the
per-claim recall and `k` the number of independently required claims. Adding the
floor the curve visibly asymptotes to:

```
S(q) = F + (1 − F) · q^k
```

**No new measurement.** Every input is read off the existing finding.

## It fits

`scripts/reader_survival_law.py`, least squares over `(k, F)` on the ten
published points:

| | |
|---|---:|
| **k** | **9.35** effective independently-required claims |
| **F** | **0.338** floor (the finding reports always-none at 0.347) |
| **rmse** | **0.0151** against a reported ±0.029 at N = 300 |

Largest residual **+0.037**. Two parameters reproduce the whole sweep inside its
own error bar.

## The correction it forces

Solving `S = F + (1−F)q^k` for `q` gives the required recall in closed form:

| target success | **q needed** | claims lost per 100 |
|---:|---:|---:|
| 0.60 | 0.9057 | 9.4 |
| 0.80 | 0.9623 | 3.8 |
| **0.90** | **0.9826** | **1.7** |
| 0.95 | 0.9916 | 0.8 |

> **The published reading — "roughly ≥ 90% per-claim recall" — is a target for
> `S = 0.585`, which is barely above that pipeline's own strongest floor of
> 0.450.** Reaching `S = 0.90` needs **98.3%** recall. The allowed error rate is
> **6× smaller** than the sweep was read as saying.

That is the whole reader programme's specification, and it was not visible
without the fit.

## `k` decomposes across claim kinds

The finding's per-kind table at `p = 0.20`, inverted through the same law:

| kind | agreement | **k_kind** |
|---|---:|---:|
| mass | 0.733 | **2.31** |
| capacity | 0.747 | **2.16** |
| link | 0.800 | 1.61 |
| demand | 0.900 | 0.73 |
| load_limit | 0.907 | 0.68 |
| flooded | 0.960 | 0.28 |
| **sum** | | **7.77** vs aggregate **9.35** |

Sum and aggregate agree to 17%, so **`k` is additive across kinds** — it counts
answer-critical claims, and each kind contributes its own. That turns the
finding's qualitative reading (*"fragility is in the facts that define the
answer's domain, not the facts that constrain it"*) into a ratio: **mass and
capacity carry 8× the leverage of `flooded`.**

## What follows for the reader

- **Effort is not uniform across the schema.** Per unit of recall, `mass` and
  `capacity` are worth ~8× `flooded` and ~3× `load_limit`. A reader that is
  excellent at relations and mediocre at entity attributes is optimising the
  wrong half.
- **`k` is the quantity to attack, not only `q`.** `S = F + (1−F)q^k` is far more
  sensitive to `k` than the sweep suggests: at `q = 0.95`, halving `k` from 9.35
  to 4.7 moves `S` from 0.66 to 0.85. **Anything that makes the answer depend on
  fewer claims is worth as much as a much better reader** — which is an argument
  for the reader emitting ambiguity and the kernels bounding over it, rather than
  for a bigger parser.
- **98.3% is a hard filter on architectures.** A regex template hits 100% on the
  phrasings it was written for and ~0% off them; anything statistical has to
  clear 98.3% on answer-critical claims to beat the floor by a useful margin.

## Epistemic status, stated deliberately

**Empirical scaling law**, not an identity and not a theorem. Two free
parameters, ten points, one domain, one metric. The `q^k` form assumes claim
losses are independent and that every required claim is equally necessary;
neither is exactly true, and the 17% gap between `Σk_kind` and `k` is where that
assumption is paying.

## What would refute it

- **A second domain.** If the economy or scheduling pipeline fits a different
  functional form, `q^k` is a property of flood logistics and not of
  enumerate-then-filter pipelines.
- **Precision failures.** The sweep drops claims (recall). A reader that invents
  or misreads claims is a different channel entirely and the law says nothing
  about it. `MISREADS` exists in `read.py` and has never been swept.
- **`k` should be predictable from the task.** If it is a real count of required
  claims, it should be derivable from the answer's dependency set — which the
  certificate machinery can compute directly. Agreement between fitted `k` and
  measured dependency size would promote this from a scaling law toward a
  mechanistic model; disagreement would kill it.

## Reproduce

```bash
uv run python -u scripts/reader_survival_law.py
```

`runs/reader_survival_law.json`.
