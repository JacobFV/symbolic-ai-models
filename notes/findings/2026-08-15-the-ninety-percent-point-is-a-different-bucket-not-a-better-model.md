---
date: 2026-08-15
author: agent-r090
status: provisional
related: [2026-08-15-the-ninety-percent-split-preregistration,
          2026-08-15-the-supply-model-breaks-at-ninety-percent-masking,
          2026-08-14-the-mask-rate-curve-moves-the-opportunity-not-the-ability,
          2026-08-15-the-copy-split-survives-and-its-floor-does-not,
          2026-08-14-the-label-score-is-a-copy-score,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# The 0.90 point is a different bucket, not a better model — and the ability it was supposed to vindicate was falling the whole time

**All 179 lessons, 716 evaluation episodes, `mask_rate=0.90`, `mask_mode=scatter`,
31,671 scored fills, `runs/refute-node-r090` — a from-scratch refit of the
published `runs/infill-node-r090`, whose `final`, `floors`, `renaming` and
`masking` blocks are bit-identical.** The published run keeps no weights, so the
split needed the refit; the 0.15 arm was refitted the same way into
`runs/refit-node-r015` and is bit-identical to `runs/infill-node-r015` too.

The prediction was written down first, in
`notes/decisions/2026-08-15-the-ninety-percent-split-preregistration.md`, and
committed before either arm had produced a split.

## The split

| `corefer-001` | 0.15 | 0.35 | 0.60 | **0.90** |
|---|---:|---:|---:|---:|
| copyable share (= `copy_ceiling`) | 0.7216 | 0.6799 | 0.5833 | **0.3017** |
| `acc \| copyable` | 0.4936 | 0.488 | 0.486 | **0.5971** |
| `acc \| not copyable` | 0.0034 | 0.003 | 0.004 | **0.0013** |
| `label_acc` (published) | 0.3572 | 0.3324 | 0.2850 | **0.1810** |
| predicted from the 0.15 conditionals | — | 0.337 | 0.289 | 0.151 |

`acc (all)` is asserted equal to the run's published `label_acc` to 1e-9 and the
pooled split floor to its published `label_floor` to 1e-12, so this is a
decomposition of the published number and not a second measurement of it.

**Story 1, survivorship. Pre-registered at ≈0.59 and observed 0.5971.**
Story 2 is dead in the direction that matters: `acc | not copyable` did not rise,
it **fell**, 0.0034 → 0.0013. The bound that predicted this needed no new
compute — the run's own `renaming.drop` is 0.00035, and a memorisation channel
worth 0.046 on 70% of the fills would have had to show up there as 0.032.
Story 3 was never arithmetically available: `label_acc` is computed without
reference to any floor.

## The control that could have failed, and did not

`MaskedNode.split_floor` is a `_ContextRule` structure-only lookup. It has no
ability that can improve with practice and no notion of what a mask rate is. If
`acc | copyable` rose because the model got better at copying, the floor's
copyable column should sit still.

| split floor | 0.15 | 0.35 | 0.60 | **0.90** |
|---|---:|---:|---:|---:|
| copyable | 0.1581 | 0.159 | 0.158 | **0.183** |
| not copyable | 0.1058 | 0.106 | 0.104 | **0.102** |
| pooled (= published `label_floor`) | 0.1432 | 0.142 | 0.136 | **0.1259** |

Flat, flat, flat, **+0.025** — in the same place and the same direction as
`corefer-001`'s +0.103, and in a predictor that cannot have learned anything.
The copyable bucket at 0.90 is an easier population. That is the finding.

## What makes it easier, in two numbers that were already in the batch

`label_group` already groups every labelled non-structural node by its label
string, so for each scored fill you can read off **m**, how many nodes carry that
label at all, and **v**, how many of those are still visible.
`scripts/copyable_survivorship.py` does exactly that, on the same draw.

`acc | copyable` by **m**, each cell *accuracy* then *share of the bucket*:

| rate | m=2 | m=3-4 | m=5-9 | m=10+ |
|---:|---|---|---|---|
| 0.15 | 0.167 (13.8%) | 0.504 (30.2%) | 0.490 (33.9%) | 0.690 (22.1%) |
| 0.90 | 0.377 (3.8%) | 0.615 (18.1%) | 0.501 (36.0%) | 0.692 (42.1%) |

The two large strata are unchanged — 0.490 → 0.501 and 0.690 → 0.692 — and the
**mix** moves hard: the share of the copyable bucket with a label occurring ten
or more times nearly doubles, 22.1% → 42.1%. Applying the 0.90 mix to the 0.15
accuracies gives 0.564 against 0.4936, so about **two thirds** of the +0.103 is
the mix alone. The reason is mechanical and was pre-registered: a label occurring
k times leaves a visible copy with probability about 1 − 0.9^k, which is 19% at
k=2 and 65% at k=10, so at 90% masking the copyable bucket *is* the repeated
labels.

The mix with no accuracy in it says the same thing from the other side — the
copyable share inside each m band, which is a property of the masking draw and of
nothing else:

| rate | m=1 | m=2 | m=3-4 | m=5-9 | m=10+ |
|---:|---:|---:|---:|---:|---:|
| 0.15 | 0.000 | 0.853 | 0.992 | 1.000 | 1.000 |
| 0.90 | 0.000 | 0.099 | 0.249 | 0.450 | 0.785 |

This has now been pinned as a guard —
`test_the_copyable_bucket_is_not_the_same_population_at_every_rate`. On its
40-lesson fixture, which is a different episode set from the sweep's, the mean
label multiplicity of the copyable bucket rises monotonically **9.75 → 10.55 →
11.56 → 17.05** across the four rates while the copyable share falls 0.696 →
0.665 → 0.589 → 0.301, within 0.026 of the sweep's ceiling at every rate. The
test asserts the direction of both, and no measured constant.

## The half that is not survivorship is worse for the models, not better

The remaining third does not survive the obvious control either. **v** alone is
the wrong variable, because raising the mask rate removes right answers and wrong
candidates together: the mean number of visible labelled nodes per fill falls
**61.6 → 7.3**. The quantity a pointer's job depends on is the concentration
**v/V**, and inside it the comparison inverts:

| `acc \| copyable` by v/V | 0-0.02 | 0.02-0.05 | 0.05-0.1 | 0.1-0.2 | 0.2-0.4 | 0.4-1 |
|---:|---|---|---|---|---|---|
| 0.15 | 0.187 (8.4%) | 0.341 (31.9%) | **0.525** (32.2%) | **0.662** (18.9%) | **0.792** (4.7%) | **0.960** (4.0%) |
| 0.90 | — | 0.364 (0.3%) | **0.354** (25.2%) | **0.561** (37.9%) | **0.733** (23.7%) | **0.933** (12.9%) |

In **all four bands where both rates have real mass, 0.90 is at or below 0.15.**
Carrying the 0.15 conversion rates onto the 0.90 mix predicts `acc | copyable` =
**0.696**; the model delivers 0.5971. So once the evidence is held at constant
concentration the model at 0.90 is **0.099 worse**, not better.

Coarse bands cannot rule out the 0.90 arm sitting systematically low *inside*
each band, so the size of that 0.099 is an estimate. The direction does not
depend on the banding, because the sweep already reports the same thing with no
stratification at all.

**The two supply models bracket the truth, and they miss by the same amount in
opposite directions.** Carrying the 0.15 numbers forward to predict `label_acc`
at 0.90:

| supply variable carried forward | predicted `label_acc` | observed | error |
|---|---:|---:|---:|
| binary copyability | 0.151 | 0.181 | **−0.030** |
| v/V concentration | 0.212 | 0.181 | **+0.031** |

So the +0.030 the open note could not explain is not evidence of a model doing
better than supply allows. It is a coarse supply variable undershooting by
almost exactly as much as the fine one overshoots — the bucket really did get
easier, and the model really did convert less of it.

## `copy_lift` was in every `summary.json` and says it plainly

The pointer channel, scored against `copy_floor` — the structure-only pointer
baseline, **refitted at each rate** — for the six models that have one:

| `copy_lift` | 0.15 | 0.35 | 0.60 | 0.90 |
|---|---:|---:|---:|---:|
| `corefer-001` | +0.096 | +0.057 | −0.013 | **−0.149** |
| `ptrgen-001` | +0.078 | +0.035 | −0.024 | **−0.153** |
| `vsa_perm-002` | +0.060 | +0.045 | −0.005 | **−0.164** |
| `routes-001` | +0.051 | −0.011 | −0.088 | **−0.219** |
| `ruleinduce-001` | +0.032 | −0.050 | −0.114 | **−0.230** |
| `evidence-001` | +0.023 | +0.006 | −0.042 | **−0.148** |

**Six of six fall monotonically, and six of six are negative by 0.60.** Every one
of these models is beaten by a structural lookup at picking which node corefers,
well before the extreme. `copy_acc` and `copy_floor` share the any-node
convention flagged in `the-copy-split-survives-and-its-floor-does-not`, so the
comparison is like for like.

## So does "the mask rate moves the opportunity, not the ability" survive?

**Half of it, and the half that survives is not the half that was published.**

- *Nothing is being reconstructed.* True, and stronger than before:
  `acc | not copyable` is 0.0013 at 0.90 against 0.0034 at 0.15, and the
  `renaming` drop of 0.00035 says the memorisation channel supplies essentially
  none of it. At 90% masking these models still answer only where the answer is
  already on screen.
- *Both conditional accuracies are flat, so the ability is flat.* **False at
  0.90, and the flatness at 0.35 and 0.60 was luckier than it looked.**
  `acc | copyable` is not a fixed-difficulty question: it is an average over a
  bucket whose composition the mask rate controls. Held at constant m it is flat;
  held at constant v/V it declines; pooled it rises. Three defensible
  stratifications, three different signs — which is
  `a-ranking-is-a-property-of-a-metric` arriving as a property of a
  *conditioning*, and the pooled version is the one with no control in it.
- *The supply model.* It is right in spirit and wrong in its variable. Binary
  copyability is a coarse supply measure that happens to be nearly sufficient
  while the ceiling is falling slowly, and stops being so once 90% of the graph
  is gone. The finer supply variable, v/V, overshoots in the other direction.

The 0.90 point should not be cited as the demanding end of the mask-rate curve.
It is the least comparable point on it: a third of the fills, a different mix of
labels, and an eight-fold smaller candidate set.

## What would have refuted this

- `acc | not copyable` at 0.90 coming back ≥ 0.02. It is 0.0013. *(pre-registered)*
- `acc | copyable` coming back ≤ 0.52, leaving the miss unexplained by either
  conditional. It is 0.5971. *(pre-registered)*
- **The split floor's copyable column staying flat at 0.90.** This is the control
  the whole reading rests on: a lookup table cannot get better at copying, so if
  its copyable column had not moved, the bucket had not changed and the rise
  would have been the model's. It moved, 0.158 → 0.183. *(pre-registered as the
  mechanism half)*
- `acc | copyable` rising within the large m strata rather than the mix moving.
  m=5-9 moved 0.011 and m=10+ moved 0.002.
- The v/V comparison going the other way — 0.90 above 0.15 at matched
  concentration — which would have meant a real gain in pointing. It is below in
  all four shared bands, and `copy_lift` agrees without any banding.

## Provisional, and what it is not

The conditional split and the stratifications are `corefer-001` only; the
`copy_lift` table is all six pointer-bearing models on the full sweep. **The
per-model split at 0.90 is the missing independent check** — the reading here
would be weakened by an arm in which `acc | copyable` fell at 0.90 while
`corefer`'s rose, because that would make the survivorship story a fact about one
model rather than about the bucket. It is the first thing to run next.
