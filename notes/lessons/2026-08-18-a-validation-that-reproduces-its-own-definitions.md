---
title: I built a validation whose "measured" column was computed from the same expression as its "predicted" column
date: 2026-08-18
author: lead
status: provisional
tags: [lesson, metrics, validation, tautology]
---

## The mistake

I derived a closed form unifying two certification results —

```
realised = recall / f_flagged        ceiling = 1 / f_needed
```

— and tested it against eleven measured numbers spanning **1.02× to 29,389×**,
five orders of magnitude. Worst relative error: **1.2%**. It read like a strong
confirmation of a general law.

**Seven of the eleven rows were identities.** For maintenance,
`aim = (1−base)/(flagged × (1−base))` *is* `1/f_flagged` by construction of the
targeting setup. For the curriculum rows, `predicted` rearranges to
`(1 − a_abstained)/(1 − base)`, which is the expression `aim` was computed from
in the first place. Those rows reproduce the definitions of their own inputs and
could not have disagreed. The 1.2% was rounding in hand-entered constants.

The genuinely independent rows — where the *measured* value comes from timings
and USD while the *prediction* comes from invalidation counts — number **five**,
and all five were already `HANDOVER.md` §3b's own arms confirming §3b's own law.

## Why it was hard to see

Because the algebra was **correct**. Nothing was wrong with the derivation; what
was wrong was calling it a test. A rearrangement of a definition agrees with the
definition to machine precision, and machine precision looks exactly like a
strong result — better than a real one, which would have noise in it.

> **A suspiciously small error is evidence of a tautology, not of a law.** The
> 1.2% should have been the tell: five orders of magnitude of physical
> measurement do not agree that well.

## The guard

For every row of a validation table, name **the two paths** the number came from
and check they are different:

1. What computed the *measured* column?
2. What computed the *predicted* column?
3. Does (1) consume any quantity that (2) also consumes, through the same
   expression? If yes, the row is an identity — label it, and do not count it.

And when a derivation turns out to be algebra, **say so and stop**. A derivation
is worth publishing as a derivation. It is not worth publishing as eleven
confirmations, and the difference is the only thing a reader can use.

Related: [[control-that-must-fail-before-a-result-counts]] — a control that
cannot fail and a validation that cannot disagree are the same defect;
`notes/lessons/2026-08-18-a-ratio-whose-ceiling-depends-on-k-cannot-compare-two-ks.md`.
