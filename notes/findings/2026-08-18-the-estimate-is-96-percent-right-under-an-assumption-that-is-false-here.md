---
title: The estimate is right to within 5 points 95.9% of the time — under an assumption that is demonstrably false here, and that is worse than being inaccurate
date: 2026-08-18
author: lead
status: provisional
tags: [bounds, estimates, missingness, federation, refuted-prediction, epistemics]
---

## The question the whole session assumed the answer to

Every finding in this arm treats **exact bounds** as the product. But a user is
actually choosing between:

- **bounds** — right 100% of the time, usable (band ≤ 20 points) **25.2%** of the
  time;
- **an estimate** — usable 100% of the time, right *some* fraction.

If the estimate is usually close, the bounds are the worse product and the
framing needs revising. This measures it, with ground truth.

## Two measurements

**1. The estimate's best case.** Cross-validate on the **bridged** positions,
where country is known: hide 42% of them — the real unbridged rate — estimate the
country share from what remains, compare to the truth. That is
**missing-completely-at-random**, the estimate's most favourable condition, so
whatever it scores is an **upper bound** on its real accuracy.

| n = 579 filers | |
|---|---:|
| estimate within **5 points** | **95.9%** |
| estimate within 10 points | 98.6% |
| median absolute error | **0.4 points** |
| mean signed error | −0.24% (no bias) |
| **truth inside the exact bound** | **579/579 = 100.0%** ✓ |

I predicted 45–60% within 5 points, and a systematic upward bias. **Badly wrong.**
My sampling-error reasoning ignored value weighting: a few large positions carry
most of the value, so hiding 42% *by count* leaves most of the *value* visible.

**2. Whether that condition holds. It does not.**

| | |
|---|---:|
| CINS securities (letter-leading, **foreign by construction**) | 3,008 = **11.2%** of everything held |
| of those, **bridged** | **7 = 0.23%** |
| **so unbridged** | **99.8%** |

The bridge covers ISINs beginning `US`, and a foreign issuer's ISIN begins with
**its own** country code. So the unbridged set is not a random sample of
holdings — it contains essentially **every** definitionally-foreign security.
Missingness is correlated with the answer, maximally.

## The result, and why it is worse than a bad estimate

> **The estimate is nearly perfect under missing-completely-at-random, and the
> missingness here is emphatically not random. Its measured accuracy is
> conditional on an assumption that is demonstrably false, and it does not
> transfer.**

**A method that looks mediocre invites scrutiny. A method that scores 95.9%
under a condition nobody checked is more dangerous** — the number is real,
reproducible, and about a different world from the one it will be used in.

The bound has no such dependency. 579/579 truths inside it, unconditionally, and
its **width is the ignorance made visible**.

**So the session's assumption survives, and not for the reason I held it.** Bounds
are not better because estimates are inaccurate — estimates are excellent when
their assumption holds. Bounds are better because **the assumption's failure is
unobservable from inside the estimate**, while the bound's width reports the same
ignorance in a form a caller can act on.

## What would refute it

- **The MCAR test hides bridged positions**, which are systematically *more*
  US-domiciled than the unbridged. So the cross-validation measures the estimate
  on an easier population than the real one — in the estimate's favour, which is
  the direction that keeps the conclusion safe.
- **The real bias is unmeasured and unmeasurable here.** How far the estimate
  actually misses depends on the unbridged countries, which are exactly what is
  unknown. The claim is that the error is *unbounded from inside the method*, not
  that it is large.
- **11.2% CINS is a floor on the enrichment**, not the whole of it: an unbridged
  digit-leading CUSIP may also be foreign, and 89.1% is the measured rate at
  which it is not.
- **One country, one quarter, one workload.**

## Reproduce

The measurement is a ~40-line cross-validation over the same three sources as
`scripts/vertical_slice_country_exposure.py`; the numbers and method are recorded
in `notes/autonomy/predictions.jsonl` under `are-bounds-worth-it`.
