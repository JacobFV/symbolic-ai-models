---
title: Two detectors, neither sound alone, sound together
date: 2026-08-19
status: measured
arm: combined-detector
---

## Applying this turn's own lesson to a claim I made

*"Refusing to collapse costs nothing and flags every error"* reported soundness
**1.000** for the insensitivity certificate on the hard-distractor surface,
measured at **N=60**. By the rule of three that bounds the error at 5%, and
"fires iff the enumeration decides" — which I checked at 252 — is a **different
claim** from "fires implies correct", which I had not.

At 400 seeds, 252 non-empty cases, interleaved, `hard_distractors=True`:

| policy | answers | coverage | wrong | accuracy |
|---|---:|---:|---:|---:|
| answer everything | 252 | 1.000 | 81 | 0.679 |
| role flag only | 223 | 0.885 | 75 | 0.664 |
| **certificate only** | 140 | 0.556 | **3** | **0.9786** |
| **both** | 120 | **0.476** | **0** | **1.0000** |

**The certificate alone is not sound.** Three wrong answers at 400 seeds,
invisible at the sixty it was measured on.

## The three are the same three

Seeds **64, 83, 92** — the identical cases that broke the exactness audit. All
three:

- have `role_assignment_forced = False`;
- read the **depot as a flooded region**, swapping it with one of the true
  flooded ones;
- pass the certificate, because a misread role is **not a link deletion** and
  link-insensitivity has no view of it.

So the two detectors are genuinely complementary, and the demonstration is exact
rather than statistical: the certificate's entire failure set is the role flag's
entire catch set.

| | catches | blind to |
|---|---|---|
| certificate | link sensitivity | role assignment |
| role flag | role guessing | the phantom link |
| **pair** | **both** | — |

## What it costs

Coverage **47.6%** — roughly the product of the two, since the conditions are
close to independent. Answering 120 of 252 with **0 wrong**, which bounds the
error at **2.5%**, not zero. Stated rather than rounded away, because that is the
mistake this whole sequence has been correcting.

Against the alternative of answering everything at **0.679**, the pair converts
32% silent error into 52% refusal.

## What this corrects

The soundness claim in
[[2026-08-19-refusing-to-collapse-costs-nothing-and-flags-every-error]] is
**0.9786, not 1.000**, for the certificate alone. The finding's structure holds —
carrying still discards only wrong answers on the population it measured, and the
`decided ⟺ correct` identity held there — but the sample could not distinguish
1.000 from 0.98, which is exactly the failure that finding's successors have been
finding everywhere.

Two tests pin the pairing: one asserts the certificate's failures **exist**, so
the pair does not silently become redundant; the other asserts the pair is clean.

## What would refute this

- Coverage is the price and it is high. A detector that caught role errors
  without refusing every unforced assignment would recover much of the 11.5% the
  role flag costs, since it refuses ten times more often than it corrects.
- 0 wrong in 120 is a bound, not a proof. The next sample that doubles it will
  halve the bound; nothing here says it will stay clean.
