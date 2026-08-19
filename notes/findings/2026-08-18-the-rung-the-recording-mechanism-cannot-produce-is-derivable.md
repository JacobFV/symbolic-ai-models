---
title: The rung §3b called "the one the recording mechanism cannot produce" is derivable from an intermediate the computation already had — 62.22% invalidation to 6.16%, aim× 1.61 to 16.23, and it slightly beats the hand-built margin
date: 2026-08-18
author: lead
status: provisional
tags: [certificates, maintenance, capability, prediction-confirmed, core]
---

## What was believed

`HANDOVER.md` §3b measured a **stability margin** surviving 93.62% against the
read set's 33.04% and called it *"the rung the recording mechanism cannot
produce"* — treating it as **query-supplied**, a hand-written rule per query, and
therefore not something a generic mechanism could offer.

`notes/findings/2026-08-18-over-approximation-is-a-property-of-the-answer-...md`
then showed why a read set cannot reach that rung: two queries with
**byte-identical read sets**, the same securities and 9 ns of cost between them
over-approximate **1.1×** and **79.8×**. What a certificate wastes is a property
of the *answer*, and reads cannot see it.

## The slack was never hidden

`q_widely_held` computes `len(holders) >= 100`. **The count is an intermediate it
already produced.** `|count − 100|` is the distance to the flip, and only the
*discarding* of that number was ever the problem.

`symbolic_ai_core/runtime/certificate.py` now carries `Sensitivity`, `Counted`
and `revalidate_sensitive`. A certificate records the numeric intermediate and a
per-key Lipschitz bound; revalidation is

```
sum_k  lipschitz_k × |old_k XOR new_k|   <   slack
```

with **no per-query delta rule**. Above the threshold a count of 140 tolerates a
fall of 40; below it, a count of 97 tolerates a rise of 2. A raw count gets slack
**0**, which is correct — every change moves it — and the certificate degrades to
exactly the read-set behaviour rather than to something weaker.

## Measured

`scripts/cert_answer_stability.py`, the same two filed 13F snapshots.

| query class | read-set flagged | **derived flagged** | over-approx | **recovers** |
|---|---:|---:|---:|---:|
| `is_widely_held(k=100)` | 62.22% | **6.16%** | 79.8× → **7.9×** | **10.1×** |
| `holder_count` | 62.22% | 62.22% | 1.1× | 1.0× |

And in the ledger, priced by the `Targeting` denominator:

| arm | aim× | **$/quality point** |
|---|---:|---:|
| `is_widely_held`, read set | 1.61× | $8.67e-10 |
| **`+margin is_widely_held`** | **16.23×** | **$3.46e-11** |

> **25× cheaper per quality point, from recording one extra number per answer.**

**Zero false survivals on every arm.** The script raises rather than reports if a
margin ever survives an answer that moved — a loose margin costs money, an
unsound one silently serves a wrong answer, and the run must stop.

## It beats the hand-built version

The derived margin flags **6.16%**; §3b's query-supplied margin flagged **6.38%**.
The automatic one is marginally *tighter* than the rule a person wrote, and it
needed no rule.

> **The rung is producible. It is not a property of the query author's
> diligence; it is a property of whether the mechanism keeps the number the
> computation already had.**

## Where the remaining 7.9× is, and why it is honest

`moved_elements` uses the **symmetric difference**, which over-estimates the
movement of a count: an add and a remove cancel in the count and do not cancel in
a XOR. That is the documented price of a mechanism that does not know what the
query does with its inputs, and it is bounded and measurable rather than unknown.
Closing it would need the query to declare that its aggregate is a *count* rather
than a general function of the set — a strictly larger contract.

## What it does not do

Nothing for `holder_count` or `portfolio_overlap` (slack 0 — the answer really
does move on any change) and nothing for `min_filers_covering` (no cheap sound
Lipschitz bound for a set cover's optimum). **The mechanism pays exactly where
the answer is coarse, which is exactly where the waste was.** That is the correct
shape and not a limitation to apologise for.

## The prediction

Pre-registered before implementing: *"f_flagged drops from 62.1% toward 3–8%,
landing near the hand-built margin's 6.38%, recovering ~10× and leaving ~8× on
the table; holder_count unchanged."* Measured: **6.16%, recovers 10.1×, leaves
7.9×, holder_count unchanged exactly.** The closest prediction of the session.

## AMENDMENT: the 25× omitted revalidation cost, and the condition it hides

`notes/findings/2026-08-18-the-derived-margin-is-the-first-arm-above-1x-...md`.
The **$/quality-point** comparison above priced *recompute* for both arms and
left *revalidation* out of both. The two arms do not revalidate alike: a read-set
check is one digest comparison; the derived check is a symmetric difference. And
the pass that produces the delta costs **6,634 ns per key** against the digest
pass's **853 ns** — **7.8× dearer**.

Net maintenance advantage, as a function of **queries per key**:

| queries per key | 1 | 20 | 50 | 200 | **∞** |
|---|---:|---:|---:|---:|---:|
| read set | 0.25× | 0.91× | 0.99× | 1.04× | **1.05×** |
| **derived, delta supplied** | 0.04× | 0.65× | 1.22× | 2.16× | **2.91×** |
| derived, delta recomputed | 0.05× | 0.05× | 0.05× | 0.05× | **0.05×** |

> Per *quality point bought by aiming*, 25× stands. Per *dollar of maintenance*,
> it is **2.91× at best, 1.0× at 36.4 queries per key, and 0.05× if the delta is
> not supplied**. "One extra number per answer" understated the cost.

**What survives is larger than what was corrected:** the derived margin is the
**first arm in the certificate programme to exceed 1.0×** on a real corpus
update — §3b's read-set rows were 0.3×, 0.3×, 0.6×, 1.0×, and the read-set
ceiling here is 1.05×.

## What would refute it

- **One threshold on one corpus update.** The margin's value depends on how far
  the data sits from the boundary; `k = 100` is far from most securities' holder
  counts. A threshold at the median would collapse the gain, and that is a
  property of the *question*, not of the mechanism.
- **Soundness is tested, not proved.** 78 parametrised cases in
  `tests/test_certificate_sensitivity.py` sweep counts and deltas across the
  boundary, plus a zero-false-survival assertion over 5,000 real queries. That is
  evidence, not a proof, and the proof obligation is `|Δcount| ≤ |A XOR B|`,
  which is immediate.
- **`Counted` covers counts and thresholds.** Whether the approach generalises to
  min/max, top-k, or ratios is unmeasured; each needs its own Lipschitz argument
  and some will not have a cheap one.
- **The extra number is not free.** It is one integer per certificate and no
  extra reads, so the cost is negligible here — but a query whose intermediate is
  large would not enjoy that.

## Reproduce

```bash
uv run pytest tests/test_certificate_sensitivity.py
uv run python -u scripts/cert_answer_stability.py
```

90 tests; the 17 existing certificate tests are unchanged.
