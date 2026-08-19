---
title: A flag that means sound on one surface and 0.664 on another
date: 2026-08-19
status: measured
arm: refusing-reader
---

## Building the refusal the last finding named

`read_content_roles` is **0.988** interleaved, and in all three failures it knew
it was guessing: `needs` resolved by adjacency, `depot` still open, two
unresolved regions left, so which became the depot depended on document order.
That is detectable at read time with no ground truth, so the reader can refuse.

`read_content_roles_checked` now returns `(world, role_assignment_forced)`.

## Two results, and the second is the one that matters

| surface | n | accuracy | refused | coverage | **accuracy among forced** |
|---|---:|---:|---:|---:|---:|
| easy distractor | 252 | 0.9881 | 29 | 0.885 | **1.0000** |
| **hard distractor** | 252 | 0.6786 | 29 | 0.885 | **0.6637** |

**It works, and it is 10× more conservative than the failure.** On the published
surface it removes **3 of 3** errors and leaves soundness 1.000 — but gives up
**11.5%** of coverage to remove **1.2%** of error. Whether that is worth taking
depends on what a wrong answer costs; keeping the guess and reporting 0.988 is a
defensible alternative, and the reader should not make that choice for the
caller.

**And it is not a correctness flag.** On the `hard_distractors` surface accuracy
among the *forced* readings is **0.664**. The phantom link makes answers wrong
without touching role assignment, and this flag cannot see it — it refuses the
same 29 cases either way, because it is looking at something else entirely.

## Why that is the important half

A flag that means "sound" on one surface and 0.664 on another is **the same scope
error as quoting "grounded 1.000" without saying what it certifies** — and this
repo made that one three weeks of findings ago, on the renderer.

The pattern repeats because the mistake is natural: a check is built for one
failure mode, verified against that mode, and then its name promises more than it
delivers. `certain` promised correctness. The thing it actually computes is *the
lone-region roles were not guessed*.

So it is named `role_assignment_forced`, its docstring carries both numbers, and
`test_the_flag_is_not_a_correctness_flag` **asserts that forced-and-wrong cases
exist** — a test that fails if the flag ever starts looking like a guarantee.

## What I am not doing

Not shipping refusal as the default. It costs 10× the error it removes, and the
alternative — report 0.988 and say so — is honest and cheaper. The flag is
available for a caller who knows what a wrong answer costs them.

## What would refute this

- A cheaper detector for the *same* failure. This one refuses whenever the role
  assignment is unforced, which is far more often than the assignment is wrong;
  a detector that also used the value registry or adjacency margins might refuse
  only when the guess is close.
- A detector for the phantom-link mode. That failure is invisible here, and the
  certificate work is the machinery that addresses it — the two are complementary
  and neither covers the other.
