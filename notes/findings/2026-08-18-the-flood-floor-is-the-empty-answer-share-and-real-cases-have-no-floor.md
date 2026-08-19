---
title: The parse-fidelity "floor" of 0.450 is exactly the share of cases whose answer is empty — on cases with a real answer the pipeline is a pure power law with no floor, S = q^8.31, and needs 98.7% recall
date: 2026-08-18
author: lead
status: provisional
epistemic_status: mechanistic model (decomposition verified on the same population; exponent accurate to ~30%)
tags: [reader, text-to-world, theory, correction, floors]
---

## What was being tested

`notes/findings/2026-08-18-the-reader-survival-law-...md` fitted
`S = F + (1−F)q^k` to the published parse-fidelity sweep, got `k = 9.35`,
`F = 0.338`, and labelled itself an empirical scaling law with a named promotion
test: **does `k` equal the answer's dependency size, measured directly?**

`scripts/k_versus_dependency.py` measured it by single-claim ablation — drop one
claim, re-solve, count the claims that move the answer — over 40 cases.

## The first answer was "killed", and it was wrong

Mean `d` = **6.95**, implied exponent `k_eff` = **5.76** against the fitted
**9.35**: a 38% gap, and in the *opposite* direction from the Jensen correction
registered beforehand. The script printed **KILLED**.

The trace showed why that verdict could not be trusted: many cases print
`answer 0` — the correct answer is the **empty set**, no vehicle can make the
delivery — and those have `d ≈ 2` because corruption cannot break an answer that
is already empty.

## Same population, and the gap vanishes

`scripts/k_same_population.py` runs the drop sweep on **the same 40 cases**:

| | fitted `k` | fitted `F` | rmse |
|---|---:|---:|---:|
| all 40 cases | **5.71** | 0.400 | 0.0724 |
| **non-empty answers only** | **8.31** | **0.014** | **0.0176** |

- **Interaction effect: −0.9%.** `k` fitted here (5.71) matches `k_eff` from
  ablation (5.76) almost exactly. The 38% gap was **population**, not claim
  interactions.
- **The empty-answer share is 0.450**, against an all-cases fitted floor of
  **0.400** — and the published sweep's "strongest floor" is **0.450**.

> **The floor was never a reasoning baseline. It is the fraction of cases whose
> correct answer is "no vehicle can do it", which survive any corruption for
> free.**

## On real cases there is no floor at all

| p | q | all cases | **non-empty** | `q^8.31` |
|---:|---:|---:|---:|---:|
| 0.02 | 0.98 | 0.895 | **0.873** | 0.845 |
| 0.05 | 0.95 | 0.770 | **0.664** | 0.653 |
| 0.08 | 0.92 | 0.715 | **0.509** | 0.500 |
| 0.10 | 0.90 | 0.615 | **0.409** | 0.417 |
| 0.15 | 0.85 | 0.560 | **0.291** | 0.259 |
| 0.20 | 0.80 | 0.470 | **0.136** | 0.157 |
| 0.50 | 0.50 | 0.440 | **0.018** | 0.003 |

`F = 0.014`, rmse 0.0176. **A pure power law.** Where the answer is real, a lossy
reader is driven to nothing.

### The requirement, restated on the cases that matter

| target success on real cases | **q needed** |
|---:|---:|
| 0.50 | 0.9200 |
| 0.80 | 0.9735 |
| **0.90** | **0.9874** |

The original sweep was read as "roughly ≥ 90% per-claim recall". The pooled fit
corrected that to 98.3%. **Restricted to cases with a real answer it is 98.7%,
and at 90% recall the pipeline answers 41% of them** — with no floor to fall
back on.

## Status of the law: promoted, with the accuracy stated

**Promoted from empirical scaling law to mechanistic model**, because both
parameters now have referents rather than being fitted constants:

- `F` = **share of cases whose answer is corruption-proof** (0.450 measured vs
  0.400 fitted).
- `k` = **the answer's dependency size**, measurable by ablation with no sweep
  (5.76 vs 5.71 pooled).

**And the accuracy is ~30%, not 1%.** Restricted to non-empty cases, ablation
gives mean `d` = 11.05 and `k_eff` = 10.91 against a fitted 8.31 — a 31% gap, now
in the Jensen direction originally predicted. The pooled agreement of 0.9% is two
component errors cancelling and **must not be quoted as precision**.

## Why this matters for the reader programme

- **Report the two populations separately.** A pooled score on this task is 45%
  a measure of the case mix. Any reader arm evaluated on the aggregate will look
  far better than it is.
- **The target is `q ≥ 0.987` on answer-critical claims**, and there is no
  graceful degradation to lean on.
- **`k` is measurable per task without a sweep**, so the required recall for a
  *new* domain can be computed before building its reader — which is what the
  law was for.

## What would refute it

- **One task.** The decomposition should reproduce on scheduling or solvency;
  if their "floors" are not their trivial-answer shares, `F` is not general.
- **`corrupt` drops `bridge_on` with `load_limit`**, so per-claim drop is not
  uniform and the mapping from `p` to `q` is approximate. That is a candidate
  source of the residual 31%.
- **40 cases, 5 repeats.** The non-empty arm has n = 22.
- **Precision failures unswept.** `MISREADS` exists and has never been run; the
  law describes recall loss only.

## Reproduce

```bash
uv run python -u scripts/k_versus_dependency.py
uv run python -u scripts/k_same_population.py
```
