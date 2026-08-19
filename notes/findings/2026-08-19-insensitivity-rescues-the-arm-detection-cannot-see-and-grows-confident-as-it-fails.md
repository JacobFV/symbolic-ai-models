---
title: Insensitivity rescues the arm detection cannot see, and grows confident as it fails
date: 2026-08-19
status: measured
arm: solvency-membership-certificate
---

## The arm that was declared unrepairable

Today's floor was the **uncued** divested-filer distractor — *"sub_98 left the
group in April"* — which has the ownership signature exactly, carries no declared
cancellation cue, and sits on a **multi-valued** role. Detection fires 0.000 on
multi-valued roles by construction, and the staleness gate needs a cue. Accuracy
0.485, unmoved by every combination built today.

The other response to a corrupt channel does not decide whether the claim is
true. It proves the **verdict does not depend on it**: is the answer the same
after removing *any single member*?

| arm | accuracy | coverage | accuracy \| certified | wrong \| certified |
|---|---:|---:|---:|---:|
| clean surface | 1.000 | 0.550 | 1.000 | 0 |
| hard `owns`, **uncued**, published reader | 0.485 | **0.485** | **1.000** | **0** |
| hard `owns`, **uncued**, consolidated | 0.485 | 0.485 | 1.000 | 0 |
| hard `owns`+filing, uncued, consolidated | 0.450 | **0.935** | **0.481** | **97** |

**On the arm nothing else could touch, certified ⟺ correct, exactly.** 0.485
accuracy with 103 silent errors becomes 0.485 coverage with **zero**. Predicted
20–40%; measured 48.5%.

## It is the monotone half, and that is all it is

Coverage is not set by the margin. It is set by **one-sidedness**: removing a
member can only *lower* the sum, so a verdict of `False` survives every deletion
for free, and a verdict of `True` survives only when no single member's filing
covers the margin. Measured exactly — it fires on **1.000** of false verdicts and
**0.000** of true ones, and the clean-surface coverage 0.550 *is* the false-verdict
share.

That is the fourth appearance of the same asymmetry in this repo: ASP's UNSAT
side being expensive, the capacity gate proving infeasibility cheaply, the flood
certificate's monotone half being the part that transferred to scheduling, and
now this. **What is cheap to prove is the negative.**

My margin diagnostic was the wrong statistic and said so loudly — median margin
0.11 of the largest filing, share above 1 of only 0.080, against a measured
coverage of 0.550. The number that explains it is the false-verdict share.

## The warning, and it is the second instance

Add a spurious **filing** — a channel the membership hypothesis does not cover —
and coverage rises **0.485 → 0.935** while accuracy among the certified falls to
**0.481**, 97 wrong.

Coverage rises *because* the corruption is larger: the spurious figure pushes the
sum clear of the threshold, so no member deletion can flip it. **A margin-based
certificate is most confident exactly when the corruption is biggest.**

This morning's flood certificate did the same thing — it certified more often on
the `hard_distractors` surface (0.127) than on the clean one (0.056), because the
phantom links added 2-edge-connectivity. Two independent instances, two different
domains, one shape. It is worth stating as a property of the whole family:

> **A certificate that asks "would a small perturbation change the answer?" reads
> a large error as stability.** Its coverage is not a measure of its own
> reliability, and comparing coverage across surfaces is a trap.

It is also the fifth appearance of *a check that reads part of the world inherits
that part's errors* — the docstring says the certificate is silent about a
spurious filing, and here is that sentence with a number on it.

## What would refute this

- The one-spurious-membership hypothesis is a bound, not a fact; two spurious
  memberships break the argument and are untested.
- `certified ⟺ correct` on the uncued arm is an identity of this population,
  not a theorem: it holds because the spurious member always pushes the sum
  **up**, so every case it corrupts is one the monotone half refuses. A
  distractor that removed revenue would invert it.
- 0 wrong in 97 certified cases bounds the error at ~3%, not at zero.
