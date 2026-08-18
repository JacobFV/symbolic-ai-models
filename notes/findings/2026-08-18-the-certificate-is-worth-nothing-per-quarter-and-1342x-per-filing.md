---
title: A dependency certificate is worth 0.4x per quarter and 1,342x per filing — its ceiling is dependency size, not the cost of the answer, and the most expensive kernel has the least valuable certificate
date: 2026-08-18
author: lead
status: provisional
tags: [certificates, cost, incremental, sec-13f, refuted-prediction, kernels]
---

## The question

`HANDOVER.md` recommended, as the highest-value next action:

> **Make dependency-certification a substrate-wide contract.** Only
> `possible_answers_scoped` reports what it read. Generalise it so every kernel
> and flow node returns the facts it consumed. *Why this first:* it is the only
> claim of ours that survived contact with a realistic opponent.

That recommendation contains an untested economic premise — that knowing what an
answer rests on is *worth* something — and it names no number. This measures it,
on the first real corpus update this repo has: two filed SEC 13F snapshots,
December 2025 and the quarter after, 2,282,570 → 2,360,678 holdings edges, with
333,014 positions closed and 411,122 opened. Nothing here is injected.

**The prediction, recorded before the run** (`notes/autonomy/predictions.jsonl`,
`cert-maintenance-13f` rev 2): the certificate's value is
`(recompute cost / revalidate cost) x (survival)`, so it should be ~1x on a cheap
aggregate and **>50x on a solver answer** — worth most where the computation is
dear relative to its dependency.

That was wrong, and wrong in the direction that matters.

## What was built

`symbolic_ai_core/runtime/certificate.py`. It generalises the recording trick
that `possible_answers_scoped` already used on *conflicts* to record reads over
*facts*: hand the computation a mapping that remembers, run it once, and its
dependency set is the answer. No annotation, no static analysis, and it works on
an arbitrary Python computation — including one that shells out to clingo, which
is the half incremental view maintenance does not give you.

Three things in it are load-bearing and were each a bug first:

- **Misses are reads.** `store.get(k)` returning nothing is a fact the answer
  depends on. Recording only hits fails to notice *additions*, which are 411,122
  of this delta's 744,136 changes.
- **Digests, not values.** Revalidation compares one hash per key, so a 3,000-
  member holder set costs one comparison. Comparing values would make
  revalidation O(bytes read) and the aggregate case would never move.
- **Iterating the store is refused.** A certificate over every key is sound and
  worthless, and a worthless certificate that looks real is how a scoped method
  quietly becomes an unscoped one.

## Result 1 — per quarter, the certificate is worth nothing, and often less

`scripts/cert_maintenance_13f.py`. Four query classes over one store, spanning
four orders of magnitude of compute cost, all certified by the same mechanism
with no per-query delta rule written by hand.

| query class | n | read set | compute/answer | revalidate/answer | speedup | survive | **maintenance advantage** |
|---|---:|---:|---:|---:|---:|---:|---:|
| `holder_count(S)` | 5,000 | 1 | 748 ns | 1,208 ns | 0.6x | 33.0% | **0.3x** |
| `is_widely_held(S,100)` | 5,000 | 1 | 739 ns | 1,101 ns | 0.7x | 33.0% | **0.3x** |
| `portfolio_overlap(F1,F2)` | 5,000 | 2 | 6,048 ns | 1,656 ns | 3.7x | 0.4% | **0.6x** |
| `min_filers_covering(12)` | 300 | 12 | 6,745,104 ns | 4,262 ns | **1,582.6x** | **0.0%** | **1.0x** |

The speedup prediction was right and beaten — 1,582x on the solver, against a
predicted >50x. The *value* prediction was wrong, because I treated speedup and
survival as independent factors and **they are anticorrelated**: the read set
that makes a certificate cheap to check is the same read set that makes it
likely to be hit. Under 75.7% key churn a twelve-fact dependency survives with
probability 0.24^12, which is nil. The two factors cancel to ~1.0x across four
orders of magnitude of compute cost, and on the cheap queries the certificate is
a **net loss** — a digest comparison costs more than a `len()`.

