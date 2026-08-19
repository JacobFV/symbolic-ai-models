---
title: The explanation is wrong more often than the answer
date: 2026-08-19
status: measured
arm: solvency-fabrication
---

## The conditional, tested where it bites

Flood's value experiment left a conditional rather than a result: **values that
*gate* qualification silence; values that *feed* the computation fabricate.** A
mis-slotted mass disqualifies a vehicle, so nothing is cited about it and the
explanation stays honest.

Solvency's values feed. Revenue figures are summed, and `render_answer` states
the consolidated total as its central sentence:

> *"On the information available at 2026-05-31, consolidated revenue was 617.35
> USD against a requirement of 775.14 USD."*

200 seeds, rendered from the **read** reading:

| surface | verdict wrong | **stated total wrong** | mean \|error\| | `ungrounded` |
|---|---:|---:|---:|---:|
| clean | 0.000 | 0.000 | 0.000 | 0.000 |
| **hard filing** | **0.485** | **1.000** | **0.398** | **0.000** |
| hard both | 0.550 | **1.000** | **0.999** | **0.000** |

## The explanation is wrong twice as often as the answer

An admitted unofficial figure makes the **stated total wrong on every case** —
1.000 — while the **verdict** is wrong on 0.485, because a wrong sum only flips a
threshold test when it crosses the threshold.

So **more than half of all cases carry the right verdict justified by a false
number.** Flood's version of this was 1 in 13; solvency's is 1 in 2, and the
falsehood is not a peripheral citation but the sentence the answer is *about*.

The misstatement is large: **39.8%** of the true consolidated revenue on average,
and **99.9%** when both distractors are present — the stated total roughly
doubles.

## And nothing here can flag it

`ungrounded` fires on **0.000**, and it is right not to: the spurious figure **is**
in the world as read, so the number is supported by everything the checker knows.
Seventh appearance of *a check that reads part of the world inherits that part's
errors*.

Nor can the marker built this morning. `render.uncorroborated` flags channels with
no second reading, and solvency's revenue channel is the one the day's law says
admits **neither** — multi-valued, so no corroborating source; an aggregating
decision, so no insensitivity. It is the single worst cell in the table built this
afternoon, and this is what that cell costs when someone reads the explanation.

## The general statement

> **An explanation's error rate is not bounded by the answer's.** A derived figure
> is wrong whenever *any* of its inputs is, while the answer is wrong only when
> the error crosses a decision boundary. Reporting accuracy therefore says nothing
> about whether the account of it is true, and the gap grows with how much
> aggregation sits between the claims and the verdict.

That reverses the intuition the repo has been working from — that inspectability
is a *free* property of a symbolic pipeline, obtained by citing what the kernel
used. It is free only when the kernel uses claims directly. Every layer of
arithmetic between a claim and the answer is a layer where the explanation can be
wrong while the answer is right.

## The law at its extreme: sweep the perturbation and only one curve moves

The two error rates are governed by different things, and a magnitude sweep shows
it directly. `hard_relative` sets the spurious figure as a **relative
perturbation of the filer's own latest figure**, so the perturbation is `d` by
construction:

| relative perturbation | verdict wrong | **stated total wrong** | mean \|error\| |
|---|---:|---:|---:|
| none (clean) | 0.000 | 0.000 | 0.00000 |
| **0.001** | **0.000** | **0.985** | 0.00022 |
| 0.01 | 0.020 | 0.985 | 0.00224 |
| 0.05 | 0.075 | 0.985 | 0.01120 |
| 0.2 | 0.285 | 0.985 | 0.04481 |
| 1.0 | 0.445 | 0.985 | 0.22407 |

**At a 0.1% reading error the answer is perfect and the explanation is wrong 985
times in 1,000.** The explanation's error rate is **constant at 0.985 across four
orders of magnitude** while the verdict's climbs 0.000 → 0.445.

So the two are not merely unequal; they are **functions of different variables**.
The explanation is wrong iff *any* input is wrong, which is independent of
magnitude. The answer is wrong iff the error *crosses the boundary*, which is
entirely magnitude. The ratio does not have a bound — it diverges as the
perturbation shrinks.

## A harness bug worth recording, because it produced a confident wrong sweep

The first version of this sweep set the injected figure to
`own[-1] if own else case.threshold`. When the chosen filer had no figure usable
at the determination date, that **silently fell back to the threshold** — turning
a 0.1% perturbation into a 100% one. The sweep reported a mean error of 0.21 at
`d = 0.001` and a verdict-error rate of 0.06, and the shape looked like noise
rather than a law.

It now picks a filer that *has* a usable figure and **raises** if none does. That
is `notes/`'s standing rule — *no fallbacks, fail loudly* — biting in experiment
code rather than in the pipeline, where it is just as expensive and much easier to
miss.

## What would refute this

- One renderer and one distractor family. The 1.000 is because the injected figure
  always lands in the usable set; a distractor dated after the determination would
  be excluded and the total would stay true.
- `mean |error|` is driven by `hard_scale`, which is half the threshold by
  default. That parameter sets the magnitude and is quoted with it.
- The verdict-wrong rate of 0.485 depends on the threshold distribution; a domain
  whose decisions sit far from their boundaries would show an even wider gap
  between explanation error and answer error, not a narrower one.
