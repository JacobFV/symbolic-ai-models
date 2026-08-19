---
title: The episode-level benchmark's majority floor is fitted on the evaluation answers, so it inflates as episodes-per-lesson shrinks
date: 2026-08-18
author: lead
status: provisional
tags: [lesson, floors, benchmark, instruments]
---

## What was found, in passing

`CurriculumReport.floor` is `max(uniform, per-lesson majority, best shortcut)`.
The **majority** term counts gold answers **on the evaluation episodes
themselves** (`by_lesson[r.lesson_id][r.answer] += 1`), so it knows the eval
label distribution and its strength depends on how many episodes each lesson has:

| episodes/lesson | episodes | uniform | **majority** | shortcut | floor | winner |
|---:|---:|---:|---:|---:|---:|---|
| 4 | 716 | 0.2595 | **0.4832** | 0.2765 | 0.4832 | majority |
| 8 | 1,432 | 0.2588 | **0.3813** | 0.2744 | 0.3813 | majority |
| 16 | 2,864 | 0.2581 | **0.3317** | 0.2633 | 0.3317 | majority |
| 32 | 5,728 | 0.2577 | **0.2971** | 0.2685 | 0.2971 | majority |

**The floor moves 0.483 → 0.297 purely by adding evaluation episodes.** At four
per lesson, "always answer this lesson's most common gold label" is right nearly
half the time by chance, because with four draws the modal count is usually two.

`runs/agents-full179` reports `floor_by: shortcut` at **0.264**, which matches no
row here — that run used a different episode set, so its floor and any score
computed at another `n_eval` are **not comparable**.

## Why it matters

A lift against this floor is not a property of the model alone; it is a property
of the model *and the eval size*. Two runs at different `n_eval` cannot be
compared, and the smaller one looks worse for a reason unrelated to the model.

This is `APPROACH.md` property 4 — "a floor built from every feature the model
sees" — failing in the *opposite* direction from the usual one. The repo's
recorded danger is floors set too low; this one is set too high, by peeking at
the answers it is grading.

## The fix, not applied

Fit the majority term on **training** episodes and score it on eval, exactly as
the task floors do (`task.floor(eval_eps, tok, train_eps)`). Then it is a
baseline rather than an oracle and stops depending on eval size.

Recorded rather than fixed: the programme was redirected to **text→world** before
this arm went anywhere, and **no published number rests on it** — the only
observed value, `corefer-001` at accuracy 0.2486 against a floor of 0.4832, is
discarded with the arm.
