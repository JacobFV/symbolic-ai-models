---
title: Agreement is a test for exclusive alternatives, and real prose does not supply them
date: 2026-08-19
status: measured
arm: emission-on-real-text
---

## The repo's most distinctive idea, on text nobody here wrote

*Emit rather than collapse* is the idea this repo is most committed to, and the
enumeration theorem proved it **sound and complete** where the candidate set
covers the channel: all candidates agreeing ⇒ correct, a wrong collapse ⇒ they
disagree. Every measurement of it was on generated surfaces.

The Wikipedia parent task gives real prose with a gold answer, and its reader was
taking `candidates()[0]` — the *first* match, which is branching, the exact thing
the packing work said not to do. So: accumulate every ownership candidate and
answer only when they agree.

| arm | answers | correct | **precision** |
|---|---:|---:|---:|
| naive first match | 0.589 | 0.369 | **0.626** |
| emit, string identity | 0.375 | 0.226 | **0.603** |
| emit, shared content token | 0.423 | 0.256 | **0.606** |

*(ceiling — the gold parent named in the intro at all — 0.696)*

**Agreement carries no information at all.** Precision is flat at ~0.60 across all
three arms while coverage varies by 0.21. Loosening the equivalence from string
identity to a shared content token recovers coverage and moves precision by 0.003.

That was the refutation condition, written down before the run.

## Why, and it is not the reason I guessed

I expected correlated errors — the patterns picking up the *same* wrong name
repeatedly. The measurement says something else:

- **multi-candidate cases are *more* precise than single-candidate ones**, 0.667
  against 0.603. Disagreement is not a distress signal here; it is a good sign.
- **78% of multi-candidate cases contain a correct candidate.** The information is
  in *which* candidate, not in whether they agree.
- only 17% of them genuinely have several gold parents.

And the candidates themselves show the mechanism:

```
RCA Records          Sony Music Entertainment | Sony Music Group | Japanese
Metro-Goldwyn-Mayer  Amazon MGM Studios | Amazon | Amazon MGM Studios
Hulu                 Disney Streaming | Disney Entertainment | Nippon Television
```

These are **the same corporate group at different granularities**, plus regex
noise. They are neither competing readings of one fact nor a list of independent
facts.

## The scope statement

> **Agreement is a test for mutually exclusive alternatives.** In the generated
> surfaces the candidates are role assignments — exactly one can be right, so
> disagreement means the reader guessed. Real prose supplies candidates that are
> neither exclusive nor equivalent: several partly-true descriptions of one
> entity. Agreement is vacuous there, and demanding it discards cases that were
> more likely to be right than the ones it keeps.

The enumeration theorem is untouched — its premise is that the true reading is
among the candidates and the wrong ones give a *different answer*. What fails on
real text is the second half: two candidates naming *Sony Music Entertainment* and
*Sony Music Group* are not giving different answers, and no string relation says
so. **Emission needs an equivalence relation on answers, and on real prose that
relation is entity resolution** — the problem the whole signature discipline
sidesteps by naming things `region_0`.

## What would refute this

- One relation and one corpus. A task whose answers are genuinely exclusive —
  a date, a boolean, a quantity — would restore agreement's meaning, and that is
  the more common shape in the domains here.
- The candidate generator is four regexes; a better one might produce cleaner
  alternatives and make agreement informative again. The 0.667-vs-0.603 split
  argues against that, but it is one measurement.
- "Shared content token" is a crude equivalence. A real entity resolver would
  merge *Sony Music Entertainment* with *Sony Music Group* and could change the
  coverage substantially — though it would move cases from *discarded* to
  *answered by the first candidate*, which is the naive arm.