One rung did work, and it is the one the recording mechanism cannot produce: a
**query-supplied stability margin** ("this answer survives while fewer than *m*
of its facts move", checked against the delta rather than the corpus) survives
**93.6%** against the read set's 33.0%, at O(1) per answer.

## Result 2 — per filing, it is worth 37x to 1,342x

The quarter is not the unit in which 13F changes. It changes one filing at a
time — 8,425 filings moved something, each touching a mean of 89.3 keys, **0.185%
of the corpus** (p50 23, max 4,330). `scripts/cert_freshness_13f.py` measures a
cache of answers that must be *correct after every update*, against an opponent
that cannot certify non-dependence and so must re-derive all of them.

| batch (filings) | updates | keys/update | `holder_count` | `portfolio_overlap` | `min_cover(12)` |
|---:|---:|---:|---:|---:|---:|
| 1 | 8,425 | 89 | **165.4x** | **1,342.0x** | **37.3x** |
| 5 | 1,685 | 422 | 33.6x | 264.9x | 8.2x |
| 20 | 422 | 1,434 | 8.9x | 64.0x | 2.8x |
| 100 | 85 | 4,337 | 2.5x | 16.1x | 1.3x |
| 500 | 17 | 9,417 | 1.1x | 5.0x | 1.0x |
| 8,425 (the quarter) | 1 | 36,628 | 0.4x | 0.7x | 1.0x |

**The control that had to pass:** the whole-quarter endpoint must reproduce
Result 1, or the two experiments are measuring different things and neither is
safe. It does — 0.36x / 0.71x / 1.00x against 0.3x / 0.6x / 1.0x.

Note what the table does to the intuition the whole idea rests on. The **most
expensive computation has the least valuable certificate**, by 36x: a two-key
set intersection is worth 1,342x and a twelve-key NP-hard cover is worth 37x.

## Result 3 — why: two ceilings, and dependency size is the binding one

`scripts/cert_dependency_size.py`. In every query class above, cost and
dependency size are confounded — the dear query is also the one with the big
read set — so both were swept independently.

```
advantage  =  min( compute_per_answer / check_per_answer ,  1 / P_hit )
                  \___ check-bound ___/                     \_ invalidation-bound _/

with   P_hit  ~  r x keys_per_update / total_keys
```

**A. Dependency size swept 1→48, clingo kernel held fixed.** Advantage falls
364.8x → 11.7x, converging onto the `1/P` prediction as the invalidation ceiling
starts to bind (r=48: measured 11.7x, predicted 11.3x).

**B. Kernel cost swept over six orders of magnitude, dependency pinned at one
fact.** Advantage rises 12.6x → 74.8x → 350.2x and then *stops*: the last row's
sample had P(hit) 0.371%, and 1/0.00371 = 269.5 against a measured **269.7**.

So cost does not set the value; it decides only whether the ceiling is reached.
The ceiling is `total_keys / (r x keys_per_update)`. The solver is worth less than
the set intersection **entirely** because it reads six times as many facts, and
not at all because it is 1,000 times dearer.

## What this refutes, including my own recommendation

- **"The certificate pays where the computation is expensive relative to its
  dependency."** False as stated, and it was my prediction eight hours ago. It
  pays where the dependency is *small under the update*, and expensive kernels
  systematically have large dependencies.
- **`HANDOVER.md` item 1 is the lower-value half of the right idea.** Making
  every kernel report its read set is cheap and buys 0.3x–1.0x at quarterly
  granularity. What the substrate should carry is the **stability condition** —
  and that is exactly the part the generic recording mechanism *cannot* produce,
  because it needs the query to say what would change its answer. The
  93.6%-vs-33.0% row is the whole design consequence.
- **The design pressure inverts.** The substrate should be pushing kernels toward
  *smaller* read sets, not toward reporting the read sets they have. A projection
  that halves a kernel's dependency doubles its certificate's ceiling.

## What would refute this

- **A different opponent.** The opponent here re-derives everything per update,
  which is what an LM or retrieval agent must do and is emphatically **not** what
  a database would do. Against incremental view maintenance — DBSP, differential
  dataflow — the advantage would be far smaller and possibly inverted, because
  IVM maintains the answer at delta cost instead of re-deriving it. The claim
  that survives that comparison is narrow and should be stated narrowly: this
  mechanism gets delta-proportional maintenance for an **arbitrary computation
  including an external solver**, with no per-query delta rule, which IVM
  requires the view to be expressible in its algebra to give. The *numbers* here
  are against the LM-shaped opponent and carry no claim against a database.
- **The inverted index is not charged per update.** Its build cost is amortised
  over answer insertion. If a cache's answers turn over as fast as the corpus,
  that amortisation is wrong and the check-bound ceiling drops.
- **One filing stream, one corpus.** The `1/P` ceiling is the claim; the third
  significant figure on 364.8x is not. `keys_per_update / total_keys` is a
  property of 13F's filing structure and a corpus that updates in larger units
  moves every row of the table left.
- **The anchor could have failed and did not.** 15,300 answers recomputed on the
  new snapshot; **0 false survivals** on every rung, including the stability
  margin. A certificate that certifies an answer which moved is broken, not
  weaker, and that count is the one number here that is not allowed to be
  non-zero.

## Reproduce

```bash
uv run pytest tests/test_certificate.py                    # 17 pass, <1s
uv run python -u scripts/cert_maintenance_13f.py           # ~2 min, Result 1
uv run python -u scripts/cert_freshness_13f.py             # ~2 min, Result 2
uv run python -u scripts/cert_dependency_size.py           # ~1 min, Result 3
```

Rows land in `runs/cert_maintenance_13f.json`, `runs/cert_freshness_13f.json`,
`runs/cert_dependency_size.json`. Predictions and outcomes, written before and
after, are in `notes/autonomy/predictions.jsonl`.
