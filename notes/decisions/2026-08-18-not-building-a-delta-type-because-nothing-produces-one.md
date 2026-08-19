---
title: Not building the Delta type — the number is derivable and nothing in this repo produces an update stream
date: 2026-08-18
author: lead
status: decided
tags: [decision, certificates, parked-prediction]
---

## The proposal

`notes/findings/2026-08-18-the-derived-margin-is-the-first-arm-above-1x-...md`
found the derived margin's crossover set by a single quantity: the delta pass
costs **6,634 ns/key** against the digest pass's **853 ns**. And that pass should
not exist — a corpus update *is* a set of adds and removes, so `|old XOR new|` is
its **by-product**, not something to be recovered by diffing two snapshots after
the fact.

The proposal was a `Delta` type an ingest path produces directly and
`revalidate_sensitive` consumes, with the snapshot diff kept as a fallback.

## Why it is not being built

**The outcome is derivable, and I believe it.** Removing the amortised pass
leaves `80.1 + 0 + 0.0547 × 277.5 = 95.3 ns` against a 277.5 ns recompute:

> **A flat 2.91× at every queries-per-key, with the crossover moving from 36.4
> to ~1.** The curve stops being a curve.

The repo's standing rule fires: *if you can state the outcome and the mechanism
in advance and you believe it, record the prediction and spend the time on
something whose answer you do not have.*

**And there is no producer.** Nothing in this repo emits an update stream.
`symbolic_ai_core/runtime/certificate.py` has `changed_keys(old, new)` — which is
precisely the after-the-fact diff being charged for — and both 13F snapshots
arrive as complete parquet files. A `Delta` type would be consumed only by a
test, which is the shape
`notes/decisions/2026-08-18-deferring-the-egraph-witness-...md` already declined
once this week: *the cheap version is a trace, not a certificate, and the real one
has no consumer today.*

## What would reverse this

An ingest path that produces adds and removes — a streaming loader, an
incremental corpus builder, or a source that publishes diffs rather than
snapshots. **SEC filings are published as individual documents**, so a loader
that read filings rather than a quarterly aggregate would emit exactly this, and
at that point the `Delta` type has a producer and is worth an hour.

Until then the honest statement is the one now in `HANDOVER.md`: the derived
margin reaches 2.91× **above 36.4 queries per key**, and the condition is a
property of the deployment, not of the mechanism.

## The parked prediction, so a later session can check it

**2.91×, flat in queries-per-key, if the delta arrives with the update.** If
something later measures a different number, that contradiction is the finding.
