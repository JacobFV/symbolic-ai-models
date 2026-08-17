---
date: 2026-08-17
author: lead
status: preregistration
related: [2026-08-17-the-per-guard-floor-keeps-the-channel-and-drops-the-chosen-constant,
          2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control,
          2026-08-15-the-kg-arms-are-a-null-and-the-quarter-that-mattered-did-not-move,
          2026-08-13-a-control-that-could-fail]
---

# Point the most permissive model in the repo at an arm where the answer is provably nothing

## The weakness being tested

`frontier-008` replaced a global precision floor with each guard's own modal
rate. Its finding named the open risk against itself:

> The floor is `const`'s precision, and `const` is one of the resolvers being
> floored. So a guard where `const` happens to be weak is a guard where
> everything is admitted. A guard whose answers are merely **noisy** looks
> identical to one whose answers are **structured but not modal**, and the floor
> cannot tell them apart.

That is an argument. It needs an arm where "structured" is *known* to be absent,
so that anything the model finds is definitionally noise.

## Why the `kg:` arms are that test

`kg:wordnet` re-labels the curriculum from a knowledge graph; `kg:wordnet-shuffled`
does the same from a **degree-preserving scramble** of it. The repo has already
established, and written down as a lesson, that those two arms are *one problem
under a relabelling*: to a learner whose only input is this corpus they are
isomorphic, so the difference between them **cannot** carry signal.

Measured over twenty models: mean `−0.0013`, and `kg:wordnet-shuffled` tied its
treatment. That is a null with a proof, which is exactly what makes it useful
here — it is not "we found nothing", it is "there is nothing to find".

So: **any model showing a systematic gap between `kg:wordnet` and
`kg:wordnet-shuffled` is fitting noise, and the size of the gap is a direct
measure of how much noise its admission rule lets through.** That is a control
that can fail, on an arm nobody chose for this model.

## Predictions, before the numbers

1. **`frontier-008`'s `label_acc` gap between `kg:wordnet` and
   `kg:wordnet-shuffled` is ≤ 0.005 in absolute value** — the same region the
   twenty published models occupy (mean −0.0013).
2. **`frontier-001`'s gap is the same size.** It is the strict-floor model, so if
   the permissive floor admitted noise the two would differ, and the comparison
   between them is the actual measurement — a gap for `-008` and none for `-001`
   is the refutation.
3. **Both models' pooled `label_acc` on `kg:wordnet` is close to their
   `base` figures** (0.4414 and 0.4042), since the `kg:` manipulation relabels
   rather than restructures.

## What refutes what

- **`frontier-008` shows a gap ≳ 0.01 where `frontier-001` does not.** The
  per-guard floor admits noise at a rate that shows up on a provable null, and
  the derivability result — which rests on that floor — needs re-examining with
  that in hand. This is the outcome that would matter.
- **Both models show a gap.** Then the noise is in the shared machinery rather
  than in the floor, and the twenty published models' −0.0013 becomes the thing
  needing explanation.
- **Neither shows a gap.** The floor does not detectably admit noise on an arm
  where noise is all there is. That does not prove it never does — a null result
  from a control is weaker than a failure — and the write-up must say so rather
  than promote it into a clean bill of health.

## What this cannot show

The `kg:` arms have their own known limitation: they are a null *by
construction*, so they cannot distinguish "the floor is well-behaved" from "this
arm has no structure for any floor to over-fit". A stronger version would need an
arm with known noise of a *chosen* magnitude, which does not exist here. Stated
now so the result is not read as more than it is.
