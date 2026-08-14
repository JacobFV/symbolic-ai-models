---
date: 2026-08-13
author: lead
status: measured
---

# A slice is a different curriculum, and it has inverted results eight times

Every confident wrong result this repo has published came from measuring a
*sample* of the world rather than covering it. The count is eight, three of them
in one day.

| claim, from a slice | what the full run said |
|---|---|
| "no rule-based model clears the label floor" (6 lessons) | nearly all of them do |
| the 6-lesson slice ranked the models **close to backwards** | — |
| `peer` collapses 0.141 → 0.005 under EM, subsumed by `mirror` (3 lessons) | `peer` keeps 26%, loses less than `prev` or `echo` |
| turning off `structural_fallback` costs `vsa` **two thirds** of its accuracy (3 lessons) | 0.219 → 0.200, i.e. **9%** — overstated sevenfold, and already in a commit message |
| `I(d)` plateaus at **2.35 bits**, a constant-latent signature | mostly plug-in estimator bias; the controlled term is **0.31** |
| `test_encoding_is_lossless` passes | its fixture drew episodes with no underscore, so a tokenizer deleting `_` went unseen |
| the seeding 2x2's *positive* lifts (12 lessons) | every arm is **below** the label floor at 179; only the ordering survived |
| a +0.051 renaming drop for the permutation VSA (24 episodes) | +0.008 at 192 episodes, +0.010 on the full curriculum |
| Indo-European ranks at the median, Spanish nearest Chinese (7 packs) | at 46 languages a real, if weak, family signal appears |

**Why:** lesson families differ enormously in which structure is available, so a
handful of them re-weights every model's strengths. The tokenizer case is the
same error wearing a fixture instead of a lesson set; the `I(d)` case is a third
form — a raw curve read without the null that says what the number is when no
signal exists.

**The rule, and it is absolute:** a slice or scratch script may form a hypothesis
and **may never appear** in a commit message, a docstring, `RESEARCH_LOG.md` or a
report. Only the full sweep reports. When a slice result is startlingly large,
expect the full run to cut it by roughly an order of magnitude — and say so
*before* running it.

**The variant that catches people twice:** do not pin a constant measured on one
slice into a test that runs on another fixture. A test asserting the curated
ontology's 0.68 imbalance failed on a three-lesson fixture where it is 0.47. The
imbalance is the invariant; its size is not.
