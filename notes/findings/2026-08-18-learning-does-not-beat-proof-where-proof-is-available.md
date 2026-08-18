---
title: The learned gate captures 11.1% of the routing headroom at zero accuracy loss and the hand-written provable gate captures 13.7% — learning only wins once it is allowed to be wrong
date: 2026-08-18
author: lead
status: superseded-in-part
tags: [routing, learning, cost, refuted-prediction]
---

## What was asked

The routing finding ended by saying the next arm is a gate *allowed to be wrong*,
scored on the constrained objective — cheapest arm above an accuracy bar, not the
raw ratio, because the raw ratio has a perverse regime far above the floor.

## The setup

Nine solver-free features (the slack ratio the hand gate thresholds on, datalog's
reachability, bridge and fleet counts, spreads, flooded share), a logistic
regression fitted by plain gradient descent, and the repo's standing splits:
**fitted on seeds 0–799, threshold tuned on a development split from 500,000,
reported once on evaluation seeds from 1,000,000.**

The constraint on the features is doing real work and is worth stating: **a gate
may only read what is already on the table.** The best predictor of "does the
cheap answer match the full answer" is *the full answer*, and it is not
available. Everything the gate sees is a proxy.

## Prediction, before the numbers

Stated in advance: the learned gate at accuracy ≥ 0.99 costs **0.88–0.93 C**
against the hand gate's 0.955 C; it will not reach accuracy 1.000 at any
threshold that saves anything; and the dominant weights will be
`laden_over_min_limit` and `reachable`, both negative.

**Two of three wrong.** It does reach 1.000. The saving is 0.94 C, not 0.88–0.93.
The weight signs were right — `reachable = −2.01`, `laden_over_min_limit = −1.02`
— but `bias = +2.17` dominates both, and `spread_limits` and `n_bridges` outrank
the slack ratio.

## Measured — one run, eval seeds 1,000,000–1,000,399

| arm | acc | $/episode | cheap share | headroom captured |
|---|---|---|---|---|
| always full | 1.000 | 1.312e-08 | 0.000 | 0.0% |
| **hand gate (provable)** | **1.000** | **1.248e-08** | 0.133 | **13.7%** |
| learned gate, bar 1.00 | 1.000 | 1.260e-08 | 0.115 | **11.1%** |
| learned gate, bar 0.99 | 1.000 | 1.235e-08 | 0.145 | 16.6% |
| learned gate, bar 0.95 | 0.975 | 1.137e-08 | 0.250 | 37.7% |
| learned gate, bar 0.90 | 0.905 | 9.861e-09 | 0.407 | 70.2% |
| ORACLE gate (cheats) | 1.000 | 8.478e-09 | 0.542 | 100.0% |

All rows from **one** run. The baseline moves ~4% between runs under machine
contention, and an earlier draft of this compared a hand-gate number from one run
against a learned-gate number from another — which would have reversed the
headline.

## What it says

> **Learning does not beat proof where proof is available.**

At zero accuracy loss the hand-written gate — two provable conditions, no fitting
— captures 13.7% of the headroom and the learned gate captures 11.1%. The learner
is *more conservative* than the proof, because a threshold tuned to never be
wrong on a development split has to leave margin for cases it has not seen,
whereas a provable condition needs none.

The learned gate wins only once permitted to be wrong: 16.6% at a 0.99 bar,
37.7% at 0.95, 70.2% at 0.90. That is a real and useful frontier — but it is a
frontier of *accuracy sold for cost*, and the constrained objective is what makes
the price visible. The unconstrained ratio would simply have picked the bottom of
the table.

## The ceiling, and why 83% of it is unreachable

The cheap answer is **already correct on 54.2%** of evaluation worlds, worth a
**35.4% cost saving at zero accuracy loss**. The learned gate takes 14.5% of
worlds; the hand gate 13.3%.

So roughly **41 percentage points of safe cases are left on the table**, and not
for want of a better learner. Those are worlds where the cheap answer *happens*
to agree — the bridges did not bind, or every vehicle failed on capacity anyway —
and no cheap feature distinguishes "agrees by construction" from "agrees by
luck", because what distinguishes them is the full answer.

> **Coincidental agreement is not routable.** A router can only safely capture
> the cases where cheapness is *decidable from cheap features*.

## What would have refuted it

- **Tuning on evaluation.** The threshold is chosen on a development split from
  500,000; evaluation seeds from 1,000,000 are read once, at the end.
- **Comparing across runs.** Caught mid-analysis and redone in one run; the note
  above records it because the cost baseline is noisy enough to have flipped the
  result.
- **The oracle being unreachable in principle.** It is not an upper bound on
  *accuracy* — every gate here scores 1.000 at the top bar — it is an upper bound
  on *cost*, computed by letting the gate see the label. That is why it is
  labelled as cheating.

## What is not established

Nine features and a logistic regression is the smallest honest learner, not the
best one. A stronger model might close some of the 83%, and the argument that it
*cannot* close much rests on the mechanism above rather than on having tried one.
The cheap test of that claim is a gradient-boosted tree on the same features; if
it captures materially more than 16.6% at bar 1.00, this note is wrong about why.

## The falsification was run, and the headline was too strong

**Superseded in part, same day.** Gradient-boosted trees on the same nine
features capture **19.3%** of the headroom against the hand gate's **14.5%**, so
*learning does beat proof on headroom*. The title of this note is wrong as
stated.

What survives, and in a sharper form, is
`2026-08-18-a-provable-gate-is-lossless-at-any-n.md`: the boosted gate buys its
extra headroom by being wrong about 1 world in 750, which is invisible at the
N = 400 this note evaluated on and stable across three disjoint 1,000-seed
ranges. The logistic model was lossless across 3,000 seeds — but only because a
conservatively tuned threshold cost it 2.5 points of headroom against the proof.

The ceiling argument in this note is unaffected: 81% of the available saving is
still unreachable, for the reason stated.
