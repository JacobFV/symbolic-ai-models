---
date: 2026-08-14
author: agent-lean-006
status: measured
related: [2026-08-14-the-lean-gate-closes-the-kernel-loses-to-an-arity-check,
          2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property,
          2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name]
---

# "I have no information" and "this is impossible" must not share a code path

## The mistake

`006`'s kernel rejects a candidate whose type does not fit the hole. Two
different things then arrive at the same branch:

* a symbol the episode **never declared** — a genuine unknown identifier, which
  real Lean would refuse;
* a symbol the elaborator **gave up on**, because two of its occurrences
  demanded incompatible types.

The second is *no information*. It was being answered "impossible".

## What it cost

The first full 179-lesson gate reported the `declared` arm at gold survival
**0.9151** — inside the pre-registered "worse than dead" row, which would have
been written up as a fact about the curriculum: *the kernel cuts the right
answer out 8.5% of the time.*

**221 of those 232 lost gold answers were demoted symbols.** Fixing the branch
moved the arm to **0.9843** and moved its pre-registered verdict from "worse
than dead" to "build". A five-line branch was the whole difference between two
readings of a table that had been fixed in advance precisely so the reading
could not drift.

The final verdict did not change — the arm still loses to the arity floor, so
the line still closes — but it closed *for the right reason* rather than for a
fabricated one, and that was luck, not care.

## Why nothing would have caught it

Every guard was pointed elsewhere and all of them passed. The renaming control
passed: demotion is renaming-invariant. The hidden-answer control passed:
demotion does not read the answer. The round trip passed. The `shifted` control
passed and looked healthy. **A filter that over-rejects for a bad reason looks
exactly like a filter that over-rejects for a good one** — the number is in
range, the controls behave, and the only thing wrong is the meaning.

What surfaced it was asking a question no test asks: *why* was each gold answer
refused? Bucketing the refusals by reason and reading the buckets took two
minutes and the answer was one bucket, 95% of the losses, with a name on it.

## The guards

1. **A rejection carries its reason, and the reasons are counted.**
   `Elaboration.verdict` returns `ok | undeclared | mismatch | saturation |
   duplicate field | wrong name` rather than a bool, and `symbolic-ai-lean gate`
   prints the distribution — for every filter, and separately for the gold
   answers each filter cut. A prune rate is a sum over mechanisms, and only some
   of them are the mechanism being claimed.
2. **Abstention is a verdict, and it is not the negative one.** This repo
   already knows the model-side version — an abstaining model must land on the
   prior, not on chance (`_forward_graph`'s mixture), and where it does not, it
   scores 0.0431 against chance 0.1034. This is the same rule one layer down: a
   component with nothing to say must return the permissive answer.
3. **Pin it as a test, not as a resolution.** `test_lean_elaborate.py`::
   `test_a_symbol_the_elaborator_gave_up_on_is_possible_in_every_mode` builds
   the collision by hand (`push` as both a binary predicate and a leaf) and
   asserts the verdict is `ok` in all three arms.

## The general form

**Wherever a component can fail to know something, check which of its outputs
the failure lands on.** If "unknown" shares an output with "no", the component
is quietly asserting the negative every time it is ignorant — and ignorance is
usually the common case, so the assertion dominates the number.
