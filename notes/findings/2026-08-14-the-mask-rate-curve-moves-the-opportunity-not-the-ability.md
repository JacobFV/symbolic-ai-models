---
date: 2026-08-14
author: agent-generation
status: provisional
related: [2026-08-14-the-label-score-is-a-copy-score,
          2026-08-14-the-infilling-ladder-preregistration,
          2026-08-14-the-curriculums-own-question-asked-on-the-graph]
---

# Rung 1: raising the mask rate moves the opportunity to copy, not the ability

> **Corrected in two places, 2026-08-15.**
> **(a) The 0.90 arm, and the title's second half.**
> `notes/findings/2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model.md`
> computed the split this note left running. `acc | copyable` **rises** to
> 0.5971 at `mask_rate=0.90` — the flat-conditionals reading holds at 0.35 and
> 0.60 and breaks at 0.90, because copyability is defined by what is *visible*
> and so the bucket's composition is a function of the rate. `acc | not copyable`
> falls to 0.0013, so the "nothing is being reconstructed" half is stronger than
> ever. The `copy_lift` column of these same runs falls monotonically and is
> negative for six of six pointer models by 0.60.
> **(b) The rung-4 bound below is the wrong way round** —
> `notes/findings/2026-08-15-rung-fours-bound-points-the-other-way.md`.
> Determinism gives `exact_match >= graph exactness`, not `<=`. The 0.0380 is a
> **lower** bound and the interval is [0.038, 0.15]. The numbers in the tables
> below are reproduced to the digit by an independent refit and are not in
> dispute; the inequality around them is.

**All 179 lessons, 716 evaluation episodes, `runs/infill-node-r015` and
`runs/infill-node-r035`, twelve pre-registered models plus floors refitted at
each rate.** The 0.60 and 0.90 arms were still running when this was written and
are marked as such; nothing here is averaged over rates.

## The two pre-registered expectations, and what happened

**R1 — "pointer models degrade fastest".** *Refuted, in the opposite
direction.* Mean `label_lift` over the pre-registered arms:

| arm | 0.15 | 0.35 | retained |
|---|---:|---:|---:|
| six with a pointer | 0.201 | 0.172 | **86%** |
| six without | 0.116 | 0.075 | **65%** |

The decision note called the opposite outcome "the most interesting result
available here", and this is it: pointer models degrade **slowest**. But the
reason is not that they are reconstructing — the copyable split below says they
are not — it is that the pre-registered axis is the wrong one. The no-pointer arm
contains both `omegaclaw_rank-001` (0.248 → 0.206, no pointer head, retains like
a pointer) and `grammar-001` (0.051 → 0.009). Split the twelve by renaming drop
instead, `label_lift` at 0.15 → 0.35:

| renaming drop ≤ 0.031 | | | | drop ≥ 0.088 | | |
|---|---:|---:|---|---|---:|---:|
| `evidence-001` | 0.089 → 0.091 | 102% | | `brill-001` | 0.172 → 0.108 | 63% |
| `vsa_perm-002` | 0.213 → 0.198 | 93% | | `grammar-001` | 0.051 → 0.009 | 18% |
| `corefer-001` | 0.250 → 0.222 | 89% | | `ngram-001` | 0.031 → −0.014 | *below floor* |
| `ptrgen-001` | 0.225 → 0.196 | 87% | | `ctw-001` | −0.040 → −0.056 | *below floor* |
| `omegaclaw_ctx-001` | 0.234 → 0.198 | 85% | | | | |
| `omegaclaw_rank-001` | 0.248 → 0.206 | 83% | | | | |
| `routes-001` | 0.210 → 0.164 | 78% | | | | |
| `ruleinduce-001` | 0.217 → 0.162 | 75% | | | | |

Every equivariant row retains 75% or more and one gains; two of the four
vocabulary rows fall through the floor. The axis is renaming-invariance, not
`source_votes` — the same correction the copyable split forces, arriving
independently.

**R2 — "the curve falls off a cliff at 0.35".** *Refuted.* The registered
threshold was: a cliff means the mean pointer `label_lift` at 0.35 is below half
its 0.15 value. It is 0.172 against 0.201 — 86% retained, not 50%. The 0.35→0.60
and 0.60→0.90 steps have not landed, so the registered *shape* condition is
still open; the cliff-at-0.35 half is closed.

## The curve, with its floors

`corefer-001`, the repo's best label model:

