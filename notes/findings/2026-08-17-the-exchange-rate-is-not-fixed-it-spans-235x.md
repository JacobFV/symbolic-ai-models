---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-two-different-knobs-trace-one-frontier,
          2026-08-17-a-knob-inert-in-one-column-is-a-lever-in-another,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# "A fixed exchange rate" was true inside one knob's range and wrong across the front, which spans 235x — and 4 of the 5 Pareto-optimal models are this week's chain

An hour ago I committed the phrase *"equivariance is bought with accuracy at a
fixed exchange rate"*. It was measured with two knobs on one model over a narrow
range. This is the wider check, against every scored model, and it says two
things — one that supports the week's work and one that corrects me.

`scripts/trade_frontier.py` takes each model as a point in
(`label_acc`, `renamed_label_acc`) and computes the Pareto front. 44 models have
both columns.

## The trade is a model property, not a task constraint

That was the thing worth being wrong about: if all 44 lay on one curve, the whole
pointer arc had been sliding along a constraint of the curriculum rather than
pushing one. They do not. Of 17 families, **15 sit strictly under the front**:

| family | n | shortfall | via |
|---|---:|---:|---|
| `corefer` | 3 | **0.0000** | `corefer-mass` |
| `frontier` | 20 | **0.0000** | `frontier-floortype` |
| `omegaclaw` | 3 | 0.0015 | `omegaclaw_rank-001` |
| `routes` | 1 | 0.0340 | `routes-001` |
| `cart` | 3 | 0.0392 | `cart-noop` |
| `softreason` | 3 | 0.0917 | `softreason-onehop` |
| … | | | |
| `ctw` | 1 | 0.3392 | `ctw-001` |

(*shortfall* = how much more accuracy some other model achieves while being at
least as equivariant. Zero means on the front.)

## The front is this week's chain, and that needs a caveat stated plainly

| | acc | renamed | bits |
|---|---:|---:|---:|
| `frontier-floortype` | 0.4477 | 0.0469 | 7.082 |
| `frontier-point` | 0.4462 | 0.2476 | 7.092 |
| `frontier-pointsoft` | 0.4372 | 0.2672 | 6.457 |
| `frontier-pointflat` | 0.4110 | 0.3183 | 6.500 |
| `corefer-mass` | 0.3575 | 0.3507 | 6.793 |

Four of five are the pointer chain built this week, in order. Every step was a
genuine Pareto improvement rather than a slide.

**The caveat: effort predicts front membership almost perfectly.** The two
families with the most variants (`frontier` n=20, `corefer` n=3) hold the entire
front, and eleven of the fifteen families under it have exactly **one** model. A
family with one unturned variant cannot be expected to sit on a front. This is
*not* evidence that the frontier architecture is better than `omegaclaw` or
`cart`; it is evidence that twenty attempts beat one, which is not news.
`omegaclaw_rank-001` is **0.0015** under the front from three variants and is the
strongest untouched lead in the repo.

## The correction: the rate spans 235x

Marginal accuracy paid per unit of renamed accuracy, walking the front:

| step | Δrenamed | Δacc | **rate** |
|---|---:|---:|---:|
| `floortype` → `point` | +0.2007 | −0.0015 | **0.007** |
| `point` → `pointsoft` | +0.0196 | −0.0090 | 0.459 |
| `pointsoft` → `pointflat` | +0.0511 | −0.0262 | 0.513 |
| `pointflat` → `corefer-mass` | +0.0324 | −0.0535 | **1.651** |

The first **0.20** of equivariance costs essentially nothing — 0.0015 of
accuracy, which is noise. The last 0.03 costs 1.65 accuracy per unit, **235x**
more expensive. So "a fixed exchange rate" is a local statement about one knob's
range that I generalised without checking, which is the same error as writing up
the sharpness curve as "flat" when it was flat only in the column being ranked
by. Twice in one day, from the same habit: reporting the shape of a curve from
the segment I happened to sample.

The corrected claim: **the trade is convex and mostly cheap.** Nearly all
available equivariance is free, and only the last stretch — the stretch between
`frontier-pointflat` and `corefer` — is genuinely expensive. That reframes the
0.058 gap I have been treating as a target: it is the most costly region of the
whole front, and closing it by tuning is the worst available use of effort.

## What this licenses

Not another `frontier` descendant. The two things it points at are **(a)**
`omegaclaw_rank-001`, one variant from the front and never worked on, and
**(b)** the observation that `frontier-floortype` → `frontier-point` bought
0.2007 of equivariance for free, which suggests other families may have similarly
free gains sitting untouched because nobody has run their second variant.
