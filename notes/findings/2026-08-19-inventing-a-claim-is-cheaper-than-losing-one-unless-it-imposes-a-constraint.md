---
title: Inventing a claim is cheaper than losing one — unless the claim imposes a constraint
date: 2026-08-19
status: measured
arm: reader-sensitivity
---

`L_reader = Σ sᵢ Lᵢ` failed as a training weight because a margin-scaled update
over-predicts the upweighted class: it protects a critical claim by inventing
one. That finding named the fix — "a calibrated loss and a **separate, higher
price on false positives**". This derives that price instead of assuming it, and
the assumption turns out to be backwards.

The measured `sₚ` was always a *deletion* sensitivity. Its mirror had never been
measured:

    sₚ⁻ = P(answer changes | one TRUE claim of p is deleted)
    sₚ⁺ = P(answer changes | one FALSE claim of p is inserted)

If they are equal, sensitivity **cancels** in the decision rule and the optimal
assertion threshold is 0.5 for every predicate. If they differ, expected cost is
minimised at `θₚ = sₚ⁺ / (sₚ⁺ + sₚ⁻)` — a per-predicate threshold **derived from
the kernels**, not tuned, and the form in which downstream importance can reach a
reader without deforming its training.

Falsehoods are plausible by construction: a role re-pointed at another entity of
the same type in the same world, or a quantity scaled by 0.5–2.0. A claim about
an entity appearing nowhere is a false positive no reader would emit and no
kernel would be fooled by. `runs/asymmetric_sensitivity.json`.

## The asymmetry, and it is signed the other way

| domain | predicate | `s⁻` delete | `s⁺` invent | ratio | **θ** |
|---|---|---|---|---|---|
| flood | `flooded` | 0.129 | **0.200** | **1.55** | **0.608** |
| | `bridge_on` | 0.130 | **0.172** | **1.32** | **0.570** |
| | `depot` | 0.850 | 0.744 | 0.87 | 0.467 |
| | `load_limit` | 0.130 | 0.100 | 0.77 | 0.435 |
| | `needs` | 0.850 | 0.615 | 0.72 | 0.420 |
| | `link` | 0.144 | 0.068 | 0.47 | 0.321 |
| | `mass` | 0.633 | 0.178 | 0.28 | 0.219 |
| | `capacity` | 0.633 | 0.089 | 0.14 | 0.123 |
| | `demand` | 0.850 | **0.000** | 0.00 | 0.000 |
| solvency | `revenue` | 0.328 | 0.133 | 0.41 | 0.288 |
| | `owns` | 0.550 | **0.000** | 0.00 | 0.000 |
| scheduling | `duration` | 0.171 | 0.122 | 0.72 | 0.417 |
| | `capacity` | 0.350 | 0.181 | 0.52 | 0.340 |
| | `has_capability` | 0.179 | 0.050 | 0.28 | 0.217 |
| | `needs_capability` | 0.350 | 0.095 | 0.27 | 0.214 |

**Predicted: a false road is worse than a missing one**, because flood's network
is cyclic and absorbs a deletion while an invented route cannot be absorbed.
**Wrong** — `link` comes in at 0.47, less than half as damaging to invent as to
lose. And it is wrong the same way almost everywhere: `s⁺ < s⁻` in 13 of 15
cases.

θ spreads 0.000–0.608 in flood, 0.214–0.417 in scheduling, 0.000–0.288 in
solvency. **A uniform 0.5 rule is wrong, and it is wrong by being far too
conservative.**

## The mechanism, and the two exceptions that prove it

These tasks are **constrained selection**: a route to choose, a packing to find, a
sum to compare. A missing fact removes something the kernel needed. An invented
fact only matters **if it becomes binding** — an extra road that is not on the
best route, an extra capability nobody needs, an earlier filing that is not the
latest, costs nothing at all.

The two predicates with `s⁺ > s⁻` are exactly the ones that **impose
constraints** rather than supply capacity:

- **`flooded`** (1.55) — a spurious closure shuts a road that is open;
- **`bridge_on`** (1.32) — a spurious crossing puts a weight limit where the
  route had none.

And the two at exactly **0.000** are the purest capacity claims: an invented
`owns` adds a member with no filings, and an invented `demand` is not the one the
query asks about.

So the design rule, derived rather than asserted:

> **A reader feeding a constraint solver should assert on weak evidence for
> claims that supply capacity, and demand strong evidence only for claims that
> restrict it.**

## It also closes the earlier failure

The weighted-objective arm lost 0.200 end-to-end on flood, and the entire loss
was `needs` precision falling 1.00 → 0.79 under a weight of 1.61. `needs` has
`s⁺ = 0.615` — among the highest false-positive sensitivities in the domain. The
objective upweighted a predicate whose invented claims are expensive, and a
margin scale produces exactly over-prediction. **Both halves of that failure are
now measured rather than inferred**, and the correct form is a threshold on a
calibrated belief, not a weight on a loss.

## What would have refuted this

Every θₚ landing near 0.5. Sensitivity would then genuinely cancel, a uniform
rule would be optimal, and the `L_reader = Σ sᵢ Lᵢ` line should be closed rather
than reformulated. The spread is 0.608 in flood, so it is not that.

## What this does not yet show

The thresholds are **derived and unapplied**. Whether asserting at θₚ on a
calibrated belief beats asserting at 0.5 end-to-end is the next measurement, and
it needs the calibrator that now exists on the reader plus a regime where the
reader's beliefs are not all 1.0 — which on these surfaces means the unseen-
phrasing split, since six documents saturate everything else.
