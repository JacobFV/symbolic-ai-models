---
title: The grounding contract transfers to a bitemporal task and the mechanism does not — the paragraph now has to explain by date, and the checker needed a boolean verdict form and a date channel
date: 2026-08-19
author: lead
status: provisional
tags: [renderer, grounding, transfer, bitemporal, pipeline]
---

## What was tested

The flood renderer established a contract: **the structured answer is canonical,
the paragraph is strictly downstream, and unsupported or contradictory assertions
are caught mechanically.** This puts it on a structurally opposite task — one
boolean per group instead of a vehicle set, a trivial kernel instead of two
expensive ones, and a **bitemporal** core.

## The explanation has to cite a date, not a value

A covenant does not fail because a number is small. It fails because a figure was
**not knowable** at the decision date:

```
The covenant was not met. On the information available at 2026-05-30,
consolidated revenue was 450.98 USD against a requirement of 651.22 USD.
Excluded as not yet knowable: sub_3 filed 169.91 USD dated 2026-06-01, after
the determination.
```

```
The covenant was met. On the information available at 2026-08-04, consolidated
revenue was 605.60 USD against a requirement of 570.13 USD. Restated before the
determination and counted at the later figure: sub_1.
```

**That is the first explanation in this repo that must cite a date rather than a
value**, and it is exactly what `transaction_time` is for. A representation
carrying only values could state the verdict and not the reason.

**60/60 grounded**, and a test requires the bitemporal clause wherever a member
filed only after the determination — a paragraph that quietly omitted the
exclusion would be true-but-misleading and is caught as a missing explanation
rather than as a false one.

## The contract transfers; the mechanism does not

I predicted the flood checker might transfer with nothing but a new token set.
It did not:

- The contradiction check needed a **boolean verdict** form, not the flood
  renderer's per-vehicle `runs`/`cannot` polarity.
- A **date channel** was needed, since every asserted date must be a filing date
  or the determination date.

> **What transfers is the contract — three checks: tokens, a domain-specific
> relation, and contradiction against the structured answer — not any line of
> code.** That is the weaker of the two outcomes I named in advance, and it is
> the honest one.

The domain-specific middle check is the interesting slot. In flood it is **route
adjacency**; here it is **date validity**. Both answer the same question — *what
relation can this paragraph get wrong while using only real tokens?* — and the
answer is different per domain.

## A checker that fired on everything

The first version reported **0/60 grounded**. `_NUM` matches the digit runs
inside dates, so every `2026-05-30` contributed three spurious "numbers", and my
guard tested whether the *token* was a full date — which `2026` is not. Stripping
dates before the number scan fixes it.

Worth recording because it failed **loudly**: a checker that flags everything is
obvious, where one that flags nothing looks like success. The renderer's own bugs
in flood were caught the same way round.

## What would refute it

- **Two domains.** Scheduling has no renderer, and its answer is also boolean, so
  it would test whether the boolean contradiction form is reusable or whether
  every domain needs its own.
- **Grounding is still not semantic.** A figure attached to the wrong member
  where no date or verdict claim is made would pass, the same residual hole the
  flood renderer has.
- **The renderer is a template.** Its value is that it fixes the checkable
  contract; a learned renderer would be scored by the same `ungrounded()`.

## Reproduce

```bash
uv run pytest tests/test_solvency_render.py
```
