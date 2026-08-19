---
title: The flagged share cancels — certification value is bounded by 1/(1−accuracy), so the repo's models top out at 1.48× while the federated arms reach 57.5×, and the strongest determinacy signal in the repo is worth 1.02×
date: 2026-08-18
author: lead
status: provisional
tags: [certification, cost, north-star, models, unification, prediction-refuted-mechanism]
---

## The question

This session measured certification value on federated data and found it real —
escalation targeting worth **4.69×** on entity alignment, a maintenance
certificate worth **16.1×** rising to **57.5×** with a tighter sound bound. The
repo's actual subject is the language substrate, and nobody had asked whether its
models have any certification value at all.

They abstain, and abstention looks like epistemic virtue.

## The signal was already computed and thrown away

`_forward_graph` builds `s_conf`, which is **0 at every position a model declined
to vote on** and positive where it committed, feeds it to `_mix`, and discards
it. Exactly the shape of the certificate arm's discarded slack. It is now exposed
as `ModelOutput.channels["determinacy"]`, consumed by nothing else, so no
published number moves.

Ten models, one shared config, each rebuilt from it and re-fitted (rule-based
models are fitted, not checkpointed).

| model | votes on | acc\|voted | acc\|abst | gap | label_acc | **aim×** | ceiling |
|---|---:|---:|---:|---:|---:|---:|---:|
| routes-001 | 98.3% | 0.329 | 0.000 | +0.329 | 0.323 | **1.48×** | 1.48× |
| ruleinduce-001 | 82.9% | 0.391 | 0.030 | +0.360 | 0.329 | 1.45× | 1.49× |
| ilp-001 | 60.9% | 0.475 | 0.059 | +0.416 | 0.312 | 1.37× | 1.45× |
| syllogism-001 | 56.0% | 0.207 | 0.068 | +0.139 | 0.146 | 1.09× | 1.17× |
| **synth-001** | **2.1%** | **0.759** | 0.062 | **+0.697** | 0.077 | **1.02×** | 1.08× |

`corefer-001`, `ptrgen-001` and `vsa_perm-002` **never abstain** — no flagged set
to aim with. `evidence-001` and `grammar-001` abstain on **one position out of
5,233** and are slices, not results.

## The flagged share cancels

```
aim  =  (1−v)(1 − a_abstained)  /  [(1−v)(1 − base)]  =  (1 − a_abstained) / (1 − base)
```

> **Certification value is not governed by how much you flag, nor by how *well*
> you flag it.** Since `a_abstained ≥ 0`:
>
> **aim ≤ 1 / (1 − label_acc)**

Every model sits at or just under that bound. `routes-001` and `grammar-001`
attain it exactly, because their abstained positions score 0.000.

### The sharpest instance

**`synth-001` has the strongest determinacy signal in the repo** — it votes on
2.1% of positions at **0.759** against **0.062** elsewhere, a gap of **+0.697** —
**and it is worth 1.02×.** A near-perfect flag on a model that is 7.7% accurate
buys nothing, because escalating what it skipped only helps to the extent
everything else was already right.

> **A model can only certify to the extent it is usually right.**

## This unifies the whole session

| system | base accuracy | measured aim× | `1/(1−base)` |
|---|---:|---:|---:|
| curriculum models | 7.7%–32.9% | 1.02×–1.48× | ≤ 1.49× |
| federated resolver (escalation) | 0.873 | 4.69× | 7.9× |
| maintenance, derived margin | 0.9924 | 16.1× | 131.6× |
| maintenance, `\|Δcount\|` bound | 0.9924 | 57.5× | 131.6× |
| maintenance **oracle** | 0.9924 | **131.6×** | **131.6×** |

The oracle's 131.6× is **exactly** `1/(1 − 0.9924)`. The whole session's spread —
1.02× to 131.6× — is one quantity: **how often the system is already right.**

That also explains the earlier finding that determinacy is informative only when
the candidate generator has high recall. Recall sets the base accuracy, and the
base accuracy sets the ceiling.

## The prediction: right number, wrong reason

I pre-registered **1.0×–1.3×, none above 1.5×**, and measured **1.02×–1.48×**.
But the mechanism I gave was *"these models abstain on most positions so they
flag 65–99%"*, taken from a docstring citing `ilp` at 35% and `synth` at 1%. In
fact three models flag **~0%** and vote rates span 2.1% to 100% — and the flagged
share **cancels entirely**. Getting the number right from a mechanism that is not
operating is not a successful prediction, and it is recorded as such.

## Two defects fixed before this was reportable

- The script printed a canned conclusion about a "middle regime" of flagged share
  while the table beside it showed 0–2% — and the algebra says the term cancels.
  The conclusion is now derived from the measured rows.
- `grammar-001` and `evidence-001` abstain on **one** position each and were
  printed as measurements. A minimum abstained set of 30 is now required, per the
  standing rule that a slice may form a hypothesis and never report one.

## What would refute it

- **One config, ten models, `n_train = 20`.** The accuracies here are low partly
  because the budget is small; a model at 0.7 accuracy would have a ceiling of
  3.3× and the ordering could change. The *bound* is algebraic and holds
  regardless, but which models approach it is a measurement.
- **The ceiling is attained only when abstained positions score 0.** A model
  whose fallback is strong has a lower ceiling, so strengthening the structural
  back-off — which this repo did deliberately — **reduces** certification value
  while raising accuracy. That trade is real and nobody has priced it.
- **`aim` prices one use of certification** (escalation targeting). A certificate
  that lets a downstream consumer skip work is worth something this does not see.
- **Only the label head.** Type and pointer heads have their own determinacy and
  are unmeasured.

## Reproduce

```bash
uv run python -u scripts/can_the_models_certify.py
```

`runs/can_the_models_certify.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `can-the-curriculum-models-certify`.
