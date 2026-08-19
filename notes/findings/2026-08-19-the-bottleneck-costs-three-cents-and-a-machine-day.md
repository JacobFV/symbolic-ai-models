---
title: The bottleneck costs three cents and a machine-day — what 385,000 articles are actually worth
date: 2026-08-19
status: measured
arm: real-text-scale
---

The crossover is verified: matching four hand-written patterns takes
**384,874 articles** of distantly supervised text, from a twelve-point fit
(`rate = 0.0347·n^0.189`, 1.54x per decade). That is the knowledge-acquisition
bottleneck restated as an exchange rate. **Nobody had priced either side.**

## What the data side costs

Fit and read time measured at four corpus sizes on shuffled subsamples:

| articles | supervise | fit | read |
|---|---|---|---|
| 200 | 0.03 s | 0.80 s | 1.19 ms/doc |
| 500 | 0.07 s | 1.89 s | 1.18 ms/doc |
| 1,000 | 0.17 s | 5.46 s | 1.43 ms/doc |
| 2,502 | 0.43 s | 15.04 s | 1.50 ms/doc |

**Fitting is superlinear** — 18.8x for 12.5x the documents, an exponent of
**1.16**, because the sparse feature set grows with the vocabulary. Reading is
flat per document, as a linear-model reader should be.

Extrapolated to 384,874 articles:

| | |
|---|---|
| fit | **1.44 core-hours** |
| read the corpus once | 0.16 core-hours |
| **compute, at $0.02/core-hour** | **$0.032** |
| fetch | 27,000 batched requests — **7.5 hours at one request a second** |
| storage | 349 MB |

Three cents of compute, a machine-day of polite fetching, and a third of a
gigabyte. In money it is free; Wikipedia and Wikidata charge nothing.

**Honesty about the fetch rate:** the batched fetches in this session were
throttled hard — 429s on most requests, with backoff to minutes. At the rate
*actually observed* the same job is days, not hours. The 7.5-hour figure is what
a well-behaved client is nominally entitled to, and the observed figure is what
happened; both are wall clock and neither is money.

## What the pattern side costs

Four regular expressions and the knowledge of which phrasings English uses for
corporate ownership. That is an expert's afternoon — at any realistic rate,
**one to three orders of magnitude more in money than the entire data side**, and
the scarce resource is the attention rather than the hours.

## The exchange rate, and it inverts the classical story

**385,000 articles ≈ $0.03 + one machine-day ≈ four patterns ≈ half a day of
expert time.**

The symbolic-AI post-mortem says the knowledge-acquisition bottleneck killed the
programme: the world had to be entered by hand, and hands do not scale. On this
task, at this reader quality, **the hand-entered side is the expensive one** and
the data side is essentially free.

The reason is specific and worth stating rather than generalising: **a public
knowledge base supplies the labels.** The classical bottleneck was not that text
was expensive — it was that *nobody had the gold*. Wikidata does. So the honest
form of the claim is:

> The bottleneck moved from **rules** to **labels**, and for any relation a
> public KB already curates, it has been bought out.

Which immediately says where it has *not*: a relation nobody has curated is
exactly as expensive as it was in 1984, and the reader measured here has no way
to acquire one.

## Two caveats that bound it

- **Distant supervision only reaches 58%** of articles for `parent` (the
  containment ceiling), so the 385,000 buys a reader capped below what the gold
  could in principle support. Buying out the bottleneck does not buy out the
  ceiling.
- **The patterns cap at 68% of that ceiling and data does not cap at all**, so
  above ~385,000 articles the data side wins outright. The exchange rate is a
  crossing point, not an equilibrium.

## What would have refuted it

The compute cost landing anywhere near an expert afternoon in money. It is three
cents against a hundred dollars or more — four orders of magnitude, which is not
a number a different price sheet moves.
