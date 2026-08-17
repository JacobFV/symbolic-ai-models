---
date: 2026-08-17
author: lead
status: measured
related: [2026-08-17-a-rule-is-verified-on-the-population-its-guard-admits,
          2026-08-17-verification-and-diversity-are-in-tension,
          2026-08-17-an-average-cannot-see-a-sub-population,
          2026-08-13-measure-before-retrying-and-before-commissioning]
---

# Five hypotheses, five pipeline stages, and every time the stage was innocent

## The mechanism

A model does not do what you want. You know the pipeline, so you look at its
stages — the proposal gate, the ranking, the reachability filter — and each one
is a plausible culprit, because each one *discards* something. You pick the most
plausible, build the variant that disables it, and it changes nothing. You pick
the next one.

What every one of those hypotheses has in common is that it blames a **stage**
for what is a property of the **objective**. A stage that discards X does so
because the objective scored X low. Removing the stage lets X back in with the
same low score, and the model behaves the same way — so the experiment comes
back null and is uninformative about the real cause, which is upstream of every
stage in the list.

The tell, in hindsight: **each variant produced a null on the target metric and
a much larger structural change than the metric reflected.** 8,786 guards
proposed instead of 5,316, and the bucket identical to six decimals. 272 rules
restored, and the single-symbol share moving 0.527 → 0.519. When a big structural
change buys nothing, the thing you moved was not load-bearing, and the next
hypothesis should not be another thing of the same kind.

## The five, in order

| # | blamed | variant | target metric | outcome |
|---|---|---|---|---|
| 1 | proposal support gate | `frontier-002` | derived bucket 0.531546 | unchanged to 6 dp |
| 2 | first-match-wins ordering | diagnostic | 0.0000 of misses blocked | no such rules exist |
| 3 | guard purity ceiling | diagnostic | map would verify at 0.625 | it would have survived |
| 4 | one resolver per guard | `frontier-003` | derived bucket 0.531546 | unchanged to 6 dp |
| 5 | reachability filter | `frontier-vote` | single-symbol 0.527 → 0.519 | 272 rules, no diversity |

Candidates 1, 4 and 5 are the same mistake three times: a stage that drops
things was blamed for the things being absent.

Candidate 4 is the interesting one because it **found a real defect** — one
resolver per guard genuinely discards a resolver that is perfect on a
sub-population, and fixing it produced `frontier-003`, which strictly dominates
`frontier-001` at 6.2× the equivariance. It still did not move the metric it was
built to move. **A variant can be a real improvement and a failed experiment at
the same time**, and the write-up has to say both.

## What was actually going on, both times

For the derived bucket: still unknown after four candidates. Recorded as unknown.

For the bits gap: the objective. A cross-fitted verifier keeps rules that agree
with the data, and rules that agree with the data agree with each other. The
rules the reachability filter drops are unreachable *because they say the same
thing as the rule that outranks them* — so restoring them cannot add
disagreement, and the measurement says it does not: 824 rules against 552, and
the median top-share of the mass stays at exactly **1.0000**.

That is the version of
[[2026-08-17-verification-and-diversity-are-in-tension]] that survives, and it is
stronger than the one that note argued: the diversity is not being *removed* by a
stage, it was never *produced*.

## The guard

Before building a variant that disables a stage, ask the cheap question first:
**would the thing that stage discards score any differently if it were kept?**
That is usually one measurement over the fitted model and it costs minutes.

- Candidate 1 needed: does a guard specific to the derived slot exist with usable
  support? (It does; that killed the hypothesis before the variant.)
- Candidate 5 needed: do the unreachable rules *predict differently* from the
  ones that shadow them? (They do not.)

Both were measurable on an already-fitted model with no new variant at all. Two
registered models and roughly an hour would not have been spent. The general
form: **a stage-removal experiment is only informative if you have first shown
that what the stage removes is different from what it keeps.**
