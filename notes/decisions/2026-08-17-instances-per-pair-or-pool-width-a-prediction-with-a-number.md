---
date: 2026-08-17
author: lead
status: preregistration
related: [2026-08-17-sixty-pairs-seen-three-times-each-and-the-lift-is-still-0614,
          2026-08-17-the-pair-count-curve-and-a-correction-to-yesterdays-block,
          2026-08-13-no-null-from-an-undertrained-budget]
---

# If the pair curve is about supervision, k=60 at forty training seeds lands on k=24 at twenty

## What is being tested, and why it is the interpretation rather than the number

The pair-count curve measured `acc | derived, not copyable` falling 0.989 →
1.000 → 0.896 → 0.641 as the pool widens 6 → 12 → 24 → 60. The write-up read
that as a **data** curve — the fall tracks instances-per-pair (≈30, 15, 7.7, 3),
not pool width — and said so as an interpretation with the direct test named and
unrun.

That interpretation is load-bearing. If it is wrong the honest statement is "the
model holds about twenty-four pairs", which is a capacity claim and a much weaker
result than "it induces a corpus-wide correspondence and the curve is
supervision".

`notes/lessons/2026-08-13-no-null-from-an-undertrained-budget.md` is the standing
reason to check: this repo has already published one null that was an
undertrained budget wearing an architecture's name.

## The prediction, with a number

Raising `n_train` from 20 to 40 doubles instances-per-pair at fixed pool width.
So the two readings make **different, non-overlapping** predictions, and the
comparison is against a rung that already exists rather than against a hope:

| arm | pool | `n_train` | instances/pair | measured | predicted |
|---|---:|---:|---:|---:|---|
| k24 | 24 | 20 | ~7.7 | **0.896** | — |
| k12 | 12 | 20 | ~15 | **1.000** | — |
| **k60** | 60 | **40** | **~6** | ? | **≈ 0.85–0.92, i.e. near k24@20** |
| **k24** | 24 | **40** | **~15** | ? | **≈ 0.97–1.00, i.e. near k12@20** |

**The claim is that instances-per-pair predicts the score and pool width does
not.** k60@40 has ~6 instances per pair, slightly fewer than k24@20's 7.7, so it
should land just below 0.896. k24@40 has ~15, matching k12@20, so it should land
near 1.000.

## What refutes it

- **k60@40 stays near 0.641.** Doubling the supervision bought nothing, the score
  is a function of pool width, and the result is a capacity claim. This is the
  outcome that would force the previous finding to be restated.
- **k60@40 overshoots to ≈1.000.** Then instances-per-pair is not the variable
  either — something about `n_train` beyond per-pair supervision is doing the
  work, most likely the rest of the rule set getting better and carrying the
  bucket, and the decomposition is wrong in a third way.
- **Either control rises above its blind marginal.** Then that rung is admitting
  noise and nothing at it is readable, whatever the treatment says.

## The confound, named before the run

Raising `n_train` raises supervision for **everything**, not only for the derived
pairs. So a rise at k60@40 is consistent with "more instances per pair" *and*
with "a better model overall". That is why the prediction is stated as a
**match to an existing rung** rather than as "it goes up": if k60@40 lands on
k24@20 — same instances-per-pair, pool width two and a half times larger — the
match is evidence that per-pair supervision is the variable, in a way that a bare
increase would not be.

The residual confound stays real and is not removable by this design: pooled
accuracy will also move, and `acc | rest, not copyable` is the column to watch as
the check on it.

## Bookkeeping

`scripts/derived_split.py` pins `N_TRAIN = 20` so the derivation floor sees
exactly the evidence the models did. It needs to follow the run's `n_train` or
the floor and the model are fitted on different corpora — a `--n-train` flag,
defaulting to 20 so every published row is unaffected.
