---
title: I added a new ratio column and did not carry over the guard the old ratio column already had
date: 2026-08-18
author: lead
status: provisional
tags: [lesson, metrics, instruments]
---

## The mistake

`symbolic_ai_core/cost.py` has carried a `perverse_regime` check for a long
time: far above the floor, `$/solved-above-floor` prefers a *less capable*
system, so the table detects that and prints a warning naming both rows.

I added `aim×` — a second ratio, in the same table — and did not carry the guard
across. Measured two cycles later, `aim×` ranks an **unsound** certificate above
a sound one by **4.77×**, because relaxing a certificate cuts the flagged share
faster than it costs quality. The accuracy column caught it ($7.31e-11 against
$3.97e-10) and **nothing in the table said the two columns disagreed.**

## Why it is the same lesson twice

`notes/findings/2026-08-18-the-million-fold-advantage-is-8x-...md` already
established the rule in a third place:

> *"advantage AT FIXED QUALITY — the only comparison that is fair across
> extractors"*

Cost ratio across extractors, `$/solved-above-floor` across systems, `aim×`
across policies: **all three are ratios whose numerator and denominator both
move with quality, and all three prefer the worse system in some regime.** The
repo had learned it twice and I rebuilt it a third time within a week, in code I
wrote specifically to be careful about floors.

## The general shape

> **A new ratio column inherits every pathology the old ratio column had.** The
> guard is not a property of the particular metric; it is a property of *being a
> ratio in a table that gets sorted*.

Adding one is not a small change even when the arithmetic is obvious, because
the arithmetic was never the hard part — the sorting is.

## The guard

When adding a derived column to a comparison table, before writing the
docstring:

1. **Find every existing warning in that table** and ask whether the new column
   can trigger the same failure. `grep` for the warnings, not for the metrics.
2. **Construct the adversarial row deliberately** — the system that scores best
   on the new column while being worst on the old one — and check the table says
   something. If it cannot be constructed, say why in a test.
3. **A bound is not a system.** The oracle row initially suppressed the warning
   because it had both the best `aim×` and a perfect rate; it is attainable only
   by knowing the answer being certified. A ledger of systems that contains an
   oracle ranks the unbuildable first and hides the real comparison.

Related: [[audit-the-floor-before-quoting-a-lift]],
`notes/lessons/2026-08-18-a-ratio-whose-ceiling-depends-on-k-cannot-compare-two-ks.md`
— that one was a ratio whose *ceiling* moved with the sample; this is a ratio
whose *ranking* moves with quality. Same family.
