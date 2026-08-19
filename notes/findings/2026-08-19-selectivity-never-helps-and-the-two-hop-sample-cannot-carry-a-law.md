---
title: Selectivity never helps — and the two-hop sample cannot carry a law
date: 2026-08-19
status: measured
arm: selective-ingestion
---

A persistent world commits, hub errors are expensive, and the cheap corroboration
check came back empty. The lever left is **refusing to write the claim**. This
sweeps the ingestion threshold on a calibrated belief and measures what it buys —
and, in the process, discovers that the composition result published a day
earlier was resting on six events.

191 two-hop chains, the same reader (logistic, so the belief is a probability),
read once and re-thresholded so every row is one reading under a different
ingestion policy. `runs/selective_ingestion.json`.

## 1. Selectivity buys nothing, at any threshold

| τ | ingested | one-hop correct | one-hop precision | two-hop correct |
|---|---|---|---|---|
| 0.00 | 1,131 | **0.183** | 0.259 | 0.021 |
| 0.60 | 1,067 | 0.178 | **0.266** | 0.021 |
| 0.70 | 1,006 | 0.173 | 0.268 | 0.021 |
| 0.80 | 930 | 0.157 | 0.256 | 0.021 |
| 0.95 | 679 | 0.115 | 0.247 | 0.010 |

**No interior maximum anywhere.** One-hop correctness falls monotonically as the
world refuses more claims, precision moves by 0.01 and then falls back, and
two-hop accuracy is flat until τ=0.8 and then drops. Predicted no interior
maximum and there is none — **selective ingestion is not a mitigation for the
blast-radius liability**, it is just a smaller world.

The precision column is the surprise: refusing the bottom 40% of claims by belief
raises precision from 0.259 to 0.268 and then *loses* it. The reader's confidence
ranks its errors (AUC 0.745–0.905 measured earlier), but not well enough that
discarding a third of the corpus is worth 0.009.

## 2. The two-hop column cannot carry the weight put on it

Two-hop accuracy of 0.021 over 191 chains is **four successes**. Yesterday's
multi-hop finding reported 0.031 (six successes) for a perceptron reader and
0.058 (eleven) for the hand reader, and concluded that composition holds "to
within 0.001".

Wilson 95% intervals:

| reader | one-hop | two-hop | k | 95% CI | `p₁²` |
|---|---|---|---|---|---|
| learned, perceptron | 0.178 | 0.031 | 6 | [0.014, 0.067] | 0.032 |
| learned, logistic | 0.183 | 0.021 | 4 | [0.008, 0.053] | 0.034 |
| hand patterns | 0.173 | 0.058 | 11 | [0.032, 0.100] | 0.030 |

**The "within 0.001" was 6 observed against 6.1 expected inside a band admitting
ratios from 0.4 to 2.1.** It is agreement at a resolution the sample does not
have. The correction is written into that note, marked, with its overstated title
left unchanged so the overstatement stays on the record.

Two things do survive:

- **The hand reader's clumping is significant, barely.** Its interval excludes
  the independence prediction by 0.002.
- **Composition is expensive whatever the exact ratio.** A reader at 0.18
  answers a two-hop question about three times in a hundred, and that follows
  from multiplying two rates near 0.18 however they are correlated.

## 3. What this changes about how to measure here

The corpus supports **1,661 one-hop questions and 191 two-hop chains**, and the
two-hop rate is a few per cent — so any two-hop finding is built on single-digit
counts and cannot separate hypotheses that differ by less than a factor of two.
**Composed-query claims from this corpus need either a much larger corpus or a
much better reader**, and quoting three decimals from four successes is the
mistake this repo's own lesson notes describe.

The one-hop column, by contrast, is 191 trials at rates near 0.18 — 22 to 35
successes — and its monotone fall across the sweep is the robust half of this
result.

## What would have refuted the headline

An interior maximum in either column. There is none, and the two-hop column is
too coarse to have shown a small one had it existed — which is itself part of
the finding.
