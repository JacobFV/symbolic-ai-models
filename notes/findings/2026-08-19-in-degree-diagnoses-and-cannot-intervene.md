---
title: In-degree diagnoses and cannot intervene — three uses tried, three closed
date: 2026-08-19
status: measured
arm: blast-radius
---

In-degree — how many corpus articles name this entity as their parent — was the
one actionable signal this session produced. It predicts where an error is
expensive **before any reading**, from link structure alone, and the two findings
that named it as the way forward reached it from different directions: cost (hub
claims are consulted most) and composability (added coverage at the leaves does
not compose, because the constraint is at the hubs).

Three ways to use it have now been tried. **All three fail**, and the third is the
one that closes the question.

| use | intervention | result |
|---|---|---|
| **verification** | corroborate hub claims against other articles | co-occurrence measures topic, not support: AUC **0.503** |
| **decision rule** | refuse to ingest low-belief claims | no interior maximum at any threshold; a smaller world, not a better one |
| **allocation** | **train on hub articles more** | this note |

## Weighting the supervision buys nothing

Hub articles' sentences duplicated in the training set in proportion to
in-degree, capped at four copies. Three splits, four-fold cross-validation,
scored on **consultation-weighted accuracy** — each article counted once per
query that depends on it — because that is the metric a persistent world is
judged on rather than the leaf-heavy raw rate.

| arm | raw | **consultation-weighted** | hub | leaf |
|---|---|---|---|---|
| uniform | 0.147 | 0.140 | 0.114 | 0.153 |
| in-degree weighted | 0.140 | 0.135 | **0.114** | 0.144 |

**Hub accuracy does not move at all** — 0.114 to 0.114 — while leaf accuracy
falls 0.153 → 0.144. Consultation-weighted accuracy is down 0.005, **0/3 splits
up**. Predicted hubs would rise and leaves fall; the second half happened and the
first did not.

## Why, and it was measurable in advance

Hub articles are not hard because they are **rare in training**. They are hard
because of what they are: an entity many companies belong to is a big company,
and a big company's intro is **1,504 characters against 816** for a leaf. Longer,
more clauses, more candidate mentions, the relation stated further from the
subject.

**Duplicating a hard example does not make it learnable.** It re-weights capacity
toward examples the model cannot fit at any weight, and the capacity comes out of
the examples it could. That is exactly the shape of the result: hubs flat, leaves
down.

## What this settles

**In-degree is a diagnostic, not a lever.** It says truthfully where the errors
will be expensive, and nothing in this reader's control surface can act on it:
not by checking those claims, not by declining them, not by training harder on
them. The signal survives as something to *report* — a system could tell a user
which of its answers rest on hub claims and therefore deserve review — and dies
as something to *optimise*.

That is the same shape as the sensitivity programme, which also produced a real
measurement (`sₚ` spans 6.6x; inventing a claim is cheaper than losing one unless
it imposes a constraint) with no working intervention behind it. **Two signals
this session, both real, both diagnostic only.** The pattern is worth naming: a
quantity measured *about* a reader is not automatically a quantity that reader can
be steered by.

## What would have refuted it

Hub accuracy rising at all. It is 0.114 either way, to three decimals, on 268 hub
articles per split.
