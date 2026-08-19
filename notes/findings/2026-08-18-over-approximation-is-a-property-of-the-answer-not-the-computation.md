---
title: Two queries with identical read sets, identical inputs and 9ns of cost between them over-approximate 1.1x and 79.8x — what a certificate wastes is a property of the answer, and reads cannot see it
date: 2026-08-18
author: lead
status: provisional
tags: [certificates, maintenance, cost, control, prediction-refuted, decisive]
---

## The question §3b left open

The certificate arm measured **soundness** on every row — `false_survivals = 0`,
a certificate never declares valid for an answer that moved — and never measured
**precision**: how many invalidations were *unnecessary*, because the inputs
changed and the answer did not.

That matters now, because `symbolic_ai_core/cost.py` has a `Targeting`
denominator. Maintenance is a targeting problem in the escalation sense —
recompute nothing / recompute what the certificate flags / recompute the same
share at random — and for a **sound** certificate the algebra collapses:

```
aim×  =  1 / f_flagged          a minimal certificate would reach  1 / f_stale
```

so over-approximation destroys targeting value in direct proportion. §3b measured
a **6,591×** over-read on shortest path and never priced it.

§3b also stated the open question outright: *"Whether a recorded read set is
tight is a property of the problem, and **nothing in the mechanism tells you
which case you are in**."* This says what does.

## The controlled comparison, which fell out rather than being designed

`scripts/cert_answer_stability.py`, over the two filed 13F snapshots.

| query class | compute/answer | f_flagged | f_stale | **over-approximation** | aim× |
|---|---:|---:|---:|---:|---:|
| `is_widely_held(k=100)` | 739 ns | 62.1% | **0.78%** | **79.8×** | 1.61× |
| `holder_count` | 748 ns | 62.1% | 54.3% | **1.1×** | 1.61× |
| `portfolio_overlap` | 6,048 ns | 99.0% | 62.1% | 1.6× | 1.01× |
| `min_filers_covering(12)` | 6,745,104 ns | 100.0% | 40.7% | 2.5× | 1.00× |

The first two rows run over the **same sampled securities**, read the **same
keys**, and cost within **9 ns** of each other. Their read sets are byte-identical
by construction. They differ **73×** in over-approximation.

> The only variable is the answer function: `len(holders)` against
> `len(holders) >= 100`.

## What that establishes

> **What a certificate wastes is a property of the ANSWER's sensitivity — not of
> the computation's cost, not of the read set's size — and it is invisible to any
> mechanism that records reads**, because the two cases that differ 73× record
> the identical read set.

That is the mechanism §3b said the recording approach could not supply, and it
explains the arm's whole spread: the 6,591× over-read on shortest path is not a
pathology of BFS, it is what happens when a coarse answer (a distance) is
certified by the fine inputs a search touched.

### The prediction it refutes is mine

I pre-registered the sharper claim that **over-approximation would be largest
where the computation is dearest**, on the reasoning that expensive computations
produce coarse answers insensitive to churn. It is largest at the **cheapest**
class (739 ns, 79.8×) and only **2.5×** at **9,000× the compute**. An NP-hard set
cover's answer moved **40.7%** of the time — I predicted 8–35% and expected a
small integer to be stable. One of four factor predictions landed in range.

## The stability margin is loose too

§3b called the query-supplied stability margin *"the rung the recording mechanism
cannot produce"*, surviving 93.62% against the read set's 33.04%. Since that
margin certificate is **sound**, its 6.38% flagged rate is an **upper bound** on
`f_stale`, and the measured `f_stale` is **0.78%**.

> **The hand-built margin — the best rung in the arm — itself over-approximates
> by 8.2×.** Being much tighter than a read set is not the same as being tight.

*(My anchor asserted `f_stale` must **equal** 6.38%, and the script duly reported
a disagreement and blamed itself. The number is a bound, not an estimate; the
anchor's design was the error. Confusing the two, again.)*

## What it is worth, in the ledger

| query class | rate | floor | **$/answer kept correct** | aim× |
|---|---:|---:|---:|---:|
| `portfolio_overlap` | 1.000 | 0.379 | **$8.95e-13** | 1.01× |
| `holder_count` | 1.000 | 0.457 | $1.02e-12 | 1.61× |
| `min_filers_covering(12)` | 1.000 | 0.593 | $1.37e-12 | 1.00× |
| `is_widely_held(k=100)` | 1.000 | 0.992 | **$7.12e-11** | 1.61× |

`rate` is 1.0 because the certificate is sound: recomputing everything it flags
leaves every answer correct. The floor is recomputing nothing. So `above_floor`
is exactly `f_stale` — the answers maintenance actually had to save.

**Maintaining an insensitive answer costs 80× more per answer saved**, because
almost none of them needed saving. And `min_filers_covering` flags 100% of
queries, so aiming and spreading are the same policy and its `$/pt` is `inf` —
*"the confidence signal is not informative"*, printed by the module itself.

## What would refute it

- **Four query classes on one corpus update.** The controlled pair is strong;
  the *ordering* across all four is four points.
- **`f_flagged` here is 62.1% where §3b reports 66.96%** — different sampling of
  securities (with replacement, from the intersection of both snapshots). The
  over-approximation ratio is internal to each row and unaffected.
- **A threshold far from the data is the easy case.** `is_widely_held(k=100)` is
  insensitive because few securities sit near 100 holders. A threshold placed at
  the median would collapse the 79.8× toward 1×, which is the point — sensitivity
  is a property of the *question asked*, and a system could be asked either.
- **`min_filers_covering` samples 12 random securities**, which makes the cover
  volatile. A realistic portfolio question would use a related set and might be
  far more stable, moving the dearest row's number a lot.

## Reproduce

```bash
uv run python -u scripts/cert_answer_stability.py
```

`runs/cert_answer_stability.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `certificate-precision`.