| mask rate | copy ceiling | `label_acc` | `label_floor` | `label_lift` | `label_bits` | scored fills |
|---:|---:|---:|---:|---:|---:|---:|
| **0.15** | 0.722 | 0.357 | 0.143 | 0.250 | 6.955 | 5,233 |
| **0.35** | 0.680 | 0.332 | 0.142 | 0.222 | 7.399 | 12,264 |
| **0.60** | 0.583 | 0.285 | 0.136 | 0.173 | 7.925 | 21,172 |
| **0.90** | 0.302 | 0.181 | 0.126 | 0.063 | 9.516 | 31,671 |

`label_lift` is the normalised form, `(acc − floor) / (1 − floor)`, which is why
it is not the difference of the two preceding columns.

And the arm, both rates complete, `label_acc` / `label_lift`:

| model | 0.15 | 0.35 |
|---|---|---|
| `corefer-001` | 0.357 / 0.250 | 0.332 / 0.222 |
| `omegaclaw_rank-001` | 0.356 / 0.248 | 0.319 / 0.206 |
| `omegaclaw_ctx-001` | 0.344 / 0.234 | 0.312 / 0.198 |
| `ptrgen-001` | 0.336 / 0.225 | 0.311 / 0.196 |
| `ruleinduce-001` | 0.329 / 0.217 | 0.282 / 0.162 |
| `vsa_perm-002` | 0.326 / 0.213 | 0.312 / 0.198 |
| `routes-001` | 0.323 / 0.210 | 0.283 / 0.164 |
| `brill-001` | 0.290 / 0.172 | 0.235 / 0.108 |
| `evidence-001` | 0.219 / 0.089 | 0.221 / 0.091 |
| `grammar-001` | 0.187 / 0.051 | 0.150 / 0.009 |
| `ngram-001` | 0.170 / 0.031 | 0.131 / −0.014 |
| `ctw-001` | 0.109 / −0.040 | 0.095 / −0.056 |
| **floor** | *0.143* | *0.142* |

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

| | 0.15 | 0.35 | **0.60** |
|---|---:|---:|---:|
| copyable share | 0.722 | 0.680 | **0.583** |
| `corefer-001` acc \| copyable | 0.494 | 0.488 | **0.486** |
| `corefer-001` acc \| not copyable | 0.003 | 0.003 | **0.004** |
| `corefer-001` acc (published) | 0.357 | 0.332 | **0.285** |
| predicted from the share alone | — | 0.337 | **0.289** |
| `ptrgen-001` acc \| copyable | 0.462 | 0.450 | *running* |
| `ptrgen-001` acc \| not copyable | 0.010 | 0.015 | *running* |
| floor, copyable / not | 0.158 / 0.106 | 0.159 / 0.106 | **0.158 / 0.104** |

Three points, and the ceiling has now fallen by 0.139 while `acc | copyable`
moved by **0.008** and `acc | not copyable` by 0.001. Both split floors are
within 0.002 of where they started. Carrying `acc | copyable` forward from 0.15
predicts 0.289 at rate 0.60 against an observed **0.285** — an error of 0.004,
smaller than the noise band this repo quotes for bits.

The within-type gaps survive at 0.60 as well: `pred` 0.832 against 0.001, `ident`
0.176 against 0.000, `field` 0.415 against 0.020. Non-copyable accuracy is 0.000
in four of seven types with the mask at 60%.

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

**Both conditional accuracies are flat and both floors are flat, over three
rates.** The entire 0.357 → 0.332 → 0.285 fall is the copyable share dropping
0.722 → 0.680 → 0.583.

So the mask rate is not a difficulty knob for these models in the way the ladder
assumed. It is a **supply** knob: it controls how often the answer is still
visible somewhere else, and the models convert that supply at a fixed rate.
Whether that stays true at 0.60 and 0.90 — where the ceiling must eventually
collapse — is the part of the curve still running, and it is the interesting
part, because there the supply runs out and the models have nowhere to go but the
0.003 column.

## Rung 4's bound, at both rates

~~The render is a deterministic function of the term, so `exact_match <=` graph
exact-match~~ — **the inequality is backwards; determinism gives
`exact_match >=` graph exact-match, and the numbers below are lower bounds.**
See `notes/findings/2026-08-15-rung-fours-bound-points-the-other-way.md`.
(`scripts/graph_exact.py`, run's own draw, `label_acc` bit-identical to the
published one):

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

## Rung 2, and it is the knob that moves the ability

