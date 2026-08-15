---
date: 2026-08-14
author: agent-generation
status: provisional
related: [2026-08-14-the-label-score-is-a-copy-score,
          2026-08-14-the-infilling-ladder-preregistration,
          2026-08-14-the-curriculums-own-question-asked-on-the-graph]
---

# Rung 1: raising the mask rate moves the opportunity to copy, not the ability

**All 179 lessons, 716 evaluation episodes, `runs/infill-node-r015` and
`runs/infill-node-r035`, twelve pre-registered models plus floors refitted at
each rate.** The 0.60 and 0.90 arms were still running when this was written and
are marked as such; nothing here is averaged over rates.

## The two pre-registered expectations, and what happened

**R1 — "pointer models degrade fastest".** *Half right, and the axis was
wrong.* Pointer-bearing models do fall, but so do models with no pointer head at
all (`omegaclaw_rank-001`, `omegaclaw_ctx-001`), by the same amount, while
pointer-bearing `ruleinduce-001` falls less. The axis that separates is
renaming-invariance, not `source_votes` — see
`notes/findings/2026-08-14-the-label-score-is-a-copy-score.md`. Recorded as a
wrong pre-registration rather than re-drawn.

**R2 — "the curve falls off a cliff at 0.35".** *Refuted.* The registered
threshold was: a cliff means the mean pointer `label_lift` at 0.35 is below half
its 0.15 value. It is 0.222 against 0.250 — **89% retained**, not 50%.

## The curve, with its floors

`corefer-001`, the repo's best label model:

| mask rate | copy ceiling | `label_acc` | `label_floor` | `label_lift` | `label_bits` | scored fills |
|---:|---:|---:|---:|---:|---:|---:|
| **0.15** | 0.722 | 0.357 | 0.143 | 0.250 | 6.955 | 5,233 |
| **0.35** | 0.680 | 0.332 | 0.142 | 0.222 | 7.399 | 12,264 |
| 0.60 | *running* | | | | | |
| 0.90 | *running* | | | | | |

The floor barely moves (0.143 → 0.142) because a structure-only lookup does not
care how much else is hidden. The **copy ceiling** does move, and it is the
number the accuracy tracks.

## The pre-registered prediction, and it holds

`notes/findings/2026-08-14-the-label-score-is-a-copy-score.md` was committed
while this arm was mid-flight, predicting: *raising the mask rate lowers the
copyable share mechanically, so a pointer's `label_acc` should track
`copyable_share(rate) × acc|copyable` with `acc|copyable` roughly flat; if
`acc|copyable` itself collapses, the models are losing the ability to copy and
not merely the opportunity, and that is a second effect this account does not
predict.*

| | 0.15 | 0.35 |
|---|---:|---:|
| copyable share | 0.722 | 0.680 |
| `corefer-001` acc \| copyable | 0.494 | **0.488** |
| `corefer-001` acc \| not copyable | 0.003 | **0.003** |
| `corefer-001` acc (published) | 0.357 | 0.332 |
| predicted from the share alone | — | **0.337** |
| `ptrgen-001` acc \| copyable | 0.462 | 0.450 |
| `ptrgen-001` acc \| not copyable | 0.010 | 0.015 |
| floor, copyable / not | 0.158 / 0.106 | 0.159 / 0.106 |

Six models measured both ways, `acc | copyable` then `acc | not`:

| model | 0.15 | 0.35 |
|---|---|---|
| `corefer-001` | 0.494 / 0.003 | 0.488 / 0.003 |
| `ptrgen-001` | 0.462 / 0.010 | 0.450 / 0.015 |
| `routes-001` | 0.448 / 0.000 | 0.416 / 0.000 |
| `vsa_perm-002` | 0.435 / 0.043 | 0.442 / 0.035 |
| `ruleinduce-001` | 0.425 / 0.081 | 0.380 / 0.073 |
| `evidence-001` | 0.303 / 0.001 | 0.324 / 0.002 |
| `grammar-001` | 0.191 / 0.178 | 0.149 / 0.151 |

