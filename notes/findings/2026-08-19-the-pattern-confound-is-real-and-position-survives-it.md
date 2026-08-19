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

## What would refute this

- `acquired by` at n=24 and the rank-2 bucket at n=14. The 1-vs-2 contrast within
  the dominant branch is the claim; everything past rank 2 is noise.
- "Strong" and "weak" patterns were separated by this measurement, so treating the
  split as a feature is fitting unless it holds on a second corpus. It has a
  semantic reading — *acquired* and *part of* describe events and loose
  affiliations, *subsidiary of* and *owned by* describe the current relation —
  which is why it is worth carrying, but that reading was written after the
  numbers.
