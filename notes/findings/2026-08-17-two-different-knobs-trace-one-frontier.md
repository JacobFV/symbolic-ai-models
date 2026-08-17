---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-a-knob-inert-in-one-column-is-a-lever-in-another,
          2026-08-13-a-ranking-is-a-property-of-a-metric,
          2026-08-11-abstention-falls-back-to-the-structural-prior]
---

# The mechanism story was right and the prediction from it was wrong: two structurally unrelated knobs trace one accuracy/equivariance frontier

Yesterday's finding said `vote_sharpness` helps equivariance **by demoting
`map`** — the memorising rule form, which looks a symbol up in a table fitted at
training time and is therefore stale under a renaming, where `copy` carries
whatever symbol is there now.

That is a mechanism claim, so it makes a prediction: demoting `map` *directly*
should buy the same equivariance **at less cost to accuracy**, because the `copy`
votes would stay sharply discriminated among themselves instead of being blunted
against each other. I added `map_vote_weight` (a multiplier on the mass a `map`
rule contributes; 1.0 is inert) to test exactly that.

## The mechanism holds

At the sharp setting, demoting `map` moves the renamed column:

| `map_vote_weight` | acc | bits | renamed |
|---:|---:|---:|---:|
| 1.0 | 0.4376 | 6.392 | 0.2601 |
| 0.5 | 0.4288 | 6.398 | 0.2754 |
| 0.25 | 0.4108 | 6.440 | 0.2976 |

+0.0375 of the 0.049 that sharpness buys, from a knob that touches nothing but
the `map` form. The story about *which* votes flattening is suppressing is
confirmed by an instrument that suppresses only those votes.

## The prediction from it does not

Matched on renamed, the two knobs are the same curve:

| renamed | via `vote_sharpness` | via `map_vote_weight` | Δ acc |
|---:|---|---|---:|
| 0.2601 | 4.0 → 0.4376 / 6.392 | 1.0 → 0.4376 / 6.392 | 0.0000 |
| 0.2754 | 2.0 → 0.4286 / 6.405 | 0.5 → 0.4288 / 6.398 | **+0.0002** |
| ~0.297 | 1.0 → 0.4187 / 6.429 | 0.25 → 0.4108 / 6.440 | **−0.0062** |

Identical to four decimals in the middle, and at the strong end demoting `map` is
*worse* than flattening, not cheaper. There is no free lunch here: equivariance
is bought with accuracy at a fixed exchange rate, and it does not matter which of
two structurally unrelated levers you pull.

That is a stronger statement than the one I set out to make. A mechanism can be
the correct account of *what* a knob does and still say nothing useful about
*how efficiently* it does it — the frontier is a property of the model's
hypothesis mixture, not of the knob. Two knobs on one frontier is the parameter
version of the same lesson that keeps arriving: the interesting object is the
trade, not the setting.

## The extended sharpness curve saturates, so there is no model to register

Pushing sharpness below the 0.5 that `frontier-pointflat` settled on:

| sharpness | acc | bits | renamed |
|---:|---:|---:|---:|
| 0.5 | 0.4085 | 6.448 | 0.3048 |
| 0.25 | 0.4028 | 6.465 | 0.3055 |
| 0.125 | 0.4007 | 6.471 | 0.3055 |
| **0.0** (uniform: one vote per matching rule) | 0.3923 | 6.478 | **0.3070** |

The remaining headroom is **0.0022** of renamed accuracy for 0.0162 of accuracy —
the curve has flattened out. `frontier-pointflat` at 0.5 already holds 99.3% of
what going all the way to a uniform vote would give. **A null, and it is the
useful kind**: it closes this knob rather than licensing another descendant.

## `map_vote_weight = 0.0` is an abstention artefact, and it ranks 7th

| | acc | **bits** | renamed | **drop** |
|---|---:|---:|---:|---:|
| `map_vote_weight=0.0` | 0.3169 | **8.431** | 0.2957 | **0.0168** |

Silencing `map` entirely leaves nodes where only `map` rules matched with no
mass at all, so they abstain and fall back to the structural prior — bits blow
out from ~6.4 to **8.431**, two full bits worse than every other row in the
table, and the renaming drop collapses to 0.0168 because the model is barely
predicting anything to lose.

Ranked by the equivariant objective alone it sits 7th of 16, above the sharpness
settings that are genuinely better models. This is
`quote-accuracy-bits-and-renaming-together` catching a live one: a row that looks
mid-table on the objective and is the worst row present on a column the objective
does not read. Rank on one number and this gets promoted.
