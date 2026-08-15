---
date: 2026-08-15
author: agent-r090
status: measured
related: [2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model,
          2026-08-15-the-concentration-reversal-survives-its-size-has-no-unextrapolated-estimate,
          2026-08-14-the-mask-rate-curve-moves-the-opportunity-not-the-ability,
          2026-08-13-slices-have-inverted-results-eight-times,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# Conditioning on something the knob controls does not hold the question fixed

## The mistake

`label_acc` was decomposed into `acc | copyable` and `acc | not copyable`, and
the two conditionals came back flat across three mask rates while the pooled
number fell. The reading written down was: *the mask rate moves the opportunity
to copy, not the ability — the models convert supply at a fixed rate.*

The decomposition is right. The word "fixed" is not. **Copyability is defined by
whether a *visible* node carries the answer, and the mask rate is what decides
which nodes are visible.** So the conditioning event is a function of the knob,
and holding it does not hold the question: at `mask_rate=0.90` the copyable
bucket is 30% of the fills instead of 72%, and the 30% that survive are the
labels repeated often enough to leave a visible copy. `acc | copyable` rose
0.4936 → 0.5971 with nothing about the model having changed.

## What it cost

An open question that stood for a day naming three candidate stories with
opposite implications, and a headline — "the ability is flat" — that had to be
half-retracted. Worse, three defensible conditionings of the *same* fills give
three different signs:

| held constant | `acc \| copyable`, 0.15 → 0.90 |
|---|---|
| nothing (pooled) | **rises** 0.494 → 0.597 |
| label multiplicity, m ≥ 5 | **flat**, 0.490 → 0.501 and 0.690 → 0.692 |
| evidence concentration v/V | **falls**, below 0.15 in all four shared bands |

The pooled version is the one that got published, and it is the one with no
control in it.

## The guard

**When a decomposition conditions on a property the manipulated variable moves,
the bucket's composition is part of the result and has to be reported with it.**
Concretely, and all three are cheap:

1. **Report the mix, not only the accuracy.** One row of "share of the bucket per
   stratum" beside every conditional accuracy. In this case the share of the
   copyable bucket whose label occurs ten or more times went 22.1% → 42.1%, which
   is two thirds of the movement, visible without any model at all.
2. **Read the floor's column in the same bucket.** A structure-only lookup cannot
   get better at copying, so if *its* copyable accuracy moves, the population
   moved. `split_floor` went 0.158 / 0.159 / 0.158 / **0.183** across the four
   rates — flat for three and then up exactly where the model's went up. This is
   the single cheapest test and it needs no stratification.
3. **Ask what the conditioning event is a function of.** If the answer includes
   the knob, the conditional is a mixture whose weights the knob controls, and
   "flat" is a claim about the weights as much as about the model.

Guard 2 generalises past this note: **any floor worth having is a fixed-ability
predictor, so a floor that moves when a knob moves is telling you the question
changed.** This repo already refits its floors per arm; it had not been reading
the refitted values as a signal in their own right.

And it has a sharper form, found by the refuter sent at this finding: **score the
*old arm's own fitted weights* on the new arm's draw.** The tokenizers are
byte-identical across mask rates, so this needs no refit and no floor — and it is
the cleanest fixed-ability predictor available, because it is literally the same
model. Frozen at its 0.15 values, `corefer-001` gains **+0.1038** of
`acc | copyable` on the 0.90 draw against the 0.90 arm's own +0.1035. When a
conditional moves, ask what a *frozen copy of the same model* would have scored
on the new draw before asking what changed about the model.

## The corollary, from the refutation: standardisation needs its own null

**4. Run an ability-free predictor whose accuracy is an exact function of the
covariate through the identical standardisation machinery, and require it to come
out at zero.** For `v/V` that predictor exists and is trivial — a uniform pick
among the visible labelled nodes is right with probability exactly `v/V` — so
under exact matching its shortfall is *mathematically* zero, and any other answer
is a bug in the standardisation rather than a fact about anything.

The refuter's first pass returned **+0.0814** for it, from comparing a prediction
made on matched cells against an observation pooled over all of them. Every
model's shortfall was wrong by about 0.08, all of them looked plausible, and all
of them flattered the refutation they had been sent to write. Nothing else in
that analysis would have caught it.

The same null is also what *chooses the covariate*: `v`, `v/D` and `m` all flip
the sign of the effect, but they leave +0.185, +0.109 and +0.074 of residue for a
zero-ability predictor, so they are not adjusting for anything. A covariate that
cannot price its own null is not a control.

## The relation to the slice lesson

`slices-have-inverted-results-eight-times` is about reporting a sub-population as
if it were the population. This is the neighbouring failure: reporting a
sub-population *correctly*, over several settings, without noticing that the
setting is what defines the sub-population. The slice did not lie about who was
in it. It changed who was in it, quietly, between the columns of the table.
