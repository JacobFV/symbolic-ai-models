---
title: A rate without its numerator is not a result — check the count before writing the sentence
date: 2026-08-19
kind: lesson
---

## The mistake

Publishing a rate, and a comparison drawn from it, without looking at how many
events it is made of. It happened **twice in two days** and both times the rate
looked ordinary — three per cent, thirteen per cent — while the count behind it
was single digits.

- **"The composition law holds to within 0.001."** Two-hop accuracy 0.031 over
  191 chains is **six successes**, against 6.1 expected. The 95% Wilson interval
  is [0.014, 0.067], which admits ratios to `p₁²` from 0.4 to 2.1. The agreement
  was at a resolution the sample does not have, and a third reader measured the
  next day gave k=4 and would have supported the opposite story.
- **"Hubs read 36% worse."** 17 successes in 135 hub articles. p = 0.044 on the
  headline comparison — real but fragile, and it would not survive correction for
  the four-bucket table printed beside it, whose top row is 1 success in 14.
- **"A fifth of the learned reader's correct answers are ones the patterns
  miss."** Five events.

## What it cost

One published headline withdrawn, two findings amended, and a day of work built
on a number that could not distinguish the hypothesis from its opposite. The
selective-ingestion sweep only caught it because it produced a *third* estimate
of the same quantity and the three did not agree.

## Why it keeps happening

**The denominator looks respectable.** 191 chains, 135 articles, 1,661 documents:
these read like adequate samples, and they are — for the *base* rate. They are
not adequate for a rate of 3%, where the effective sample is the numerator.
A composed query multiplies rates, so the numerator shrinks exactly where the
scientific interest is highest, and the write-up arrives at the moment of least
power.

## The guard

**Print the count next to every rate, in the script, before reading the result.**
Not in the note afterwards — in the output, so the number is seen while the
conclusion is still forming. `k/n = rate` costs nothing and would have stopped
both cases.

And a threshold worth naming: **below about 20 events, report the interval and
not the point.** At k=6 the interval spans a factor of five and no comparison
survives it. At k=94 (retrieval's hop-2 rate) or k=302 (real-text `parent`) the
point estimate is the result.

The related trap already on record is
`notes/lessons/` on slices — small *slices* inverting results. This is its
arithmetic cousin: not a biased subset, just too few events, and it is harder to
see because nothing about the data collection looks wrong.

## Where it does not apply

Rates near the middle with large denominators are fine: `parent` correct at
302/1,661 has a 95% interval of [0.164, 0.201], and the north star's 120/120 has
a lower bound of 0.969. The audit that produced this note found those solid; it
found three thin cells and all three were in the composed or subsetted arms.