`nodesub` hides **whole subtrees** drawn to the same node budget, so the amount
hidden is matched and only the *shape* of the hole varies. `runs/infill-sub-r015`,
first row, against `runs/infill-node-r015`:

| `corefer-001` at budget 0.15 | scattered | **subtree** |
|---|---:|---:|
| `label_acc` | 0.357 | 0.275 |
| `label_floor` | 0.143 | 0.126 |
| `label_lift` | 0.250 | **0.170** |
| `type_lift` | 0.612 | 0.417 |
| copy ceiling | 0.722 | 0.698 |
| **acc \| copyable** | 0.494 | **0.383** |
| acc \| not copyable | 0.003 | 0.024 |
| floor, copyable / not | 0.158 / 0.106 | 0.126 / 0.125 |

**R3 confirmed, and by the mechanism it was registered for.** The supply is
almost unchanged — the copy ceiling falls only 0.722 → 0.698 — and yet
`acc | copyable` falls by **0.111**. Raising the mask rate from 0.15 to 0.35 cost
0.006 of the same quantity while removing more supply than this does. So the two
knobs are not two settings of one difficulty dial:

* **mask rate** removes the *opportunity* to copy and leaves the ability intact;
* **contiguity** removes the *ability* at unchanged opportunity.

The pre-registration said scattered masking "leaves siblings visible and is a
fundamentally easier problem than generating a constituent", and this is what
that looks like when measured: the coreferent is still visible, and the local
context that would say *which* visible node it is has been hidden along with the
rest of the subtree.

**The whole arm, and nine of nine are worse.** `label_lift`, scattered →
subtree, floors refitted per regime (0.143 → 0.126). R3 would have been refuted
by any row at or above its scattered value:

| model | scattered | subtree |
|---|---:|---:|
| `corefer-001` | 0.250 | 0.170 |
| `omegaclaw_rank-001` | 0.248 | 0.183 |
| `ptrgen-001` | 0.225 | 0.147 |
| `vsa_perm-002` | 0.213 | 0.143 |
| `routes-001` | 0.210 | 0.107 |
| `evidence-001` | 0.089 | 0.067 |
| `grammar-001` | 0.051 | **−0.016** |
| `ngram-001` | 0.031 | **−0.041** |
| `gparse-none` (abstains) | — | −0.096 |

The two counting models fall *below* the floor. Their copyable split stays flat
under contiguity as well (`grammar-001` −0.021, `ngram-001` 0.000), so their
fall is not a copyability effect: a hidden parent and hidden siblings remove the
context their rules key on, which is the same thing that costs the copying
models their coreferent. One mechanism, two symptoms.

Four models measured both ways, `acc | copyable` at budget 0.15:

| model | scattered | subtree | Δ |
|---|---:|---:|---:|
| `corefer-001` | 0.494 | 0.383 | **−0.111** |
| `ptrgen-001` | 0.462 | 0.349 | −0.113 |
| `routes-001` | 0.448 | 0.315 | −0.133 |
| `evidence-001` | 0.303 | 0.258 | −0.045 |

**The floor says the same thing from the other side.** Under scattered masking
the structure-only lookup is itself 0.052 better on copyable fills than on the
rest; under subtree masking that difference collapses to **0.002** (0.126 against
0.125). Contiguity removes the copyability signal from a table that cannot read
a symbol, which is as clean a statement as this repo can make that the effect is
about local context and not about the models.

## What would refute this

- ~~`acc|copyable` falling materially at 0.60~~ — **checked, it did not**: 0.494
  → 0.488 → 0.486 while the ceiling fell 0.722 → 0.583. ~~The condition still
  stands for 0.90, where the ceiling should finally collapse.~~ **Resolved at
  0.90, and the condition was the wrong one**: `acc | copyable` did not fall, it
  **rose** to 0.5971, and so did the structure-only floor's copyable column
  (0.158 → 0.183), which is a predictor that cannot improve. The bucket changed,
  not the ability. Held at constant evidence concentration the model at 0.90 is
  *worse*. See
  `notes/findings/2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model.md`.
- The copy ceiling *not* collapsing at 0.90. `target_source` accepts any visible
  same-label node, and with 10% of nodes visible a repeated label often still has
  one, so the collapse is not as automatic as it sounds. If the ceiling holds up,
  the 0.90 arm is a much weaker test of generation than the ladder assumed.
  **Checked: it collapses to 0.302, and the 0.90 arm is a weaker test anyway**,
  for the different reason above.

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
