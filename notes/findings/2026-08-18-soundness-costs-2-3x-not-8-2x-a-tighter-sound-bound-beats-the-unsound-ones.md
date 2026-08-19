---
title: Soundness costs 2.3×, not 8.2× — a tighter sound bound reaches 57.5× of an available 131.6× and beats every unsound arm that serves under 0.44% of answers wrong
date: 2026-08-18
author: lead
status: provisional
tags: [certificates, cost, instruments, exactness, self-correction, prediction-confirmed]
---

## The question I asked, and the better one underneath it

Every certificate in this repo is **sound** — it never declares valid for an
answer that moved — and that had never been priced. So: what does soundness cost?

The first measurement said **8.2×**, and the framing was wrong. That number is
the looseness of **one** sound bound, not the price of exactness.

## What relaxing soundness buys

`scripts/what_soundness_costs.py`, 5,000 securities, `is_widely_held(k=100)`
over the two filed 13F snapshots. **0.76% of answers actually moved.** Relaxing
the derived margin by `alpha` — flag iff `delta >= alpha × slack`:

| policy | flagged | wrong served | rate | **aim×** | sound |
|---|---:|---:|---:|---:|:--:|
| margin, α=1 (symmetric difference) | 6.22% | 0.000% | 1.0000 | 16.1× | ✅ |
| margin, α=4 | 1.36% | 0.260% | 0.9974 | 48.4× | |
| margin, α=8 | 0.64% | 0.440% | 0.9956 | 65.8× | |
| margin, α=16 | 0.24% | 0.620% | 0.9938 | **76.8×** | |
| margin, α=64 | 0.04% | 0.740% | 0.9926 | 65.8× | |
| **`\|Δcount\|` bound** | **1.74%** | **0.000%** | **1.0000** | **57.5×** | ✅ |
| **ORACLE** (a bound, not a system) | 0.76% | 0.000% | 1.0000 | **131.6×** | ✅ |

## The correction, which is the finding

`moved_elements` bounds answer movement by the **symmetric difference**, where an
add and a remove cancel in a count and **do not** cancel in a XOR. Bounding by
`|Δcount|` instead is **equally sound** and much tighter:

| bound | flagged | × the oracle |
|---|---:|---:|
| symmetric difference | 6.22% | **8.2×** |
| **`\|Δcount\|`** | **1.74%** | **2.3×** |
| oracle | 0.76% | 1.0× |

> **Of the 8.2× looseness, 3.6× is the XOR over-counting a count and only 2.3×
> is what no sound bound can remove without computing the answer.** Soundness
> costs **2.3×**, not 8.2×. The rest was engineering.

And the consequence reverses the trade the first framing implied:

> **The tighter sound bound reaches 57.5×, beating every unsound arm up to
> α=8 — which serves 0.44% of answers wrong — while serving nothing wrong.**
> You do not have to give up soundness to get most of the aim; you have to stop
> using a loose bound.

*(Pre-registered before running: "1–2% flagged, aim 50–100×." Measured 1.74% and
57.5×.)*

## The instrument had a hole, and it is a hole this repo has patched twice before

`aim×` still ranks the **unsound** α=16 arm above the sound α=1 arm, by 4.77×.
The accuracy column catches it — `$/solved-above-floor` is $7.31e-11 for α=1
against $3.97e-10 for α=16 — but **nothing in the table said the two columns
disagreed.**

`symbolic_ai_core/cost.py` now carries `targeting_regime()`, mirroring the
long-standing `perverse_regime()`:

```
!! TARGETING REGIME: aim x ranks alpha=16 (rate 0.9938) above alpha=1
   (rate 1.0000) -- aiming better by answering worse. Compare aim x only
   across rows at the SAME rate.
```

This is the **third** instance of one rule — §3i's *"advantage at fixed
quality"*, `perverse_regime` for `$/solved-above-floor`, and now this. See
`notes/lessons/2026-08-18-i-added-a-ratio-column-without-carrying-over-the-guard-...md`.

### A bound is not a system

The oracle initially sat in the ledger and **suppressed the warning**, having
both the best `aim×` and a perfect rate. Flagging exactly the movers requires
knowing which answers moved — the thing being certified. It is printed as a bound
now and excluded from the rows.

## The catch, and it is the same one as everywhere else this week

`|Δcount|` is **not deployable from two snapshots**: computing `len(new[k])` is
the recompute it was meant to avoid. It is deployable exactly when the update
stream supplies signed adds and removes per key — the `Delta` type parked in
`notes/decisions/2026-08-18-not-building-a-delta-type-because-nothing-produces-one.md`.

That decision now has a **second, independent motivation worth 3.6×**, alongside
the 2.91×-flattening it was first proposed for. The blocker is unchanged: nothing
in this repo emits an update stream. But the note said the decision reverses when
something does, and the case for it has roughly doubled.

## What would refute it

- **One query class, one threshold, one update.** `is_widely_held(k=100)` is the
  only class with any slack, so this is the best case and not a typical one.
- **`alpha` is a crude relaxation.** A calibrated predictor would sit on a better
  unsound frontier, so "sound beats unsound below α=8" is a statement about *this*
  relaxation, not about all of them.
- **The residual 2.3× may not be irreducible.** It comes from over-flagging large
  same-side moves — a rise of +1000 while already above the threshold. A bound
  that used the *signed* delta would remove that too and reach the oracle exactly,
  which makes 2.3× the price of taking a magnitude rather than the price of
  soundness. The decomposition may go one level deeper than measured here.
- **Error rates are computed against a ground truth that exists only because both
  snapshots are on disk.** A deployment cannot compute one, which is the argument
  for soundness and not a flaw in the measurement.

## Reproduce

```bash
uv run python -u scripts/what_soundness_costs.py
uv run pytest tests/test_cost_targeting.py
```

`runs/what_soundness_costs.json`; predictions and outcomes in
`notes/autonomy/predictions.jsonl` under `what-soundness-costs` and
`decompose-the-8x`.
