---
date: 2026-08-15
author: agent-r090
status: preregistration
related: [2026-08-15-the-supply-model-breaks-at-ninety-percent-masking,
          2026-08-14-the-mask-rate-curve-moves-the-opportunity-not-the-ability,
          2026-08-15-the-copy-split-survives-and-its-floor-does-not,
          2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name]
---

# Which way the 0.90 split will go, written before the refit finishes

> **Outcome, same day: both halves held.** `acc | copyable` **0.5971** against a
> predicted ≈0.59, `acc | not copyable` **0.0013** against a predicted ≤0.002.
> The mechanism half held too — the mix over label multiplicity carries about two
> thirds of the rise — and the third refutation condition below turned out to be
> the interesting one: stratified by evidence *concentration* rather than by
> multiplicity, the 0.90 arm is **worse**, not equal. See
> `notes/findings/2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model.md`.

`notes/questions/2026-08-15-the-supply-model-breaks-at-ninety-percent-masking.md`
names three stories and deliberately declines to choose. This note chooses, with
its reasoning, **before the split exists**, so that the reading cannot drift
toward whichever story the number flatters. The refit
(`runs/refute-node-r090`, all twelve models, `runs/refit-node-r015`, six) was
launched before this file was written and neither has produced a split.

## The arithmetic the two live stories have to satisfy

From `runs/infill-node-r090/corefer-001/summary.json`, `final.node`:
`label_acc` **0.18101733**, `copy_ceiling` **0.30166398**, `label_n` 31,671.
From the 0.15 split: `acc | copyable` 0.4936, `acc | not` 0.0034.

    predicted = 0.3016640 x 0.4936 + 0.6983360 x 0.0034 = 0.151275
    observed  = 0.181017                       error = +0.029742

Exactly one of the two conditionals has to absorb 0.0297:

| story | what it needs at 0.90 | move from 0.15 |
|---|---|---|
| **1. survivorship** — `acc \| copyable` rises | `acc \| copyable` = **0.5922** at `acc \| not` = 0.0034 | **+0.099** |
| **2. the back-off** — `acc \| not` rises | `acc \| not` = **0.0460** at `acc \| copyable` = 0.4936 | **+0.043** |

Both are large. Whatever the split says, it will say it unambiguously — this is
not a 0.005 question.

## Story 3 cannot be the answer, and the arithmetic says so

The floor falls 0.1432 -> 0.1259 across the curve. **The floor does not appear in
the supply model.** The prediction is of `label_acc`, and `label_acc` is computed
without reference to any floor, so no movement of the floor can produce or
remove a 0.030 error in it. Story 3 is a real observation about what the *lift*
means and it is not a candidate explanation of this miss. Recorded so that it
does not get picked up later as one.

A fourth story that could have been the answer and is already dead: the *share*
being the wrong share. `copy_ceiling` is over `copy_scored_n` (34,978 at 0.90)
while `label_acc` is over `label_n` (31,671), so they could have been different
populations. They are not — at 0.15 the refuter counted 3,776 copyable of 5,233
scored, and 3776/5233 = 0.721575 is the published `copy_ceiling` to six places.
`copyable_split.py` reports its own `copyable_share`, so the refit checks this
again at 0.90 for free.

## The prediction: story 1, and story 2 is already bounded out

**Predicted: `acc | copyable` ≈ 0.59 at 0.90 and `acc | not copyable` ≤ 0.002.**

The bound on story 2 comes from a number that is already in the run directory
and needed no new compute. `renaming` in the same `summary.json`:

    label_acc 0.18229710   renamed_label_acc 0.18195009   drop 0.00034700

`2026-08-15-the-copy-split-survives-and-its-floor-does-not` measured that under
renaming `acc | not copyable` is **exactly 0.0000** for all five models tried,
`grammar-001` included, and argued it is a property of the partition: if no
*visible* node carries the hidden label, a predictor with no memorised symbol
table has nothing to emit. Take that as renamed `acc | not` = 0 and

    drop = (c_plain - c_renamed) x 0.3017 + n_plain x 0.6983

Story 2 needs `n_plain` = 0.046, contributing 0.0321 to the pooled score, against
a measured total drop of 0.00035. It could only survive if renaming *raised*
the copyable column by 0.106 — the opposite of the 0.0015 fall measured at 0.15
and not a thing a symbol permutation does. So **the memorisation channel supplies
at most about 0.0005 of `corefer-001`'s accuracy at 0.90**, and it is not where
the missing 0.030 comes from.

The positive half of the prediction is mechanical. `target_source` accepts a
same-label **visible** node. With 10% of nodes visible, a label surviving into
the copyable bucket is overwhelmingly a label with high multiplicity in the graph
— a label occurring k times has roughly 1 - 0.9^k chance of leaving a visible
copy, which is 19% at k=2 and 65% at k=10. High multiplicity is exactly what
makes a fill easy to point at. So the copyable bucket at 0.90 is not a random 30%
of the fills, it is the most repeated 30%, and `acc | copyable` should rise for a
reason that has nothing to do with the model getting better.

## What would refute this note

- `acc | not copyable` for `corefer-001` at 0.90 coming back **≥ 0.02**. That
  kills the prediction and also contradicts the renaming drop, which would make
  the renaming check the thing to investigate rather than the model.
- `acc | copyable` coming back **≤ 0.52**, which would leave the miss unexplained
  by either conditional and mean the decomposition itself does not close — most
  likely because `copyable_share` at 0.90 is not `copy_ceiling`.
- The mechanism half: `acc | copyable` rising while, **stratified by the number
  of visible same-label nodes**, each stratum is unchanged from 0.15 and the
  bucket's mix has not shifted toward high-multiplicity labels. Then the rise is
  real ability and not survivorship, and the note is wrong about why even if
  right about which column moved. This is why `runs/refit-node-r015` is being
  refitted alongside: the stratified comparison needs weights at both ends.

## What this does to the mask-rate curve's headline

If story 1 holds, *"raising the mask rate moves the opportunity, not the
ability"* survives at 0.90 in the sense that matters — nothing new is being
reconstructed — but its clean form, both conditionals flat, does **not**. The
honest statement becomes: the conditionals are flat over 0.15-0.60 and the
copyable bucket becomes a different, easier population by 0.90, so the fourth
point is the least comparable one on the curve rather than the most demanding.
