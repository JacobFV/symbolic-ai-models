---
title: The threshold line closes — three estimates of false-positive cost agree, and the rule still loses
date: 2026-08-19
status: measured
arm: reader-sensitivity
---

The derived-threshold mechanism was left "correct, cheap, and unusable", because
the perceptron's calibrated belief had two values and no threshold could act. It
is now usable, and it loses. This closes the line and says what would reopen it.

> **Corrected the same day.** Sections 1 and 2 first attributed the flat belief
> to the perceptron and were wrong. The perceptron's raw belief is graded (15
> distinct values on flood) and predicts its own correctness at **AUC 0.843**.
> What flattened it was **calibrating on the training distribution**, where the
> model is near-perfect, so isotonic regression correctly reported that score
> does not predict accuracy and returned a constant. Calibrating on the
> deployment distribution keeps 5–7 levels. The conclusion is unchanged and now
> rests on a fair test rather than a broken one: with graded, meaningful beliefs
> the derived thresholds still never improve end-to-end accuracy, in nine cells.

## 1. A graded posterior, without a neural encoder

`LearnedSpanReader(model="logistic")` — multinomial logistic regression by SGD
over the same sparse features. Not a network; the point is calibration, not
capacity. Distinct belief values across ten held-out documents:

| model | flood | scheduling | solvency |
|---|---|---|---|
| perceptron + isotonic | 2 | 1 | 1 |
| logistic + isotonic | 2 | 1 | 1 |
| **logistic, uncalibrated** | **10** | **13** | **4** |

Note the middle row. Passing a logistic probability through the isotonic
calibrator re-binned it into at most eight levels and collapsed it. The cause was
**not** that the score was already a probability — it was the calibration set:
documents held out of the V=2 training pool, on which the model is near-perfect,
so every bin has the same outcome rate and PAVA pools them into one value. That
is the calibrator being right about a set that could not inform it.

Calibrating on **V=4 documents from the development seed range** (500,000+),
disjoint from both the fit and the evaluation, fixes it:

| arm | flood | scheduling | solvency |
|---|---|---|---|
| perceptron, calibrated on the training distribution | 2 | 1 | 1 |
| **perceptron, calibrated on the deployment distribution** | **6** | **5** | 1 |
| logistic, calibrated on the deployment distribution | 3 | 7 | 1 |
| logistic, uncalibrated | 11 | 14 | 5 |

**The belief was informative all along.** AUC(belief → claim correct), measured
directly: perceptron 0.843 / 0.794 / 0.595 and logistic 0.745 / 0.896 / 0.905 on
flood / scheduling / solvency. A reader that ranks its own errors at 0.84 is not
a reader with a flat belief.

## 2. With thresholds that can act, they hurt

Nine cells — three domains x {perceptron calibrated, logistic calibrated,
logistic raw} — and **θ never improves end-to-end accuracy in any of them**:

| domain | arm | uniform 0.5 | derived θ |
|---|---|---|---|
| flood | perceptron, calibrated | 0.375 | 0.375 |
| | logistic, calibrated | 0.342 | 0.342 |
| | logistic, raw | 0.350 | **0.317** |
| scheduling | perceptron, calibrated | 0.625 | **0.608** |
| | logistic, calibrated | 0.633 | 0.633 |
| | logistic, raw | 0.642 | **0.633** |
| solvency | all three | 0.667 | 0.667 |

Six ties and three losses. Where claim F1 moves it moves *up* while accuracy
moves down (scheduling 0.734 → 0.748 F1 against 0.625 → 0.608), which is the
signature of a rule trading answer correctness for claim count. Predicted a gain;
measured a loss or nothing, nine times.

## 3. Three independent estimates of `s⁺`, all saying "cheap"

Every θ below 0.5 comes from `s⁺ < s⁻`. That input was checked three ways:

| estimator | flood `link` | flood `mass` | scheduling `has_capability` |
|---|---|---|---|
| one synthetic falsehood | 0.068 | 0.178 | 0.050 |
| synthetic, at the reader's own FP rate | 0.049 | 0.217 | 0.041 |
| **the reader's actual false positives** | — (none emitted) | **0.308** | — |

Rate-matching does not raise `s⁺`, because the reader barely invents: `k⁺` is 1
for almost every predicate. And its *real* false positives are mostly free —
`owns` 0.000 over 40 claims, `capacity` 0.000 over 46, `needs_capability` 0.000
over 66, `load_limit` 0.000 over 17. Only `duration` (0.357) and `mass` (0.308)
cost anything.

A fourth cut, splitting the reader's false positives into those that **contradict**
a true claim about the same subject and those that merely **add** one, does not
resolve it either: flood says contradicting 0.308 against additive 0.000, and
scheduling says additive 0.270 with no contradicting cases at all. n is 11–37
documents per cell; this is not a distinction the data supports.

## 4. So the input is right and the rule still loses

The standing explanation, consistent with everything measured and not yet tested:
**a false positive is cheap in a perfect world and expensive alongside the
reader's other errors.** Every `s⁺` here is measured by inserting claims into the
*gold* world. The reader inserts them into a world that is already missing things
— and the same non-independence has been measured once before on this programme,
where the failure model `1 − Π(1−sₚ)^(nq)` overestimated by 1.23–2.27x precisely
because errors interact within a document.

If that is right, no single-perturbation sensitivity — of either sign, at any
rate — can price a decision rule, and the quantity needed is the cost of a
false positive **conditional on the reader's other mistakes**, which is a joint
measurement over error sets rather than over claims.

## What closes and what would reopen it

**Closing:** `L_reader = Σ sᵢ Lᵢ` has now failed as a training weight (three
domains, nine cells, one improvement) and as a decision rule (three domains, two
losses and a tie), with its key input verified three ways. It should not be
attempted a third time in this form.

**Reopening:** a measurement of joint error cost — perturb *sets* drawn from the
reader's actual error distribution rather than single claims — would give a
quantity the rule could use. That is a different and more expensive experiment,
and it is the only version of this line worth funding.

## What this leaves standing regardless

The asymmetry itself is real and is a fact about the **tasks**, not about any
reader: `flooded` and `bridge_on` are the only predicates whose invented claims
cost more than their lost ones, and they are exactly the ones that impose
constraints rather than supply capacity. That generalises to any constrained-
selection domain and does not depend on the threshold rule that failed to exploit
it.
