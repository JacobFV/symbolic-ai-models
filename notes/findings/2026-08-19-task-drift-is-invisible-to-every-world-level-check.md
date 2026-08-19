---
title: Task drift is invisible to every world-level check
date: 2026-08-19
status: measured
arm: task-drift
---

## The boundary the maintenance finding named

The signature-determinacy audit predicts robustness to **surface** change and
says nothing about a change in the **task**. So: a weight restriction, admitting
light vehicles and refusing heavy ones — semantics the world **cannot express**,
unlike flooding, which refuses everything.

| | catches |
|---|---:|
| answers wrong | **22 / 22 (100%)** |
| `role_assignment_forced` | **0 / 22** |
| role-independent certificate | **0 / 22** |
| `omits_load_bearing` | **0 / 22** |
| **`unconsumed` sentences** | **22 / 22** |

Catches counted only where the check is **silent without the drift**, because
`omits_load_bearing` fires on every template-rendered paragraph anyway.

## Why the world-level checks cannot see it

Every one of them inspects the **read world**. A claim kind the reader has no
branch for never enters that world, so there is nothing for them to find. This is
the lesson that has now appeared four times — *a check that reads part of the
world inherits that part's errors* — arriving one level up, at the task rather
than at the roles.

The text still contains the sentence. `unconsumed` counts sentences whose removal
leaves the read world unchanged, and it catches every case, for less than the cost
of solving once.

Two things it is not, both learned by getting them wrong first:

- **Not entity familiarity.** The restricted region already appears in the link
  claims, so a check asking whether a sentence's entities were known caught
  **0 of 22**. Consumption is not familiarity.
- **Not a presence test.** Clean text already has distractors that consume to
  nothing, so the signal is an **increase** over the document's own baseline.

## What this costs to have

`len(sentences)` reads at 0.2 ms each, against a 9 ms answer — cheaper than
solving. Nothing in this repo was computing it.

## The honest scope

This detects that the reader **ignored something**, not that the answer is wrong.
A document with a genuinely irrelevant sentence raises the count without any
error, which is why the baseline comparison is part of the check rather than a
refinement of it. It is a **drift alarm**, not a correctness oracle — and after
four checks whose names promised more than they computed, that distinction is
stated in the docstring rather than left to the name.

## What would refute this

- One drift kind, on one domain. A task change that the reader *partially*
  parses would be consumed and invisible here, and that is the more likely shape
  in practice than a wholly foreign sentence.
- The 22 cases are those where the restriction changes the answer; cases where it
  binds on nobody are excluded by construction and would dilute both columns.
