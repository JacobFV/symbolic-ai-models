---
title: The clumping mechanism confirms directly — reading a child predicts reading its parent, for patterns only
date: 2026-08-19
status: measured
arm: multi-hop-world
---

The clumping claim — a hand-written pattern reader beats independence on two-hop
queries because pattern success **clumps on canonically-phrased articles** —
rested on 20 two-hop successes at p=0.042, and the promotion queue said so.

But the ratio is a *consequence*; the claim is a **correlation between
neighbouring articles**, and that can be measured on every chain pair whether or
not both hops succeeded. 415 pairs, 50–73 with a correct child depending on the
reader — three times the events, testing the mechanism rather than its shadow.

`runs/neighbour_correlation.json`.

## The mechanism is there, and only where it was claimed

| reader | P(parent ok) | **P(parent ok \| child ok)** | P(parent ok \| child bad) | odds ratio | χ² p |
|---|---|---|---|---|---|
| learned | 0.087 | 0.120 | 0.082 | 1.52 | 0.533 |
| **hand** | 0.171 | **0.288** | 0.146 | **2.36** | **0.006** |

hand: both 21, child-only 52, parent-only 50, neither 292.
learned: both 6, child-only 44, parent-only 30, neither 335.

**Reading a company's article correctly makes the patterns 1.7x more likely to
read its parent's article correctly** — 0.288 against a marginal 0.171 — at
p = 0.006. The learned reader shows nothing: 0.120 against 0.087, p = 0.533.

This is the mechanism the two-hop excess implied, measured directly and at seven
times the significance. A test designed to embarrass the claim did not.

## Why it matters beyond the claim

**A reader's errors have a topology.** The patterns succeed on a *kind* of
article — the ones phrased the way a person expected when writing four rules —
and corporate parents of canonically-described companies tend to be described
canonically themselves. The learned reader's errors are spread across the graph
because its features are distributional rather than curated.

Two consequences that are not obvious from single-hop numbers:

- **A clumped reader is better at composition than its accuracy implies**, and
  the effect is large: hand at one-hop 0.176 gets 0.048 at two hops against an
  independent 0.031. Choosing a reader on single-hop accuracy alone picks the
  wrong one for composed queries.
- **It is also worse than it looks at coverage.** Its correct answers concentrate
  on a subgraph, so a world built from it is dense in one region and empty
  elsewhere — which is invisible in a marginal accuracy and shows up the first
  time a query crosses regions.

## What this does not settle

- **Two learned readers, one design.** The perceptron and logistic variants share
  their features, their mention proposer and their supervision; they are not
  independent evidence that *learned* readers are uncorrelated, only that this one
  is.
- **One relation.** Whether `headquarters` or `country` clumps the same way for
  the same reader is unmeasured, and `country`'s frames are adjacency rather than
  lexis, so there is reason to expect it to behave differently.
- The hand reader's own two-hop excess is still 20 events; what has improved is
  the evidence for *why*, not the size of the effect it produces.

## What would have refuted it

The hand reader's conditional matching its marginal — the two-hop excess would
then have come from somewhere other than neighbour correlation, and the mechanism
story would have been invention fitted to a ratio. It is 0.288 against 0.171.
