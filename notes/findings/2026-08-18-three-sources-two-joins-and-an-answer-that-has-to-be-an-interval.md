---
title: Three filed sources, two identifier joins, 347 µs per portfolio — and the answer has to be an interval, 38.9 points wide at the median
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
