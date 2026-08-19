---
title: Corroboration transfers where agreement does not
date: 2026-08-19
status: measured
arm: corroboration-on-real-text
---

## Two ideas the notes treat as one family

**Agreement** — emit the candidates, answer only when they concur — and
**corroboration** — a fact read a second way is trustworthy — were both built
today, and both are filed under *emit rather than collapse*. They are not the same
idea, and on real prose they come apart completely.

Agreement was measured first and transferred **nothing**: precision 0.603 (string
identity) and 0.606 (loose equivalence) against a naive 0.626, at 0.21 less
coverage. Corroboration had never been tried outside the generated surfaces, where
it caught 88 of 88 fabricated citations.

On the same 168 Wikipedia intros, splitting the answered cases by whether the
candidate's core token appears **elsewhere in the intro**:

| bucket | n | **precision** |
|---|---:|---:|
| **corroborated** (≥2 mentions) | 71 | **0.718** |
| single mention | 26 | **0.346** |

**A 2.1× gap.** As a policy — answer only when corroborated — coverage 0.423 at
precision **0.718**, against the naive 0.589 at 0.626.

## Why one transfers and the other does not

> **Agreement is a property of the *relation between* candidates; corroboration is
> a property *of one* candidate.** Agreement needs the candidates to be mutually
> exclusive, so that disagreement means somebody guessed. Real prose does not
> supply exclusivity — *Sony Music Entertainment* and *Sony Music Group* are the
> same answer at two granularities. Corroboration needs only that a true thing
> gets mentioned more than once, which real prose supplies abundantly.

That is the distinction to carry out of both experiments. The generated surfaces
made agreement look powerful because their candidates were **role assignments**,
where exactly one can be right by construction. Nothing in real text is built that
way, and the repo's notes had been treating the two mechanisms as
interchangeable.

## What it costs, in the metric built this morning

`break_even_wrong_cost(rate=0.369, coverage=0.423, m=1.0, certified_rate=0.718)`
= **0.103**.

A wrong answer need only cost **one tenth** of a right one for the corroboration
filter to pay — the lowest break-even measured today, against 0.60 for flood's
certificate and 2.95 for scheduling's. It costs no extra compute and it is the
first component in this repo that improves a **real-text** number.

## What would refute this

- One relation, one corpus, one crude notion of corroboration (a shared core
  token, ignoring stopwords). A real entity resolver would count mentions
  differently and could move both buckets.
- Repetition may be tracking **prominence** rather than correctness, and a
  company's *former* parent is often the most-discussed thing in its intro. The
  0.346 bucket argues against that reading but does not exclude it: 26 cases.
- The precision figures are over answered cases only; the ceiling — the gold
  parent named in the intro at all — is 0.696 and neither arm approaches it.
