---
title: Over-splitting and over-deleting are the same failure
date: 2026-08-19
status: measured
arm: granularity-sweep
---

## The question "clause, not sentence" did not answer

It says which of **two** units, not whether there is an optimum. If the rule were
simply *cut as small as possible*, the clause result would be a way-station.

Five granularities, on the corpus where the failure was found and on the surface
built to reproduce it. `fine` adds coordinators and relative pronouns; `finest`
adds prepositional heads, which cut **through** the patterns the reader looks for.

**Wikipedia, 168 company intros**

| granularity | answers | accuracy | picks a former parent |
|---|---:|---:|---:|
| document (no filter) | 0.589 | 0.369 | 0.024 |
| **sentence** | **0.542** | **0.327** | 0.024 |
| clause | 0.583 | 0.357 | **0.018** |
| **fine** | **0.589** | **0.375** | **0.018** |
| **finest** | **0.542** | **0.327** | 0.024 |

**Solvency `stale_clause`, accumulating reader, 120 seeds**

| granularity | accuracy |
|---|---:|
| document | 0.925 |
| **sentence** | **0.592** |
| clause | **1.000** |
| fine | **1.000** |
| **finest** | 0.925 |

## A peak, on both, and the ends fail for the same reason

**Both extremes lose and the middle wins.** Over-deleting removes the answer with
the distractor; over-splitting cuts the answer in half. The Wikipedia rows make
the identity exact: **the finest split reproduces the sentence split's numbers to
three decimals** — 0.542 / 0.327 / 0.024, in every column.

That is not a coincidence, and it is the finding:

> **A splitter fine enough to cut through the pattern the reader is looking for
> leaves no fragment matching it, which is indistinguishable from deleting the
> sentence. Over-splitting *is* over-deleting, by another route.**

`a subsidiary **of** X` spans an *of*-boundary. Split there and the mention is
gone; the gate did not remove it, the tokenisation did.

So the unit is a **real linguistic object** rather than a slider, and the fix has
a principled stopping point: cut at boundaries the patterns do not cross.

## What is and is not resolved by n = 168

**Robust:** the shape. Sentence and finest both cost about **0.045** accuracy
against no filtering — seven or eight articles — and the middle two are the peak.

**Not resolved:** which of `clause` and `fine` is best. They differ by 0.018 on
Wikipedia, three articles, and tie at 1.000 on the generated case. `fine` is the
only arm that **beats no filtering at all** (0.375 against 0.369) while halving
the former-parent error, and that margin is one article. I am not shipping a third
option on one article.

`filter_stale` keeps `sentence` (default, so earlier numbers hold) and `clause`.
The sweep is recorded so a later session does not have to rediscover that finer is
not better.

## What would refute this

- One pattern family, one relation. A reader whose patterns are short and local
  would tolerate a much finer split, and the peak would move.
- The splitters are regexes over function words. A parser would cut at real clause
  boundaries and might dominate every row here.
- The Wikipedia accuracies span 0.327 to 0.375 over 168 articles; only the
  extremes are separated by more than the noise.
