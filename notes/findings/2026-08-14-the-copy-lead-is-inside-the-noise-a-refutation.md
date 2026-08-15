---
date: 2026-08-14
author: agent-refuter-copy
status: provisional
related: [2026-08-14-the-atomspace-ir-round-trips-and-the-label-null-was-predicted,
          2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name,
          2026-08-13-the-harness-moves-more-than-the-models,
          2026-08-13-coverage-versus-accuracy-in-an-agent-column]
---

# Refutation report: `metta_perm_pure-005`'s copy lead

I did not write the work under attack. The target is one number:
`metta_perm_pure-005` at **+0.1091 copy lift** (copy acc 0.3459) against
`corefer-001`'s **+0.0959** (0.3362), `runs/metta005`, all 179 lessons, copy
floor 0.2658, copy ceiling 0.7216, n = 5,785 — quoted in
`notes/findings/2026-08-14-the-atomspace-ir-round-trips-and-the-label-null-was-predicted.md`
as *"the first thing in this repo's history to lead the copy head"*.

## Pre-registration

Written and committed **before any of my own numbers existed**, because this
repo's standing failure mode is a reading that drifts toward the write-up.

| # | hypothesis | what I predicted | what would refute *me* |
|---|---|---|---|
| 1 | the two rows answer the same question | same denominator, same exclusions, same items, by construction | any per-item key mismatch between the two models |
| 2 | the pointer inherits `structural_fallback` | it does not — `_pure` and non-`_pure` copy numbers are already bit-identical | a difference between the two rows |
| 3 | coverage-versus-accuracy | both models vote on nearly every scored node; the flat pointer back-off is not carrying either row | `metta` silent where `corefer` speaks, and scoring above the back-off there |
| 4 | **the lead is inside the noise** | the +0.0097 accuracy gap is **not** distinguishable from zero: paired 95% CI covers 0 | a CI excluding 0 and a McNemar p < 0.05 |
| 5 | the ranking is not stable | the order flips on at least one alternative evaluation mask | the order holding on every mask drawn |
| 6 | the pointer is symbol-free | `metta`'s copy accuracy is *exactly* invariant under a permutation of all 2,105 symbols; `corefer`'s is not | any drop in `metta`'s |
| 7 | the offered crosstalk mechanism | unconfirmed: the label loss will not grow with graph width | a monotone widening gap |

Hypothesis 4 is the one I expect to land, and it is the one that decides whether
"first of the pointers" may be written down.

<!-- results follow once measured -->
