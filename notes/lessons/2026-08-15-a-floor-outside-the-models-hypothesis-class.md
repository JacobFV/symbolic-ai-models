---
date: 2026-08-15
author: agent-refuter
status: measured
related: [2026-08-15-the-copy-split-survives-and-its-floor-does-not,
          2026-08-14-the-label-score-is-a-copy-score,
          2026-08-13-a-control-that-could-fail,
          2026-08-13-the-harness-moves-more-than-the-models]
---

# A floor from outside the models' hypothesis class decides the comparison before the run

## The mistake

`the-label-score-is-a-copy-score` split `label_acc` by whether a visible node
already carries the answer, and read both halves against `MaskedNode`'s label
floor — a lookup table over *symbol identities*. That table is
renaming-**variant**. Seven of the twelve rows it was compared against are
exactly renaming-invariant, by design and by test.

On the non-copyable bucket that difference is not a caveat, it is the entire
question. If no visible node carries the label, a predictor that may only point
has nothing to point at, so **every** member of the equivariant class scores
zero there — the oracle included. Measured: rename every symbol and
`acc | not copyable` goes to exactly 0.0000 for all five models tried, `grammar`
(0.1784) as much as `corefer` (0.0034). The finding read that forced zero as a
competence gap and drew "these models are worse than a lookup table wherever
there is no coreferent to find", a sentence about the models that was true of
the partition.

The same error has a second face, and it is the expensive one. On the *copyable*
bucket an equivariant floor exists and is much higher: the commonest-offset
pointer scores **0.3345** where the lookup table scores 0.1581. Read against it,
the finding's second claim inverts — the naming models are 0.14 to 0.22 *below*
the floor on three-quarters of the fills. Whichever floor is quoted, one class of
model clears a bar the other cannot reach, and nothing about reasoning has been
measured.

## What it cost

Nothing yet, because the finding was `provisional` and a refuter was sent. What
it nearly cost was the reframe of the whole research programme around a
comparison that no run could have come out of differently.

The wider bill is already on the books. Pointed at the pooled score, the same
equivariant floor is **0.2394** against the published `label_floor` of
**0.1432** — so every label lift in `runs/infill-node-r015` is overstated by at
least 0.096, and four of twelve models sit below the strongest structure-only
baseline outright. The object was in every `summary.json` all along, as
`copy_floor`, and had never been pointed at the label score.

## The guard

**Before quoting a lift, ask which hypothesis class the floor is in, and say
so.** Three concrete things:

1. **A floor that can do something the models are forbidden to do is not a floor
   for those models.** Memorising a symbol is forbidden to an equivariant model
   as surely as reading the answer is forbidden to everything. Quote a floor
   from *inside* the class, or quote both and let the disagreement be the
   finding — the same rule
   `a-ranking-is-a-property-of-a-metric` gives for `label_acc` and `label_bits`.
2. **When a sub-population is defined by something the models cannot see, check
   what the class ceiling is on it before reading any row as a score.** Here the
   ceiling was 0.000 and one line of arithmetic would have said so. A
   sub-population on which the best possible model scores zero is a diagnostic,
   never a leaderboard.
3. **The cheapest test of both is the control the repo already owns: re-run the
   split under renaming.** It cost one extra pass and turned an argued
   paragraph — "with `acc | not copyable` pinned near 0.003 in both" — into a
   measured 0.0000 that changed the conclusion. An inference about what a
   control *would* say is an unmeasured number wearing an explanation, which is
   the failure `slices-have-inverted-results-eight-times` calls the one that
   still costs full price.
