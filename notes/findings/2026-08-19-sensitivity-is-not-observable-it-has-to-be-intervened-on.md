---
title: Sensitivity is not observable; it has to be intervened on — and per-claim weight ranks differently from total contribution
date: 2026-08-19
status: measured
arm: reader-sensitivity
---

The programme's proposed reader objective is `L_reader = Σ sᵢ Lᵢ` — weight each
claim by how much the downstream symbolic computation depends on it, so
importance is backpropagated from the kernels into the reader without
differentiating through them. `sᵢ` had never been measured. This measures it,
twice, and the first attempt is the instructive one.

## 1. The observational estimate cannot work

Fit the learned reader on **2** phrasing variants, test on **4**, so it makes real
mistakes. Per document, record each predicate's recall and whether the kernels
then got the right answer; rank with `AUC(recall of p → answer correct)`.

| domain | best predicate | AUC | worst | AUC |
|---|---|---|---|---|
| solvency (acc 0.600) | `revenue` | 0.617 | `owns` | 0.616 |
| scheduling (acc 0.608) | `has_capability` | 0.516 | `duration` | 0.420 |
| flood (acc 0.350) | `depot` | 0.631 | `mass`/`demand`/`flooded` | 0.500 |

Nothing separates. And the reason is not that the claims do not matter: in flood
`mass`, `demand` and `flooded` sit at exactly 0.500 because their recall is
**1.000 on every document**. No variance, no ranking information, whatever their
true weight. An observational estimate of importance is confounded by how hard
each claim happens to be to read, and the confound is total on precisely the
claims a reader is already good at. `runs/which_claims_matter.json`.

## 2. Intervened: delete one gold claim, re-run the kernels

`sₚ = P(the answer changes | one claim of predicate p is deleted from the gold
world)`. No reader is involved, so this is a property of the **task**, reusable
for any reader. 40 documents (20 for flood, which re-solves an ASP+SMT flow per
deletion). `runs/sensitivity_weights.json`.

| domain | predicate | `sₚ` | `nₚ` | `qₚ` (this reader) | `nₚqₚsₚ` |
|---|---|---|---|---|---|
| flood | `depot` | **0.850** | 1.0 | 0.600 | 0.510 |
| | `needs` | 0.850 | 1.0 | 0.700 | **0.595** |
| | `demand` | 0.850 | 1.0 | 0.000 | 0.000 |
| | `mass` | 0.633 | 3.0 | 0.000 | 0.000 |
| | `capacity` | 0.633 | 3.0 | 0.233 | 0.443 |
| | `link` | **0.144** | 8.0 | 0.506 | **0.582** |
| | `bridge_on` / `load_limit` | 0.130 | 5.0 | 0.240 | 0.156 |
| solvency | `owns` | **0.550** | 4.0 | 0.250 | 0.550 |
| | `revenue` | 0.328 | 6.7 | 0.142 | 0.313 |
| scheduling | `needs_capability` | 0.350 | 6.0 | 0.171 | 0.359 |
| | `capacity` | 0.350 | 3.0 | 0.292 | 0.306 |
| | `has_capability` | 0.179 | 5.6 | 0.502 | **0.502** |
| | `duration` | 0.171 | 6.0 | 0.192 | 0.196 |

`sₚ` is **not** flat: flood spans 0.129 to 0.850, a 6.6x range. So the weighted
objective has something to buy, which is the question this was run to settle.

## 3. Two predictions refuted, both mechanically

**Predicted: `link` dominates flood, because reachability gates everything.**
It is the *least* sensitive claim in the domain per instance, 0.144 — the road
network is cyclic and redundant, so deleting one edge almost never disconnects
anything. But there are **eight** of them and the reader recovers only half, so
`link` carries the **largest total contribution** in the domain. Per-claim
sensitivity and total contribution rank differently, and the objective needs
`nₚqₚsₚ`, not `sₚ`.

**Predicted: `revenue` dominates `owns` in solvency, since a member with no
filing contributes nothing.** Backwards: `owns` 0.550 against `revenue` 0.328.
Deleting a membership removes that member's whole contribution from the
consolidated sum; deleting one filing usually leaves an **earlier vintage of the
same member** standing, because the domain's substance is revisions. The
bitemporal structure that makes solvency hard is the same structure that makes
its individual filings redundant.

## 4. The independence model overestimates, by 1.2 to 2.3x

`P(failure) ≈ 1 − Π(1−sₚ)^(nₚqₚ)` against the failure rate the same reader
actually suffers:

| domain | predicted | measured | ratio |
|---|---|---|---|
| flood | 0.984 | 0.800 | 1.23 |
| solvency | 0.692 | 0.425 | 1.63 |
| scheduling | 0.795 | 0.350 | 2.27 |

Directionally right, and wrong by enough to matter. Two mechanisms, both
predicted in advance: reader errors are **correlated within a document** — one
unparseable phrasing costs a whole paragraph, and those errors land on the same
answer — and some deletions are **recoverable from the rest of the world**. The
gap is largest in scheduling, which is the domain with the most redundancy
(capabilities repeat across machines) and the strongest correlation (one variant
governs a whole paragraph of capability sentences).

That gap is the honest statement of what `k_eff` has to absorb. `r^k` with
independent claims is not the model; the measured ratio is the correction.

## What this changes

- **`L_reader = Σ sᵢ Lᵢ` is worth building** — `sₚ` spans 6.6x in flood, so
  uniform weighting is leaving something on the table.
- **The weight to train on is `nₚ sₚ`**, the per-document contribution, not `sₚ`.
  Weighting by `sₚ` alone would send flood's reader after `depot` and away from
  `link`, which is the larger loss.
- **Sensitivity is measured once per task and reused.** It costs
  `|claims| × |docs|` kernel runs and is independent of the reader, so it does
  not have to be recomputed as the reader improves.

## What would have refuted it

`sₚ` coming out flat across predicates — the weighted objective would then have
nothing to buy and this line should be dropped. It did not: 0.129 to 0.850.
