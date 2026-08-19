---
title: Three filed sources, two identifier joins — the answer has to be an interval, and value-weighting doubles the usable fraction to one filer in four while making the worst cases worse
date: 2026-08-18
author: lead
status: provisional
tags: [federation, vertical-slice, bounds, gleif, sec-13f, self-correction]
---

## Why

Fifteen cycles of this session priced capabilities and never demonstrated one end
to end. The mandate asks for a vertical slice — input, a shared world, sources
that compose, a certificate, a price — and the ISIN→LEI bridge acquired last
cycle makes one possible for the first time:

```
13F holdings        filer (CIK) -> security (CUSIP)     2.36M edges
GLEIF ISIN->LEI     CUSIP -> LEI                        2.28M US CUSIPs
GLEIF entities      LEI -> country                      3.35M entities
```

**The question:** what is the country exposure of a 13F filer's portfolio? Real,
valuable, unanswerable without federation, and the first query in this repo that
joins on **identifiers** rather than on names.

## It runs

| | |
|---|---:|
| filers in the world | 8,759 |
| world built once | **5.8 s** |
| per portfolio answered | **347 µs** |
| positions per filer, p50 | 98 |

**And the answer cannot be a point estimate.** Most positions have unknown
domicile, so reporting "of the ones we know, X% are US" would be a silent lie —
a conditional quoted as a share. `additive_bounds` returns the **exact attained
extremes** with the assignment realising each, and the lower bound carries a
**witness**: the bridged positions whose issuer is domiciled in the country,
checkable by following two identifier joins per position with no search and no
trust in the script.

| US exposure, interval width | |
|---|---:|
| p10 | **18.0%** |
| p50 | **38.9%** |
| p90 | 71.0% |
| filers with a band ≤ 20 points *(threshold set before the run)* | **67/500 = 13.4%** |

A median-width example: 90 positions, 55 bridged, **US share in [61.1%, 100.0%]**.

**The honest capability statement:** this is a real answer with honest
uncertainty rather than a point estimate that would have been a lie — and it is
**not yet a product**. Only one filer in seven gets a band tight enough to act
on.

## Two corrections to the finding this was built on

**1. Coverage has two denominators and they differ by 2.6×.**

| | |
|---|---:|
| per **distinct security** | **22.3%** — the last finding's number |
| per **position held** | **58.8%** (72,293 / 122,907) |

Portfolios concentrate on widely-held large caps, and those are exactly the
issuers that carry an LEI. Which denominator is right depends on whether the
workload asks about *securities* or about *portfolios*; the last finding quoted
the security number while discussing the join in general. **This is the
slice-versus-population lesson in reverse** — I measured the population of
securities when the workload is positions.

**2. The "bridge, then names where it misses" row was invalid.**

That row — `f 11.42%`, **8.8×** — multiplied the *coverage* of the CUSIP→LEI join
by the *ambiguity* of the CIK→LEI name join. **Those are different joins over
different entity types**, and there is no name fallback for a CUSIP because
CUSIPs are not names. The honest figure for CUSIP→LEI alone is `f = 1 − coverage`:
**77.7%** per security, **41.2%** per position. The composite policy exists for
the *filer* alignment and not for this one.

## Value-weighted, because that is the question anyone asks

The section above counts positions equally, which the *what would refute it* list
named as its sharpest weakness: 13F reports **values**. Weighting by them first
required establishing what the column is — summing every AAPL position gives
**$3.06e12**, right for institutional ownership of a ~$3T company, where 3e12
*shares* would be 200× the float. **It is USD.**

**Coverage now has four readings, spanning 3.5×:**

| denominator | coverage |
|---|---:|
| per distinct security | 22.3% |
| per position held | 58.6% |
| **per dollar held, aggregate** | **79.1%** ($4.16T of $5.26T) |
| **per dollar held, median filer** | **58.0%** |

The aggregate is a property of a handful of giant filers who hold mostly large
caps with LEIs. **Quoting 79.1% as "the coverage" would describe Vanguard, not a
typical filer** — the slice-versus-population error in its third form here, after
the security-versus-position denominator.

**What value-weighting buys:**

| | unweighted | **value-weighted** |
|---|---:|---:|
| width p10 | 18.0% | **8.7%** |
| width p50 | 38.9% | 42.1% |
| width p90 | 71.0% | **88.2%** |
| **band ≤ 20 points** | **13.4%** | **25.2%** |

> **It helps the filers already close to actionable and hurts the ones that were
> not.** The usable share doubles to **one filer in four**; the median is flat and
> p90 gets *worse*, because one large unbridged position now dominates a portfolio
> that equal weighting had diluted across many holdings.

Better, still not a product, and the improvement is concentrated where it was
least needed.

### Two bugs, both caught by printing an example

- **Amended filings double-count.** The same filer appears twice for the same
  security (cik 2100119 holds AAPL at both 242.077e9 and 241.721e9). The value
  per `(filer, security)` is now the **max**, not the sum.
- **Filers with no reported values scored as perfectly determined.** Base 0 and
  contributions 0 give a spurious **zero-width** band. Four of 500. Caught
  because the "tightest" row printed as *1 position, 0 bridged,
  [0.0%, 0.0%]* — an answer that cannot be right. Now dropped and counted.

Printing a worked example next to a summary statistic found both. Neither would
have failed a test.

## What would refute it

- **`additive_bounds` assumes each unknown position is independent.** Two
  positions in the same unbridged issuer are not, and the bound is therefore
  wider than the truth by an unmeasured amount.
- **Bounds are unweighted by position size.** 13F reports values; this counts
  positions. A value-weighted exposure would have different bounds and is the
  question anyone actually asks.
- **Country is the GLEIF legal-address country**, which for a fund domiciled in
  Luxembourg says Luxembourg regardless of where its risk sits. The join is
  correct and the *concept* may not be the one a user means.
- **Coverage is a property of this workload.** A portfolio of small caps or
  foreign lines would bridge far less, and the 13.4% actionable share would fall.

## Reproduce

```bash
uv run python -u scripts/vertical_slice_country_exposure.py     # ~1 min
```

`runs/vertical_slice_country_exposure.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `three-source-vertical-slice`.
