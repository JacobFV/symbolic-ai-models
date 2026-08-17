---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-the-channel-is-walked-by-the-floor-alone,
          2026-08-17-an-average-cannot-see-a-sub-population,
          2026-08-13-a-ranking-is-a-property-of-a-metric,
          2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name]
---

# The derived bucket had only ever been measured in accuracy, and the gate assigns 0.330 to a rule that is always right and 0.318 to one that is right a fifth of the time

`agent-refuter`'s sharpest result was that **accuracy cannot see this arm's
failure mode**: a rule fitted to noise emits one of six values and is right about
1/6, which is exactly what chance reads as, so the void condition I
pre-registered could never have fired. Thirty models have been scored on this
bucket and every row was an accuracy row.

`scripts/derived_split.py` now reports **bits** on the derived bucket too. That
is the fix to the instrument; what it revealed is the finding.

## What bits shows that accuracy did not

`acc | derived, not copyable` and `bits | derived, not copyable`, same 1,325
fills:

| model | treatment acc | treatment bits | control acc | control bits |
|---|---:|---:|---:|---:|
| `frontier-008` | **0.989** | **2.363** | 0.143 | 9.281 |
| `frontier-001` | 0.532 | 5.663 | 0.072 | 9.710 |
| `frontier-nomap` (abstains) | 0.000 | **10.166** | 0.000 | **10.161** |

**`frontier-nomap` is the abstention baseline** — it has no `map` rules, fires on
nothing here, and lands on the shared back-off at ~10.16 bits in *both* arms.
That is the number every other row should be read against.

**One correction to how I relayed the refutation.** I wrote that in the control
the model is "confidently wrong". It is not: **9.281 is better than abstaining**
(10.161). It is mildly informative and useless at argmax — which is a different
and more interesting thing, and the distinction is exactly what bits was added to
make visible. Overstating it in the direction of the more dramatic reading is the
error the column exists to prevent.

## The finding: the gate is blind to the sub-population

Restricting to the fills where the model's label rule actually fires:

| arm | the firing rule's argmax | **the gate it is given** |
|---|---:|---:|
| `derive:wordnet` | **87 / 87 = 1.000** | mean **0.330**, max 0.420 |
| `derive:wordnet-perm` | 0.205 | mean **0.318**, max 0.405 |

**The same gate, for a rule that is right every single time and a rule that is
right a fifth of the time.** The model's confidence carries no information about
which arm it is in, while its argmax carries almost all of it.

The mechanism is the one this repo has now hit three times in one day. The gate
is `MassCalibrator` keyed on the rule's `score` — its held-out precision — and
the carrying rule is a 399-entry table whose score is ~0.66 *averaged over the
whole curriculum*. On the derived sub-population that same rule is right 1.000;
elsewhere it is worse. The gate prices the rule by its average, and **an average
cannot see a sub-population** — the same sentence that explained
[[2026-08-17-an-average-cannot-see-a-sub-population]] for the resolver choice and
then the precision floor, now landing on the third component.

It is also the repo's oldest complaint arriving at a new model.
[[2026-08-13-a-ranking-is-a-property-of-a-metric]]: *"a model that knows the
answer is one of ten has argmax accuracy 0.1, so it keeps a tenth of the mass and
hands the rest to a unigram."* Here it is the mirror image — a model that knows
the answer **exactly** keeps a third of the mass and hands two thirds to the
back-off.

## What is available

At mean gate 0.330 with a perfect argmax, the bits floor from calibration alone
is **1.60**; measured over the whole bucket it is 2.363. So **roughly 1.6–2.3
bits are recoverable on this bucket by calibration and nothing else** — no new
rule, no new atom, no change to what the model believes, only to how much of its
mass it is allowed to put there.

The obvious shape is a gate conditioned on more than the pooled score. What
"more" should be is not obvious and should not be guessed: the honest candidates
are the rule's identity, its guard, or a per-guard recalibration, and they differ
in how much they can overfit. That is a pre-registration, not a paragraph here.

## What this does not change

The **accuracy** result stands exactly as the refuter left it: 0.989 against
0.143, reproduced from clean, back-off contributing zero. Bits does not overturn
it — it says the model's *decision* is nearly perfect on this bucket and its
*estimate* is not, which are the two quantities this repo has insisted on
printing together since `a-ranking-is-a-property-of-a-metric` and which have
never before been printed together **on this arm**.
