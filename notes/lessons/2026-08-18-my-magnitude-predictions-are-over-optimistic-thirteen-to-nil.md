---
title: My direction predictions are good and my magnitude predictions are over-optimistic, thirteen to nil
date: 2026-08-18
author: lead
status: settled
tags: [calibration, epistemics, autonomy]
---

## The measurement

The mandate asks for periodic inspection of prediction error, and
`notes/autonomy/predictions.jsonl` had accumulated **36 hypotheses with recorded
outcomes** across 37 arms without anyone looking at them as a set.

| | n | mean confidence held |
|---|---:|---:|
| calibrated — landed inside the stated band | 9 | **0.69** |
| partial — direction right, magnitude out | 21 | 0.60 |
| **wrong** — headline or mechanism wrong | **6** | **0.58** |

**Direction of the magnitude error, where it is classifiable: 13
over-optimistic, 1 mixed, 0 under-optimistic.**

## What that says, in two parts

**1. Confidence carries real signal.** The predictions I got wrong were held at a
mean of **0.58** and the calibrated ones at **0.69**. I was *less sure* about the
ones I missed, which is what a working confidence estimate is supposed to do. And
**35 of 36 stated a falsifier in advance**; several fired and were honoured —
the geography arm, the `certain`-tier accuracy at 0.666 against a pre-registered
0.7, the `r < 1.2` line on prompt narrowing.

**2. Magnitude is biased, and in one direction only.** Thirteen to nil is not
noise. A sample:

| I predicted | it was |
|---|---|
| gazetteer closes the extraction gap, 0.65–0.80 | 0.522 zero-shot, 0.577 hybrid |
| bridge coverage 40–70% | 22.3% |
| prompt narrowing `r` = 1.5–3× | **0.68×** — it made the prompt *bigger* |
| extractor `certain` tier 0.85–0.95 | 0.666 |
| component extraction on unseen 0.50–0.70 | 0.379 |
| narrowed-band coverage at a=0.95 70–85% | 63.3% |

Every one of those is a mechanism I expected to help more than it did. **Nothing
this session delivered more than I predicted except by accident of a band's upper
edge.**

## The mechanism, as best I can see it

I predict the magnitude a mechanism *would* have if it were the only thing
operating, and then the world supplies a second constraint I did not price:
coverage, correlation, a selection effect, an offsetting cost. The gazetteer was
right about names and silent about the 65% of components carrying no registry
match. Narrowing was right that a k-way choice is easier and silent about the
tokens the choice costs.

## The guard

**Shade magnitude predictions toward the bottom of the band, and state the second
constraint explicitly before predicting.** Concretely, before writing a range,
answer: *what else has to be true for this magnitude to be reached, and have I
measured it?* In every row above the answer was "coverage" or "a cost I did not
count", and in every row it was measurable in advance.

The cheap version, and it costs one line in the prediction record: add a
`what_would_cap_this` field naming the second constraint. A prediction whose cap
is unmeasured should be stated as a **bound**, not a band —
*"at most X, and the binding constraint is Y"* — which is both more honest and
more useful than a range whose lower end is where the answer keeps landing.

**Do not adjust confidence.** It is working: 0.69 on the ones I got right, 0.58
on the ones I did not. The bias is in the numbers, not in the sureness.
