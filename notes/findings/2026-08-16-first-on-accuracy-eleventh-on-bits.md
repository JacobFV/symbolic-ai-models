---
date: 2026-08-16
author: lead
status: provisional
related: [2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary,
          2026-08-13-a-ranking-is-a-property-of-a-metric,
          2026-08-14-the-label-score-is-a-copy-score,
          2026-08-13-a-control-that-could-fail]
---

# `frontier-001` is first of twenty-four on accuracy and eleventh on bits, in one summary

`runs/full179`, the base curriculum, all 179 lessons, same config and same
evaluation seeds as every other row. This is the pooled table, not the derived
bucket — for that see
[[2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary]].

| model | lbl acc | rank | lbl bits | rank | typ acc |
|---|---:|---:|---:|---:|---:|
| **`frontier-001`** | **0.404** | **1** | 7.433 | **11** | 0.863 |
| `corefer-001` | 0.357 | 2 | 6.952 | 6 | 0.946 |
| `workspace-001` | 0.357 | 3 | 7.813 | 13 | 0.780 |
| `omegaclaw_rank-001` | 0.356 | 4 | 8.093 | 16 | 0.858 |
| `ilp-001` | 0.312 | 9 | 8.223 | 18 | 0.715 |
| `grammar-001` | 0.187 | 14 | **6.089** | **1** | 0.798 |
| floor | 0.143 | — | 9.369 | — | 0.860 |

**+0.047 over the previous best is a large move for this repo.** The entire
published spread from `corefer` at 0.357 down to `ngram` at 0.170 is 0.187, and
`RESEARCH_LOG.md` says models here span about 0.1 of lift while the harness
spans 0.15 to 2.0. This is a model-versus-model gap a quarter the size of the
whole field.

**And it is eleventh of twenty-four on bits**, which is the point of printing
both. [[2026-08-13-a-ranking-is-a-property-of-a-metric]] was written because
every published ranking here was an accuracy ranking that never said so; this is
the first new model whose two columns were read together *before* anything was
claimed, and they disagree by ten places. `grammar-001` is fourteenth on
accuracy and first on bits. There is no ranking of these models, only a ranking
under a metric.

The mechanism for the bits result is not mysterious and was not a surprise: this
model votes for **one symbol** with a gated confidence. A rule that fires puts
its whole vote on a single label, so when it is wrong the mass on the truth is
whatever the back-off had, and there is no second candidate to catch it.
Pointers spread mass over several nodes and are rewarded for being unsure
between two rather than wrong. Accuracy cannot see that difference and bits is
made of it.

**Two controls that could have failed and did not:**

* **Contract match.** This row was first produced under `tasks = "lm,node"`
  while every published row is `node` alone, which is a difference in the
  contract and not in the model. Re-run with `--tasks node`: `label_acc 0.404`,
  `label_bits 7.433`, `type_acc 0.863` — identical to four decimals. The row is
  comparable.
* **Type head.** 0.863 against a 0.860 structural floor, a lift of **+0.023**.
  Small, and positive, which matters because `RESEARCH_LOG.md` records that only
  two of nineteen models were ever positive there — `corefer` (+0.612) and `rgt`
  (+0.395, a network) — and every other model that looked good at type was
  reproducing a lookup. This one is barely above the lookup, and should be
  described that way rather than as a third success.

## What this row is not

**It is not a reasoning result, and the renaming column says so.** 0.406 → 0.034
under a symbol permutation, a drop of **−0.372** — second only to
`ensemble-001`'s −0.429, whose entire 1.14-bit headline turned out to be
vocabulary memorisation. 356 of this model's 444 label rules are symbol-keyed
maps. Offered a table over symbol identities and a structural copy, the
cross-fitted verifier preferred the table nearly everywhere, because on this
curriculum the table verifies better out of fold.

So the honest summary is the one this repo has had to write before: **the best
accuracy in the table belongs to the second-least equivariant model in it.** The
0.047 is real, it survives held-out verification, and it is bought with
vocabulary. How much it is bought with is measured in the next section rather
than inferred from the rule census.

**The control in the same hypothesis class was run**, and it prices the trade
exactly. `frontier-nomap` is the identical search with the `map` form removed:

| | `frontier-001` | `frontier-nomap` |
|---|---:|---:|
| `label_acc` | **0.4042** (1st of 24) | 0.2954 (11th) |
| `label_bits` | 7.433 | 8.541 |
| renaming | **−0.372** | **−0.066** |
| `type_acc` | 0.863335 | 0.863335 |

So the map form is worth **+0.109 accuracy and 1.11 bits, for 0.306 of
equivariance.** `frontier-nomap` sits with the equivariant models (`ilp` −0.021,
`omegaclaw_rank` −0.017) and beats `brill`'s 0.290 while being unable to reach
the derivability channel at all. Two models, one search, one form apart — which
is the comparison this repo asks for and rarely gets.
