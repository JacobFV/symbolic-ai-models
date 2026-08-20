---
title: Every composed-query number this session was macro-averaged and none said so — micro is 2x higher and inverts the comparison
date: 2026-08-19
status: measured
arm: composed-query
---

Withdrawing the subgraph explanation for the composed-query tie showed the tie was
**a property of the metric**: macro-F1 averages 53 countries equally, so it treats
Belgium like the United States. That raised an obvious question about every other
composed-query number, since all of them — 0.138, 0.109, 0.118, 0.092, 0.036 —
were macro and none said so.

| arm | correct pairs | Gini | **macro F1** | **micro F1** | micro P | micro R |
|---|---|---|---|---|---|---|
| learned | 118 | 0.694 | 0.092 | **0.130** | **0.418** | 0.077 |
| hand | 231 | 0.638 | 0.089 | **0.201** | 0.303 | 0.151 |
| **union** | 275 | 0.593 | **0.118** | **0.225** | 0.300 | **0.180** |

## The metric was wrong in two directions at once

**It understated the capability.** Micro is **1.4x to 2.3x** higher than macro for
every arm. The union's real composed-query performance is **0.225**, not the 0.118
that has been quoted. Macro-averaging over a long tail of small countries — 53 of
them, most with three or four gold groups — drags the mean toward the countries
where a handful of articles decides everything.

**And it inverted a comparison.** Macro said learned (0.092) had caught the hand
patterns (0.089). Micro says the hand reader is **55% better** — 0.201 against
0.130 — which matches the 2:1 ratio on recovered pairs and kills the "caught up"
claim outright.

## What the two readers actually are

Micro splits them cleanly, which macro could not:

- **learned: precise and narrow.** Micro precision **0.418**, recall 0.077. When
  it answers a country it is right more often than anything else here.
- **hand: broad and looser.** Precision 0.303, recall **0.151** — twice the
  recall at three quarters of the precision.
- **union: the hand reader's reach with a little of the precision back.** Recall
  **0.180**, the best of the three, at the same precision as the patterns alone.

That is a genuine characterisation of the two error profiles, measured rather than
inferred — and it is the one the withdrawn subgraph story was reaching for and got
backwards.

## What this changes

- **Every composed-query figure in this session should be read as macro** and is
  roughly half its micro value. The corrected headline for the repo's north-star
  query shape is **micro-F1 0.225** for the union.
- **Report both.** They answer different questions — *how well is the average
  country served* against *how well is the average fact recovered* — and this
  session quoted the first while discussing the second.
- **The "learned caught the patterns" claim is withdrawn**, already recorded in
  the log's believed-and-false table.

## What would have refuted the correction

Micro and macro agreeing. They differ by 1.4x–2.3x and disagree on the ranking of
two of three arms.
