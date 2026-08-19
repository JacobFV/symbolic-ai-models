---
title: Maintenance is the fourth thing the audit predicts
date: 2026-08-19
status: measured
arm: maintenance-cost
domains: flood, scheduling, solvency
---

## The last unpriced term

Amortisation ended on it: *a reader revised whenever the surface changes never
finishes amortising, and this repo has changed its surfaces repeatedly.* That is
not only a caveat — it is a **record**. Every surface transform built this
session is a maintenance event.

Each domain tested with **the reader that existed first**, against four events:

| event | flood | scheduling | solvency |
|---|---:|---:|---:|
| as published | 1.000 | 1.000 | 1.000 |
| drop headings | 1.000 | 1.000 | 1.000 |
| **shuffle paragraphs** | **0.000** | 1.000 | 1.000 |
| **interleave sentences** | **0.000** | 1.000 | 1.000 |
| paraphrase (V=4) | 1.000 | 1.000 | 1.000 |

| domain | breakages | which |
|---|---:|---|
| **flood** | **2 of 4** | shuffle paragraphs, interleave sentences |
| scheduling | **0** | — |
| solvency | **0** | — |

## The mistake I nearly published

A first version tested `read_content_roles` for flood and reported **zero
breakages everywhere** — maintenance free in all three domains.

That reader was **built specifically to survive interleaving and paraphrase**.
Testing it measures the repair and reports the damage as zero. The maintenance
cost is what it took to *get* here, not whether today's reader survives
yesterday's transforms.

Scheduling and solvency have only ever had one reader each, so testing theirs was
already the historical question — which is exactly why the flat 1.000 row looked
plausible instead of suspicious.

## The unification

flood breaks on the two events that move **arrangement**, and on neither that
moves wording. It survives paraphrase because its reader is signature-based; it
dies when the surface is rearranged because its signatures do not fix their
predicates.

The signature-determinacy audit measures that **offline, before any reader
exists**: flood's real ambiguity mass is **0.161**, scheduling's and solvency's
are **0.000**.

> A reader whose signatures fix their predicates never depended on the surface,
> so moving the surface cannot break it. A reader that needs arrangement breaks
> whenever arrangement moves.

That is a **recurring** cost rather than a one-off, which is precisely what stops
it amortising — the amortisation finding assumed a reader is written once.

So one offline number now predicts four things:

| | |
|---|---|
| reader difficulty | flood needs content; the others do not |
| where error concentrates | flood reader loss 0.500, scheduling 0.000 |
| how soon the route pays back | scheduling 1.0M episodes, flood 9.7M |
| **how often it needs repairing** | **flood 2 of 4 events, others 0** |

## What would refute this

- Four events, all invented in one session and all *arrangement* or *wording*
  changes. A change in the underlying **task** — a new claim kind, a different
  question — would break every reader here and the audit says nothing about that.
- "Breakage" is an accuracy drop over 0.1 on the domain's own metric. flood's
  drops are 1.000 → 0.000, so the threshold does no work; a domain with partial
  degradation would need a more careful definition.
- Two domains at exactly 0.000 ambiguity mass is a thin basis for a four-way
  claim. The pattern is consistent across everything measured, and it is still
  two points and one.
