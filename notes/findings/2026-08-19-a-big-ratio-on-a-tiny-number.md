---
title: A big ratio on a tiny number — when writing the reader pays back
date: 2026-08-19
status: measured
arm: amortisation
---

## The missing half, computed with the unknown left as a parameter

"No accuracy closes the price gap" ended on what it could not compute:
development cost is measured nowhere here, so **337× cheaper per answer** cannot
be turned into *worth building*. The missing quantity:

    N* = development cost / (llm $/answer − our $/answer)

Development cost stays a **parameter**. Inventing one number would be a guess
wearing a measurement's clothes.

| domain | vs model | saving/answer | \$1,000 | \$10,000 |
|---|---|---:|---:|---:|
| flood | frontier | 1.086e-03 | **920,852** | 9,208,519 |
| flood | small hosted | 5.425e-05 | 18,432,843 | 184,328,433 |
| scheduling | frontier | 9.749e-04 | **1,025,793** | 10,257,933 |
| solvency | frontier | 4.500e-04 | **2,222,224** | 22,222,239 |
| solvency | small hosted | 2.250e-05 | 44,445,109 | 444,451,086 |

At **\$1,000** of engineering: **0.9M–2.2M** episodes against a frontier model,
**18M–44M** against a cheap hosted one.

## The rankings invert, and the flattering number is the ratio

Solvency has the **largest per-answer multiple — 1,334,849×** — and needs the
**most episodes** to pay back. Its saving is 150 tokens against a decision that
costs essentially nothing, so the absolute gap is the smallest of the three.

> **A big ratio on a tiny number is still a tiny number.**

The per-answer multiple and the amortisation threshold rank the three domains
oppositely, and only one of them decides whether to write the reader.

## The audit predicts the development cost too

Scaled by reader size against a frontier model:

| domain | reader lines | episodes |
|---|---:|---:|
| **scheduling** | **63** | **1,025,793** |
| solvency | 89 | 3,139,332 |
| flood | 666 | 9,734,720 |

Scheduling pays back soonest because its reader is **63 lines** — and it is 63
lines because `job_`/`machine_` prefixes fix the predicate, which the
signature-determinacy audit measures **offline at 0.000 ambiguity mass, before
any reader exists**.

So the instrument built to predict where reading would be *hard* also predicts
how expensive the reader is to *write*, and therefore how soon the symbolic route
pays back. That is the same quantity showing up in three places now: reader
difficulty, error concentration, and now a budget.

**Confounded, and stated in the script's own output:** flood's file holds five
reader arms built for research — rules, lexical, signature/index,
signature/roles, signature+content — where the others hold one. Read the
**ordering**, not the multiple.

## What this changes about the argument

"337× cheaper per answer" sounds decisive and is hard to act on. "Pays back after
about a million episodes against a frontier model" is a volume threshold, and it
is the form that tells you whether to build.

A million episodes is not a large number for anything running continuously, and
it is a very large number for a one-off analysis. That is the honest shape of the
claim, and it took leaving the unknown as a parameter to see it.

## What would refute this

- Lines of code are a **scale anchor, not a cost**. Two files of equal length can
  differ tenfold in effort, and the flood confound above is exactly that.
- The saving assumes the model attempts the same episode at published input-token
  rates. Output tokens, reasoning tokens and retries all raise the model's side,
  which shortens payback.
- Nothing here prices maintenance. A reader that needs revising when the surface
  changes never finishes amortising, and this repo has changed its surfaces
  repeatedly.
