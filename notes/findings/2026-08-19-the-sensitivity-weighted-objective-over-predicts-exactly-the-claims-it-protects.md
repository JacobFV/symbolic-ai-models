---
title: The sensitivity-weighted objective over-predicts exactly the claims it protects
date: 2026-08-19
status: measured
arm: reader-sensitivity
---

`L_reader = Σ sᵢ Lᵢ` — weight each claim by how much the kernels depend on it —
is the programme's proposed reader objective, and the sensitivities are now
measured rather than assumed. This is the arm that spends them. **It does not
work, the reason is mechanical, and the mechanism says what to build instead.**

## The implementation

The unit classifier's mistake-driven update is scaled by the sensitivity of the
labels it confused, priced at `max(s_gold, s_pred)` so that inventing a critical
claim is charged like missing one. Nothing downstream needs to be
differentiable — the weights come from deleting gold claims and re-running the
kernels.

Two weight vectors, because the first is wrong in a way the earlier finding
predicted:

- **single-deletion `sₚ`** — `runs/sensitivity_weights.json`;
- **rate-matched `sₚ^eff`** — delete the reader's *own share* `nₚqₚ` of a
  predicate's claims rather than one. `runs/sensitivity_at_rate.json`.

## 1. Rate-matching fixes the estimator, and the control is built in

| domain | predicate | `nₚ` | `qₚ` | k | `sₚ` | `sₚ^eff` | ratio |
|---|---|---|---|---|---|---|---|
| flood | `link` | 8.0 | 0.506 | 4 | 0.150 | **0.625** | **4.17** |
| scheduling | `has_capability` | 5.6 | 0.502 | 3 | 0.125 | 0.338 | 2.70 |
| flood | `bridge_on` | 5.0 | 0.240 | 1 | 0.050 | 0.100 | 2.00 |
| solvency | `revenue` | 6.7 | 0.142 | 1 | 0.300 | 0.362 | 1.21 |
| flood | `depot` / `needs` / `demand` | 1.0 | — | 1 | 0.850 | 0.850 | **1.00** |
| solvency | `owns` | 4.0 | 0.250 | 1 | 0.550 | 0.550 | 1.00 |

Singletons come out at exactly 1.00 — deleting `nq` of one claim *is* deleting
one — which is the control the measurement carries with it. **Single-deletion
sensitivity understates redundant predicates by up to 4.2x**: one missing road is
routed around, four are not. `link` moves from last in flood to mid-table.

## 2. Neither weighting buys end-to-end accuracy

120 held-out documents. `Δ` is weighted minus uniform.

| regime | domain | Δ claim F1 | Δ end-to-end |
|---|---|---|---|
| unseen phrasings, `sₚ` | solvency | +0.060 | **+0.067** |
| | scheduling | +0.121 | +0.025 |
| | flood | +0.042 | **−0.075** |
| unseen phrasings, `sₚ^eff` | solvency | +0.060 | +0.067 |
| | scheduling | +0.025 | 0.000 |
| | flood | −0.101 | −0.008 |
| 6 training documents, `sₚ^eff` | solvency | 0.000 | 0.000 |
| | scheduling | −0.026 | **−0.167** |
| | flood | 0.000 | **−0.200** |

One cell of nine improves by more than 0.03, and three lose 0.075 to 0.200.
Rate-matching removes flood's −0.075 and takes its F1 with it. **Claim F1 and
end-to-end accuracy move independently under reweighting**, which is the one
thing the arm was built to show and is not itself the win.

## 3. The mechanism: a margin update is not a reweighted loss

flood, 6 training documents, per-predicate precision and recall:

| predicate | weight | uniform | weighted |
|---|---|---|---|
| `needs` | **1.61** | P 1.00 / R 1.00 | **P 0.79** / R 1.00 |
| `link` | 1.18 | P 0.97 / R 1.00 | P 1.00 / R 1.00 |
| everything else | 0.14–1.61 | unchanged | unchanged |

The entire end-to-end loss is one predicate's precision, and it is an
**upweighted** one. Scaling a perceptron's update by `w` moves the decision
boundary `w` times as far, so the upweighted class is **over-predicted** — and
the classes worth upweighting are by construction the ones where a false positive
does the most damage. A spurious `needs` claim, sensitivity 0.850, poisons the
query. The objective protects a claim by inventing it.

Pricing at `max(s_gold, s_pred)` does not fix this: it makes the update larger in
*both* directions rather than penalising over-prediction, which is a different
thing and was the design error.

## 4. What was predicted, and what happened

- Predicted: end-to-end rises, F1 does not. **Backwards** — F1 rose in five cells
  of nine, end-to-end in one.
- Predicted: the gain tracks the spread of `sₚ`, largest on flood (6.6x).
  **Backwards** — flood is where it hurts most.
- Predicted refutation: "no movement anywhere, which would mean the classifier's
  errors are not on a margin any reweighting can reach". Half right. There *is*
  movement; it is the wrong sign, for a reason more specific than the one named.
- Predicted (previous finding, before this arm ran): "weighting by `sₚ` alone
  would send flood's reader after `depot` and away from `link`, which is the
  larger loss." **Held**, and rate-matching is the correction.

## 5. What this leaves standing

`L_reader = Σ sᵢ Lᵢ` is **not refuted as an objective**. What is refuted is
applying it as a per-example scale on a margin-based update:

- the weight belongs on a **calibrated** loss, where raising the cost of an error
  does not raise the rate of the opposite error;
- **false positives on critical predicates need their own price**, higher than
  false negatives, because the kernels consume a claim they cannot check;
- the sensitivity to weight by is **rate-matched**, `sₚ^eff`, not
  single-deletion.

And one fact about the domains, worth as much as the rest: **six training
documents are enough for 1.000 F1 in all three.** There is no regime here where
this reader makes graded, marginal errors — it is either exact or defeated by a
phrasing it has never seen. A reweighting reallocates capacity among close
decisions, and there are almost none. Testing the objective properly needs a
reader with soft, calibrated scores, which is the argument for the neural encoder
that the critical path has at step 3 and this perceptron stood in for.

## What would have refuted this reading

The precision loss falling on a *downweighted* predicate, which would have meant
over-prediction was not the mechanism and the harm was elsewhere. It fell on
`needs`, the most upweighted claim in the domain.
