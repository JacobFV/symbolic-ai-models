---
title: The north star priced knowing-you-are-right at zero; closing that hole prices the ambiguity signal at 1.02x — worth nothing over random spending, not merely less
date: 2026-08-18
author: lead
status: provisional
tags: [cost, north-star, certification, capability, instrument]
---

## The hole

`notes/findings/2026-08-18-determinacy-is-not-accuracy-...md` produced a row that
the ledger could only half describe. The federated resolver **does not beat a
floor holding its own candidate sets** — `$/solved-above-floor` reads `inf` — and
its determinacy signal separates **95.8%** accuracy from **40.4%**, which aiming
a fixed escalation budget turns into **4.69×** more quality than spending that
budget at random.

Both are true of the same system, and **no column in `symbolic_ai_core/cost.py`
could show the second.** `$/solved-above-floor` prices *getting the answer right*
and prices *knowing you are right* at **zero**.

That is a gap in the repo's north-star metric, not in the measurement, and this
closes it.

## The denominator, and the floor that makes it a metric

`Targeting` prices a confidence signal **where it acts**: escalation. At a fixed
budget, a system that knows which of its answers are unsafe spends the budget on
them; one that does not spends it at random. So the floor is **blind escalation
of the same share**, and the class refuses to carry a targeted rate without it —
exactly as `Capability` refuses a rate without a floor, and for the same reason:

> *"We escalated and quality rose" is not a result; buying answers raises quality
> whoever picks them.*

Two columns follow. **`aim x`** — quality bought by aiming over spending blindly.
**`$/pt`** — what one such point costs. An uninformative signal reads `inf`, and a
signal *worse* than blind also reads `inf` rather than a negative number, which
would sort to the top of the table.

## What it says about the two domains this repo has measured

The OpenAlex values were computed by hand and recorded in
`notes/autonomy/predictions.jsonl` **before the implementation existed**, so the
implementation could not be fitted to what it happened to produce.

| signal | share escalated | quality | **aim ×** | verdict |
|---|---:|---:|---:|---|
| GLEIF resolver determinacy | 15.4% | 0.965 | **4.69×** | worth routing on |
| OpenAlex **silence** | 12.3% | 0.650 | **2.13×** | worth routing on |
| OpenAlex **ambiguity** | 38.3% | 0.712 | **1.02×** | worth **nothing** |

`notes/findings/2026-08-18-the-million-fold-advantage-is-8x-...md` established
that *"silence is a better escalation signal than ambiguity"* and called the
separation weak (+0.150 F1). Priced, the statement gets sharper:

> **The ambiguity signal is worth nothing over spending the same budget at
> random — not merely less.** 1.02× is a rounding error away from 1.00, and the
> row now carries the note *"targeting lift is close to blind spending; the
> signal exists but is not worth routing on."*

That is a stronger claim than the original finding made, and it comes from
pricing a description that was already on disk rather than from a new run.

## The row this was built for

```
system                       $/solved>floor   rate   floor    aim x      $/pt
federated symbolic resolver             inf  0.873   0.874     4.69  $1.31e-03
```

**Worthless at producing answers above its floor; worth 4.69× at certifying
them.** That is not a contradiction — it is the difference between producing an
answer and certifying one, and it is the distinction this repo's certificate arm
has been measuring for a week without ever connecting it to cost.

## What would refute it

- **One denominator for a family of uses.** Escalation targeting is the use where
  certification is easiest to price. A certificate that lets a *downstream* system
  skip revalidation is worth something this column still cannot see, and that is
  the certificate arm's own economics (§3b) — unmeasured against this metric.
- **The escalated tier is assumed perfect** in every number above, which inflates
  both the targeted and the blind rate. Blocked on credentials (§6). The *ratio*
  is the more robust quantity because the assumption moves both.
- **`aim x` is a ratio and ratios have regimes.** At a very small budget the
  blind gain approaches zero and the lift diverges; at a budget approaching 1.0
  both policies escalate everything and it collapses to 1.0. The number is only
  interpretable beside the budget it was measured at, which is why `Targeting`
  carries `escalated` and the table prints neither without the other.
- **n = 1,015 for the GLEIF row**, one workload, on a population enriched 1.33×
  toward ambiguity.

## Reproduce

```bash
uv run pytest tests/test_cost_targeting.py
uv run python -u scripts/arc_through_the_ledger.py
```

12 tests; the 41 existing cost tests are unchanged, because the two columns
render only when a row carries a claim.