**Both conditional accuracies are flat and both floors are flat.** The entire
0.357 → 0.332 move is the copyable share falling from 0.722 to 0.680; carrying
`acc|copyable` forward unchanged predicts 0.337 against an observed 0.332.

So the mask rate is not a difficulty knob for these models in the way the ladder
assumed. It is a **supply** knob: it controls how often the answer is still
visible somewhere else, and the models convert that supply at a fixed rate.
Whether that stays true at 0.60 and 0.90 — where the ceiling must eventually
collapse — is the part of the curve still running, and it is the interesting
part, because there the supply runs out and the models have nowhere to go but the
0.003 column.

## Rung 4's bound, at both rates

The render is a deterministic function of the term, so `exact_match <=` graph
exact-match (`scripts/graph_exact.py`, run's own draw, `label_acc` bit-identical
to the published one):

| `corefer-001` | 0.15 | 0.35 |
|---|---:|---:|
| `label_acc` | 0.357 | 0.332 |
| every hidden label right, per episode | **0.0380** | **0.0014** |
| …and every masked type too | 0.0352 | 0.0014 |

A 7% fall in the published number is a **25-fold** fall in whole-episode
exactness, because there are about seventeen labels to get right at once instead
of seven. Partial credit and exactness are not the same measurement rescaled;
they diverge with the size of the hole, which is precisely the axis this rung
varies.

All twelve rows at `mask_rate=0.15`, ordered by whole-episode exactness — the
first `exact_match` bound this repo has that means anything:

| model | `label_acc` | every label right | …and every type |
|---|---:|---:|---:|
| `ruleinduce-001` | 0.329 | **0.0394** | **0.0380** |
| `corefer-001` | 0.357 | 0.0380 | 0.0352 |
| `vsa_perm-002` | 0.326 | 0.0338 | 0.0309 |
| `omegaclaw_rank-001` | 0.356 | 0.0309 | 0.0183 |
| `grammar-001` | 0.187 | 0.0295 | 0.0253 |
| `ptrgen-001` | 0.336 | 0.0281 | 0.0267 |
| `routes-001` | 0.323 | 0.0281 | 0.0141 |
| `brill-001` | 0.290 | 0.0253 | 0.0183 |
| `evidence-001` | 0.219 | 0.0225 | 0.0141 |
| `ngram-001` | 0.170 | 0.0169 | 0.0084 |

The ordering is not the `label_acc` ordering: `ruleinduce-001` is fourth on the
published number and first here, `omegaclaw_rank-001` is second and fourth,
`grammar-001` is ninth and fifth. Twelve models spanning 0.109–0.357 of partial
credit span 0.008–0.038 of whole-episode correctness, and the map between the two
is not monotone.

## What would refute this

- `acc|copyable` falling materially at 0.60 or 0.90. That would be a second
  effect — losing the ability to copy, not just the opportunity — and this note
  does not predict it.
- The copy ceiling *not* collapsing at 0.90. `target_source` accepts any visible
  same-label node, and with 10% of nodes visible a repeated label often still has
  one, so the collapse is not as automatic as it sounds. If the ceiling holds up,
  the 0.90 arm is a much weaker test of generation than the ladder assumed.

## Reproducibility of the 0.15 rows, checked

The 0.15 arm re-runs the published setting, and it reproduces `runs/full179`:
`corefer-001` 0.357, `omegaclaw_rank-001` 0.356, `brill-001` 0.290,
`grammar-001` 0.187, `ngram-001` 0.170, `ctw-001` 0.109, copy ceiling 0.722,
renaming drops 0.130 / 0.159 / 0.143 — the rows `RESEARCH_LOG.md` quotes.

`label_acc` is identical to nine decimal places for `corefer-001` and
`evidence-001`; `label_bits` differs by +0.0019 to +0.0043, which is below this
repo's own ~0.005 noise band and reproduces the already-recorded `master` drift
digit for digit (6.951828893 → 6.954734342). `routes-001`'s accuracy moved by
1.91e-04, which is new — see
`notes/questions/2026-08-14-the-master-drift-also-moved-an-accuracy.md`. The
masking itself is provably unmoved: `test_the_scattered_draw_is_frozen` hashes
the whole batch at four rates against the value computed from the branch point's
`batch.py`.
