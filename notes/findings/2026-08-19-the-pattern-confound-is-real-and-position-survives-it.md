---
title: The pattern confound is real, and position survives it
date: 2026-08-19
status: measured
arm: position-vs-pattern
---

## Checking the weakness I published with the finding

*"The extractor's patterns may themselves be ordered — if `subsidiary of` fires
earlier than `acquired by`, part of the position effect is the pattern list, not
the prose."* Unmeasured when published, and the obvious way that finding is wrong.

| pattern | n | precision | mean rank |
|---|---:|---:|---:|
| `subsidiary/division/unit of` | 80 | 0.588 | 0.64 |
| `owned by` | 42 | **0.619** | 0.43 |
| `acquired by` | 24 | **0.292** | 1.12 |
| `part of` | 21 | 0.333 | 0.62 |

**The confound is real.** The two weak patterns are half as precise, and
`acquired by` does fire later. So part of the pooled position effect is pattern
identity.

## But position survives it, and gets stronger

Within the dominant branch alone — confound removed entirely:

| rank | n | precision |
|---:|---:|---:|
| 1 | 58 | **0.672** |
| 2 | 14 | **0.286** |
| 3 | 5 | 0.600 |

**0.672 → 0.286 is a steeper drop than the pooled 0.626 → 0.375.** I predicted the
within-branch curve would be *flatter*; it is steeper, and the position finding
stands on its own rather than resting on the pattern mix. (Rank 3 is five cases.)

## And the check produced a second feature, which composes

| policy | coverage | correct | **precision** | break-even `W` |
|---|---:|---:|---:|---:|
| first match, all patterns | 0.589 | **0.369** | 0.626 | — |
| first match, strong patterns only | 0.494 | 0.333 | 0.675 | **0.162** |
| first match + corroborated | 0.423 | 0.304 | 0.718 | 0.297 |
| **strong patterns + corroborated** | 0.405 | 0.298 | **0.735** | 0.324 |

Pattern strength and corroboration **compose** — 0.626 → 0.675 → 0.735 — unlike
corroboration and the clause gate, which did not. And the cheapest of the three is
pattern selection at **W = 0.162**: dropping two of four patterns pays if a wrong
answer costs a sixth of a right one.

So the real-text stack is now three ordered features, all of them cheap and none
of them semantic: **take the first match, of a strong pattern, whose entity is
mentioned twice.** 0.735 precision against a 0.696 ceiling on the answered set.

## Naming the category beats growing the list

The residual taxonomy asked for `bought by` and `purchased by`. Those are
**transfer-of-ownership events**, and the split above already says events are the
weak half — so the move is not *add patterns* but **name the category and order
by it**: prefer a **state** of ownership, fall back to an **event** only where no
state is stated.

| policy | coverage | correct | **precision** |
|---|---:|---:|---:|
| state only (`subsidiary/division/unit of`, `owned/held/controlled by`) | 0.488 | 0.333 | **0.683** |
| **event only** (`acquired/bought/purchased/taken over by`, `part of`) | 0.274 | 0.083 | **0.304** |
| **state, event as fallback** | **0.601** | **0.393** | **0.653** |
| *published four patterns* | *0.589* | *0.369* | *0.626* |

**Event-only precision is 0.304 against state-only's 0.683** — a 2.2× gap that
earns the ordering. And the fallback fires on **19 articles (11.3%)** where no
state pattern matched, so it is additive rather than redundant.

The ordered reader is **strictly better than the published one on all three
columns**: more coverage, more correct answers, higher precision. Composing it
with corroboration gives the best precision measured on this task:

| policy | coverage | correct | precision | break-even `W` |
|---|---:|---:|---:|---:|
| state, event fallback | 0.601 | **0.393** | 0.653 | — |
| + corroborated (≥2 mentions) | 0.429 | 0.321 | **0.750** | **0.343** |

*(Precision is over answered articles; the 0.696 ceiling is over all articles, so
the two are not directly comparable.)*

> **The design rule: when a cue list wants to grow, name the latent category and
> order by it.** Here the category is *state versus event*, and ordering converts
> a request for two more patterns into a strict improvement — where simply adding
> them to a flat list would have imported the weak half's 0.304 precision.

## What would refute this

- `acquired by` at n=24 and the rank-2 bucket at n=14. The 1-vs-2 contrast within
  the dominant branch is the claim; everything past rank 2 is noise.
- "Strong" and "weak" patterns were separated by this measurement, so treating the
  split as a feature is fitting unless it holds on a second corpus. It has a
  semantic reading — *acquired* and *part of* describe events and loose
  affiliations, *subsidiary of* and *owned by* describe the current relation —
  which is why it is worth carrying, but that reading was written after the
  numbers.
