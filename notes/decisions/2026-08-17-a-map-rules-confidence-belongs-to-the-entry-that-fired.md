---
date: 2026-08-17
author: lead
status: preregistration
related: [2026-08-17-the-gate-cannot-tell-the-treatment-from-the-control,
          2026-08-17-an-average-cannot-see-a-sub-population,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# The gate must condition on the table key, because nothing else the model has separates the two populations

## Ruling out the obvious shapes first

[[2026-08-17-the-gate-cannot-tell-the-treatment-from-the-control]] measured that
the carrying rule's argmax is right **87/87** on the derived bucket and **0.205**
in the control, while the gate gives both **~0.32**. It left the shape of a
better gate open on purpose. Working it out rules out the candidates I would
otherwise have tried:

* **A per-rule gate cannot help.** `_offer` already computes each rule's
  precision over the fills where it *fires*, and `score` is the Wilson bound on
  exactly that. The carrying rule genuinely is right ~0.66 across its firing
  population. Giving it its own calibrator would return ~0.66 again.
* **A per-guard gate cannot help either**, for the reason
  `scripts/guard_ceiling.py` was written to report: the best guard covering the
  derived fills is 0.531 pure, so no guard separates the two populations. A gate
  keyed on the guard is keyed on something that does not distinguish them.

So the rule is right 100% on one sub-population and ~60% on another, and
**neither the rule nor its guard is the thing that tells them apart**.

## What does tell them apart: the key

A `map` rule is a table. Its entries are not equally reliable. The six entries
whose key is a *kind* are deterministic — the planted correspondence — and every
other entry in the 399-entry table is whatever the corpus happened to support.

The rule's `score` averages over all of them. **The entry that fired is the
sub-population**, and it is the one thing the model does have at prediction time.

So: a map rule's confidence should be the cross-fitted precision **of the entry
that fired**, not of the rule. Same machinery — the fold tables already exist,
and the Wilson bound already prices small samples, which matters because a
399-entry table has entries seen very few times.

This is the same sentence for the fourth time in one day — *an average cannot see
a sub-population* — applied one level below where it was last applied. Resolver
choice, then precision floor, then gate, now table entry.

## Predictions, before the numbers

1. **`bits | derived, not copyable` falls from 2.363 to below 1.0** on
   `derive:wordnet`. At a perfect argmax the calibration floor is
   `−log2(gate)`, so a gate near 0.9 on the six deterministic entries puts it
   near 0.15; 1.0 is a deliberately loose bar for the mixture and the fills where
   no rule fires.
2. **The control's bits do not improve materially** — stays ≥ 9.0 on
   `derive:wordnet-perm`. Under a per-episode permutation no entry is
   deterministic across folds, so per-key precision is low for every key and the
   gate stays small. **This is the load-bearing prediction:** a per-key gate that
   also sharpens the control is fitting noise per entry, and the whole thing is
   void.
3. **Accuracy does not move** in either arm, to three decimals. Gates scale a
   vote; they cannot reorder it. `MassCalibrator`'s own docstring says so.
4. **Pooled `label_bits` improves** on `runs/full179` against `frontier-008`'s
   7.141, by less than the derived bucket moves — the derived slot is 0.20% of
   positions, so a large pooled move would mean something other than this changed.

## What refutes it

- **Bits do not move on the derived bucket.** Then the entry is not the
  separator either, and I have run out of things the model has at prediction
  time — which would be a real result about the hypothesis language rather than
  the calibration.
- **The control sharpens too.** Per-key precision is overfitting to entries seen
  a handful of times, and the Wilson bound is not enough protection at this table
  size. Void.
- **Accuracy moves.** Then something other than the gate changed and the run is
  not the experiment.

## The overfitting risk, named

A 399-entry table over ~2,300 firing fills averages six fills per entry. Per-key
precision on six samples is a weak estimate, which is precisely why the bound
rather than the point estimate is used — and why prediction 2 is the one that
decides whether this is a gate or a memoriser. `min_count` on the per-key
estimate is a knob, and if it needs moving it gets moved **on the development
split** through `scripts/rsi_loop.py`, never on the derived bucket.
