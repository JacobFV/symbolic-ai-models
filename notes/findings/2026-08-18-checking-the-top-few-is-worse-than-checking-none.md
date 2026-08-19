---
title: Checking the top one or two positions makes the answer strictly worse — taking uncertainty seriously has a threshold, not a gradient
date: 2026-08-18
author: lead
status: provisional
tags: [bounds, escalation, uncertainty, federation, operating-rule]
---

## Where it comes from

The federation arm ended with a construction: a lookup does not *settle* a
position, so if at most `m` of `k` resolutions are wrong, **widen both ends by
the `m` largest resolved weights**. At `m = 1` that recovered coverage from 63.3%
to **96.9%** at half the width.

Working the algebra of what I had just published turned up a consequence I had
not noticed. Resolving the `k` widest unbridged positions leaves

```
band(k) = sum(w[k:]) + 2·w[0]        against   band(0) = sum(w)
```

so the improvement is `sum(w[:k]) − 2·w[0]` = **`sum(w[1:k]) − w[0]`**.

**At `k = 1` that is `−w[0]`.** The band becomes `total + w[0]` — *strictly wider
than not resolving anything at all*. Resolving pays only once the second through
`k`th weights **together exceed the largest**.

## Measured

508 filers with ≥ 30 unbridged positions (so the `k=0` baseline is 48.6% rather
than the 43.5% of the wider sample), slack `m = 1`:

| k | median band | vs k=0 | **filers better than k=0** |
|---:|---:|---:|---:|
| 0 | 48.6% | — | — |
| **1** | **56.8%** | **+8.2%** | **0.0%** |
| **2** | 51.9% | +3.2% | **0.0%** |
| **3** | 47.8% | −0.9% | **73.8%** |
| 5 | 42.3% | −6.4% | 93.1% |
| 10 | 33.0% | −15.7% | 97.2% |
| 20 | 24.9% | −23.8% | 98.2% |
| 30 | 20.6% | −28.0% | 98.4% |

**A hump, exactly as the algebra predicts.** Not one filer in 508 improves at
`k = 1` or `k = 2`. The crossover is at **`k = 3`**, and beyond it more is
monotonically better — the optimal `k` is at the search cap for the median filer,
and only **1.6%** of filers have no `k` that beats doing nothing.

## The rule, and what it generalises to

> **With slack for one error, checking one or two positions makes your answer
> strictly worse. Check at least three, or none.**

*"Just check the top few"* is the natural instinct and it is **a regression**.

And the general form is worth more than the number:

> **Taking uncertainty seriously has a threshold, not a gradient.** A partial
> effort at resolving ambiguity is not a partial improvement — below the
> threshold it is a *regression*, and the threshold is set by the **concentration**
> of whatever is being resolved.

That is the same concentration that made the escalation product cheap
(five widest positions carry 57.5% of the width) and made it fragile
(coverage `≈ a^k`). Concentration has now paid, bitten, and set a floor — three
consequences from one property of the data.

## What would refute it

- **`m = 1` is a choice.** At `m = 0` there is no slack and the curve is
  monotone — but `m = 0` is the naive construction whose bands are true only
  63.3% of the time. The threshold exists *because* the guarantee is being kept.
- **The slack rule widens by the `m` largest resolved weights**, which is
  worst-case. A slack that accounted for *which* resolutions are likely wrong
  would be tighter and would lower the threshold.
- **Restricted to filers with ≥30 unbridged positions.** Portfolios with few
  unknowns have a different curve and were excluded to keep `k` meaningful.

## Reproduce

The measurement is a ~30-line sweep over the same three sources as
`scripts/bound_attribution.py`; numbers and method in
`notes/autonomy/predictions.jsonl` under `slack-makes-small-k-counterproductive`.
