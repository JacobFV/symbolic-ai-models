---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-a-map-rules-confidence-belongs-to-the-entry-that-fired,
          2026-08-17-the-gate-cannot-tell-the-treatment-from-the-control,
          2026-08-17-a-rule-is-verified-on-the-population-its-guard-admits,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# The model is not miscalibrated on the derived bucket. It correctly does not know it is in the derived bucket.

Pre-registered in
[[2026-08-17-a-map-rules-belongs-to-the-entry-that-fired]] — the central
prediction was that `bits | derived, not copyable` would fall **below 1.0** from
2.363 once a `map` rule's confidence came from the **entry** that fired rather
than from its average over the whole table.

## The result

| | acc \| der,not | **bits \| der,not** | control acc | control bits |
|---|---:|---:|---:|---:|
| `frontier-010` | 0.989 | **2.363** | 0.143 | 9.281 |
| `frontier-perkey` | 0.989 | **2.472** | 0.143 | 9.289 |

**Prediction 1 refuted** — bits got marginally *worse*, not below 1.0.
Predictions 2, 3 and 4 held exactly: the control did not sharpen (9.289 against
9.281, so no per-entry noise-fitting), accuracy did not move in either arm, and
pooled `label_bits` improved slightly, 7.141 → 7.128.

## Where the signal was lost, and it was not the calibrator

The obvious suspect was the calibrator flattening a sharp signal. It is not:

* per-entry confidence on the derived fills: mean **0.293**, max 0.649
* the gate the calibrator returns: mean **0.303**, max 0.814

The calibrator is *amplifying* and can reach 0.814. **The confidence signal
itself is low**, where the pre-registration assumed ~0.9.

## The assumption that was false, measured

The pre-registration's load-bearing sentence was: *"the entry that fired **is**
the sub-population"*. It is not. Over training, the six kind entries fire **589**
times and only **24.3%** of those firings are on derived fills:

| kind key | fires | of which derived | rule right |
|---|---:|---:|---:|
| `auto` | 105 | 0.276 | 0.371 |
| `body` | 81 | 0.247 | 0.370 |
| `building` | 93 | 0.215 | 0.398 |
| `garment` | 115 | 0.252 | 0.339 |
| `ship` | 119 | 0.244 | 0.303 |
| `shoe` | 76 | 0.211 | 0.316 |
| **all six** | **589** | **0.243** | **0.348** |

A kind word appears as the rule's key on plenty of *non-derived* fills, where the
answer is something else entirely. So per-entry precision is ~0.35, its Wilson
bound ~0.29, and that is exactly the confidence measured above. The entry is
diluted the same way the rule and the guard were.

## What this actually says, and it corrects the previous finding

Three candidate separators, all measured, none works:

| candidate | why it fails | number |
|---|---|---|
| the **rule** | `score` already is its precision where it fires | 0.66 |
| the **guard** | best guard covering the derived fills is impure | 0.531 purity |
| the **entry** | a kind key fires mostly on non-derived fills | 0.243 derived |

**Nothing the model has at prediction time identifies a derived fill.** So the
2.363 bits is **not a calibration failure — it is correct calibration under
genuine uncertainty.**

That overturns how I wrote the previous finding. I said *"the model knows the
answer exactly and keeps a third of the mass"*, and read it as the repo's oldest
complaint arriving at a new model. It is not that. **The model does not know.** It
holds a rule that is right on this sub-population and wrong elsewhere, cannot
tell which case it is in, and assigns the honest average. Being right 87/87 on
the derived bucket is a property of the bucket, not knowledge the model has
about it.

`a-ranking-is-a-property-of-a-metric` still applies, but as the *opposite*
reading to the one I gave: accuracy on this bucket is flattering, because it
scores the model only where its rule happens to be right. Bits scores it
everywhere the rule fires and reports the mixture. The refuter's point that
accuracy is blind here holds for the **treatment** arm as well as the control,
which neither of us said.

## What would recover the bits, and it is not a gate

An observable that correlates with derivedness. There is none in the current
feature set — `scripts/guard_ceiling.py` reports the ceiling at 0.531 and this
note adds 0.243 for the entry. Recovering the ~2 bits needs a **new atom**, not a
new calibration, and any atom that separated derived from non-derived fills would
have to be a fact about the generator rather than about the tree.

**`frontier-perkey` is kept registered although it is a null**, for the same
reason `frontier-002` was: it is the control that makes "the entry is not the
sub-population" a measurement rather than an assertion.
