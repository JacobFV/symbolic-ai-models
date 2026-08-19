---
title: My 25× omitted revalidation cost from both arms — including it, the derived margin is the first thing in the certificate programme to exceed 1.0×, at a 2.91× ceiling, and only above 36 queries per key
date: 2026-08-18
author: lead
status: provisional
tags: [certificates, maintenance, cost, self-correction, amortisation]
---

## What I published one commit earlier

`notes/findings/2026-08-18-the-rung-...-is-derivable.md` reported the derived
margin at **25× cheaper per quality point**, *"from recording one extra number
per answer"*. That comparison priced **recompute** for both arms and left
**revalidation** out of both — which is not apples-to-apples, because the two
arms do not revalidate alike:

| arm | what a check costs |
|---|---|
| read set | one digest comparison |
| derived margin | a symmetric difference over the whole holder set |

§3b's formula is `advantage = min(compute/check, 1/P_hit)`, and the margin
improved only the **second** term. So the question is whether the check got
dearer than the recomputes it saved.

## Measured, and the answer depends on something I had fixed at its worst value

`scripts/cert_margin_net_cost.py`, 3,000 distinct securities, mean holder set
70.4.

| | per key per update |
|---|---:|
| digest pass | 853 ns |
| **delta pass** | **6,634 ns** — **7.8× dearer** |

| | per answer |
|---|---:|
| recompute | 277.5 ns |
| revalidate, read set | 94.2 ns |
| **revalidate, derived (delta supplied)** | **80.1 ns** — *cheaper* |
| revalidate, derived (delta recomputed) | **5,911 ns** |

Net maintenance advantage, `recompute_all / (amortised pass + revalidation +
resolve)`. The amortised pass is a property of the **update**; queries are what
it is spread over, so the answer is a **curve**:

| queries per key | 1 | 5 | 20 | 50 | 200 | **∞** |
|---|---:|---:|---:|---:|---:|---:|
| read set | 0.25× | 0.64× | 0.91× | 0.99× | 1.04× | **1.05×** |
| **derived, delta supplied** | 0.04× | 0.20× | 0.65× | 1.22× | 2.16× | **2.91×** |
| derived, delta recomputed | 0.05× | 0.05× | 0.05× | 0.05× | 0.05× | **0.05×** |

- **The derived margin overtakes the read set at 34.3 queries per key**, and
  **exceeds 1.0× at 36.4.**
- **The read set's ceiling is 1.05×** — it is never really worth having, which is
  §3b's *"per quarter, a read-set certificate is worth nothing"* arriving by a
  second route.
- **Recomputing its own diffs is a 20× loss.** The XOR costs 5,911 ns against a
  277.5 ns recompute. I predicted "net loss" and under-called the severity.

## The correction

> **The 25× was not wrong arithmetic; it answered a narrower question than it
> appeared to.** Per *quality point bought by aiming*, the derived margin really
> is 25× cheaper. Per *dollar of maintenance*, it is 2.91× at best, 1.0× at
> 36 queries per key, and **0.05× if the delta is not supplied**. The extra
> number is not the whole cost: the pass that produces it is 7.8× dearer per key
> than the digest pass it replaces.

## And the part that survives, which is the larger claim

**The derived margin is the first arm in this whole certificate programme to
exceed 1.0× on a real corpus update.** §3b's four read-set rows were 0.3×, 0.3×,
0.6× and 1.0×; the read-set ceiling measured here is 1.05×. The margin reaches
**2.91×**.

The condition is named and measurable: **the delta must come from the update
stream, and each key must be read by ~36 queries.** §3b's own margin arm used a
precomputed `delta_size` without saying so, so it was already assuming the first
half of that condition; this makes it explicit and prices it.

That condition is a statement about the *workload*, not the mechanism: a
one-pass analysis that touches each security once does not meet it; a service
that re-serves answers meets it easily. Which is the same shape as everything
else this session found — **the instrument is fine and the workload decides.**

## What would refute it

- **Python constant factors.** A frozenset XOR over ~70 elements at 5,911 ns is a
  language artefact as much as an algorithmic one; the *ratio* of delta pass to
  digest pass (7.8×) is the transferable quantity, and the 36-queries-per-key
  crossover moves with it.
- **One threshold, one query class.** `is_widely_held(k=100)` is the only class
  measured here with any slack at all. `holder_count`, `portfolio_overlap` and
  `min_filers_covering` have slack 0 or no cheap bound, so this curve is the best
  case and not a typical one.
- **The delta pass is charged in full.** A real update stream produces adds and
  removes as its output, so `|old XOR new|` is a by-product rather than a pass —
  which would remove the 6,634 ns entirely and push the crossover to ~1 query per
  key. That is the strongest version of the mechanism and it needs a system that
  actually has such a stream, which this repo does not.
- **Sampling changed slightly.** 3,000 keys without replacement here against
  5,000 with replacement in the previous finding, so flagged rates read 61.13% /
  5.47% rather than 62.22% / 6.16%. The 10× ratio is unaffected.

## Reproduce

```bash
uv run python -u scripts/cert_margin_net_cost.py
```

`runs/cert_margin_net_cost.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `does-the-derived-margin-actually-pay`.
