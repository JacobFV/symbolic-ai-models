---
title: An error-correlation test needs a reader that succeeds — the fame prior has nothing to correlate
date: 2026-08-19
status: dead
---

The promotion queue's last open gap on the clumping result is **a genuinely
third reader**: the perceptron and logistic variants share their features, their
mention proposer and their supervision, so they are not independent evidence
that *learned* readers are uncorrelated.

A **fame prior** looked like the cleanest possible third bias: among the
capitalised mentions that are not the article's subject, name the one with the
highest corpus-wide document frequency. No phrasing, no supervision, no features
shared with anything else — success would depend on *entity fame*, which is
plausibly inherited up an ownership chain, so it could have shown that clumping
is a property of the graph rather than of pattern readers.

**It does not read.** Over 415 chain pairs:

| relation | P(correct) | successes on both ends of a pair |
|---|---|---|
| `parent` | **0.000** | 0 |
| `headquarters` | **0.000** | 0 |
| `country` | 0.014 | 1 |

The most frequent non-subject capitalised mention in a company intro is a common
noun phrase or a country, essentially never the parent. With no successes there
is nothing to correlate: the χ² is undefined or driven by a single cell, and the
`inf` odds ratios in `runs/neighbour_correlation.json` are that, not an effect.

## The requirement it exposes

**An error-correlation test needs events on both sides.** `P(parent ok | child
ok)` is estimated from the pairs where the child was read correctly, so a reader
contributes information in proportion to its *successes*, not its distinctness. A
maximally different reader that never succeeds contributes nothing at all, and
the third arm has to be **competent and different**, which is a much harder thing
to build than either alone.

Concretely, the bar: on 415 pairs, distinguishing an odds ratio of 2 from 1 needs
roughly 20 both-correct pairs, which at these rates means a reader above about
**0.15** one-hop accuracy. The hand patterns (0.171) and the learned reader
(0.092–0.212) clear or approach it; a prior does not.

## What would actually work

- **A learned reader over character n-grams only**, sharing the proposer and
  supervision but not a single lexical feature. Partial independence, and cheap.
- **A retrieval-and-copy reader**: find the most similar training article and
  copy the *structural position* of its answer. Genuinely different bias,
  genuinely more work.

Neither is built. The queue entry stays open, with the bar now stated as
competence rather than distinctness.
