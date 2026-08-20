---
title: The router survives holding out its threshold — 0.375 on novel vocabulary, and the threshold transfers across regimes
date: 2026-08-19
status: provisional
arm: held-out-router
refutes:
  - my registered prediction that a held-out threshold would capture under 30%
  - my registered prediction that an agreement-only router would come close
---

## Why this was run

The selector arm reported a router taking novel-vocabulary reading 0.310 → 0.370
and flagged its own flaw: the threshold was **the median of disagreements on the
test items themselves**, fitted on the thing being scored. This measures the
honest version.

It is more than bookkeeping. For the **unseen** slice the training documents are,
by construction, entirely **seen** vocabulary — the regime where the reader is the
*stronger* system and its confidence distribution is shifted. A held-out
threshold there is not merely held out; it has to **transfer across regimes**.

**Predicted:** it does not transfer, held-out capture falls below 30%, and an
agreement-only router (defer whenever the two disagree, nothing fitted at all)
comes within 0.03 of the fitted one because the reader has no lift on novel
values anyway.

## What was measured

`runs/heldout_router.json`. Threshold swept on training documents only, applied
to test.

| slice | reader | floor | oracle | agreement-only | **held-out** | in-sample |
|---|---|---|---|---|---|---|
| unseen (n=184) | 0.288 | 0.310 | 0.413 | 0.310 (0.0%) | **0.375 (63.2%)** | 0.370 (57.9%) |
| seen (n=847) | 0.536 | 0.444 | 0.638 | 0.449 (−86.0%) | **0.584 (47.7%)** | 0.540 (3.5%) |

Thresholds fitted per fold — unseen: 0.582, 0.581, 0.869, 0.956; seen: 0.578,
0.558, 0.749, 0.616.

## The result: refuted twice, and the honest number is better than the flagged one

**The held-out router scores 0.375 on novel vocabulary — above the in-sample
0.370.** Capture is **63.2%**, not the predicted sub-30%. The threshold fitted on
seen vocabulary transfers to unseen vocabulary cleanly, which is the robustness
property I expected it to fail.

It is *better* than in-sample because the in-sample rule used an arbitrary
statistic — the median — while the held-out rule **sweeps** for the best operating
point on training data. Fitting properly on the right data beat not fitting at all
on the wrong data. So the flaw I flagged was real and its correction moved the
number **up**: the 0.370 was pessimistic, not optimistic.

On the seen slice the effect is larger: **0.540 → 0.584**, capture **3.5% →
47.7%**. The selector arm's "the router barely pays on seen values" was an
artefact of the median heuristic, not a property of the router.

**Agreement-only is a disaster and that is informative.** Deferring to the floor
on *every* disagreement scores exactly the floor on unseen (0.310, 0.0% of
headroom) and **−0.087 below the best single system** on seen. So the value is not
in "prefer the symbolic rule when they disagree" — it is specifically in **the
reader's graded confidence**. A binary disagreement signal carries none of it.

## Where this leaves the arm

Charged to the system, novel-vocabulary reading is now **0.375** against a
zero-supervision floor of **0.310** and a learned reader of **0.288** — and every
component of that is held out. The reader alone still has **no measurable lift**
on novel vocabulary; the retraction is untouched. What pays is the **combination**,
and specifically the reader's willingness to say how sure it is.

That is the shape this repo has argued for from the start: the value of an
inspectable component is not only its answer but the fact that its confidence
means something an external rule can be routed on.

## What would refute this

The fold-to-fold threshold spread on unseen — **0.581 to 0.956** — is wide enough
that a different split could land somewhere much worse. Four folds of 46 items is
not enough to see the shape of that surface, and this is the number most likely to
move when the slice grows.

## Limits

n=184 unseen, one relation, one domain. The oracle ceiling itself (0.413) is a
property of two specific systems, not a task ceiling. A larger fetch is running.
