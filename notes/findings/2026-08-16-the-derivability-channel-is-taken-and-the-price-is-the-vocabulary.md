---
date: 2026-08-16
author: lead
status: provisional
related: [2026-08-16-the-hypothesis-frontier-and-what-a-learned-map-can-express,
          2026-08-15-the-derivable-fill-is-worth-0833-to-a-lookup-and-nothing-takes-it,
          2026-08-15-derivability-is-the-treatment-and-the-per-episode-permutation-is-the-control,
          2026-08-15-a-floor-outside-the-models-hypothesis-class,
          2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name,
          2026-08-16-a-private-name-on-a-torch-module-is-not-private]
---

# `frontier-001` takes the 0.833 channel, the control closes it, and the induced rule is the planted one

**Status is `provisional` and stays there until someone who did not write the
model traces this.** The control is not mine — `derive:wordnet-perm` was
designed by another agent for another model, before `frontier-001` existed —
which is the strongest thing about the result and is why it is worth
challenging rather than assuming.

Full 179-lesson sweep, `configs/derive179.toml`, three arms, measured by
`scripts/derived_split.py` on 1,325 derived fills over 704 evaluation episodes
(seeds from 1,000,000) and 8 masking draws. Not a slice: the derived slot exists
in 11 of 179 lessons and this is the whole of it.

## The number

`acc | derived, not copyable` — the only population on which the arms can differ:

| | treatment `derive:wordnet` | control `-perm` | `-shuffled` |
|---|---:|---:|---:|
| **`frontier-001`** | **0.532** | **0.072** | **0.532** |
| `brill` / `ctw` / `grammar` / `ngram` | 0.155 | 0.178 | 0.155 |
| `symbolalg-001` | 0.145 | 0.156 | 0.145 |
| the other fifteen | 0.000 | 0.000 | 0.000 |
| derivation floor (a lookup) | 1.000 | 0.167 | 1.000 |
| blind marginal | 0.167 | 0.143 | 0.167 |

`treatment − control` is **+0.460**. Every other model in the table is at or
below **zero** on that difference: the four that score 0.155 score *more* in the
control, and fifteen score nothing in either.

**H1 was ≥ 0.80 and it did not land.** The pre-registration said the treatment
should reach 0.80 and would be refuted below 0.50. 0.532 clears the refutation
bar and misses the prediction by a wide margin, and the prediction was simply
too optimistic — recorded here rather than quietly restated, because the whole
point of writing it down first is that it can be wrong.

**H2, the load-bearing control, closed harder than predicted.** Predicted ≤ 0.20
and void above 0.35; measured **0.072**, which is below the control arm's own
blind marginal (0.143) *and* below its derivation floor (0.167). The model is
not abstaining there — it is confidently wrong, which is a different and worse
thing, and it is in the mechanism below.

**H4 held and was arithmetic.** Pooled `label_acc` is 0.408 / 0.405 / 0.408
across the three arms. The derived slot is 0.20% of graph positions, so this was
predicted before the run and is not evidence about anything.

## The mechanism, traced to the rule rather than inferred from the score

The point of the map form was to make this checkable inside the fitted model.
The rule that answers the bucket is one hypothesis, and it can be read:

    [slot=1, nsib=4] -> map:sib@2     p=0.659  n=2300  |m|=399

Its entries at the six planted kinds, in each arm:

| arm | the six entries | correct | the rule itself |
|---|---|---:|---|
| `derive:wordnet` | shoe→lace, body→abdomen, ship→bay, garment→arm, building→annex, auto→buffer | **6/6** | survives |
| `derive:wordnet-perm` | — | — | **does not survive verification; the rule is not in the model** |
| `derive:wordnet-shuffled` | shoe→calcaneus, body→buffet, ship→air, garment→bight, building→aileron, auto→bedframe | **0/6** vs WordNet | survives, same guard, same `n`, same `p`, same `|m|` |

**All six planted pairs are recovered verbatim.** Tracing the 111 derived
non-copyable fills of a sub-draw: 55% are answered by this rule and **61 of 61
of those are correct**; the remaining 45% match no kept rule and abstain. So the
model is not half-right — it is exact where it fires and declines the rest, and
0.532 is a recall number, not a precision one.

**The control's mechanism is not abstention, and my first statement of it was
wrong.** I wrote in the model's docstring that under the permutation the map
would fail verification "and the model abstains". Half true. The *derived-slot*
rule genuinely fails verification and is absent from the control's model —
that half is confirmed above. But the control keeps 355 other map rules, nearly
the same set as the treatment's 356, and on the derived bucket a *different* map
fires and is wrong at chance. Hence 0.072 rather than the ~0.17 an abstaining
model would score. Corrected in the docstring.

**The `-shuffled` arm is the nicest row here.** It was predicted to tie and did,
at 0.532 to three decimals — but now the tie is visible one level down: the same
guard, the same support, the same table size, and a completely different table
whose six kind entries agree with real WordNet **zero** times out of six. The
earlier note could only assert that this instrument reads *derivability* and
never *meaning*. This shows it: the model learns whatever correspondence the
corpus states and has no opinion about whether it is true.

## The price, and H5 was refuted

Renaming, from the sweep, all three arms: **0.408 → 0.034, a drop of −0.374.**
That is the second-largest renaming loss ever measured here, behind
`ensemble-001`'s −0.429 and ahead of `grammar`'s −0.159.

Some of this was predicted and is not a defect. Naming a symbol that no visible
node carries requires storing an association between symbol identities across
episodes, so **derivation and renaming-invariance are incompatible** and the
fifteen models at 0.000 are a theorem rather than a failure — the same shape as
[[2026-08-15-a-floor-outside-the-models-hypothesis-class]].

But H5 said the drop would be **large on the derived bucket and small
elsewhere**, and that is refuted by the pooled number: −0.374 pooled cannot come
from a bucket that is 0.20% of positions. The mechanism is in the rule census:
**356 of 444 label rules are maps.** The map form did not stay where derivation
was needed. Offered a symbol-keyed table and a structural copy, cross-fitted
precision preferred the table nearly everywhere, because on this curriculum it
verifies better. That also accounts for `acc | rest, not copyable` = **0.238**,
the highest in the table and above `grammar`'s 0.178 — and it should be read as
memorisation, not as reasoning.

## The control in the model's own hypothesis class, and it settles the trade

`frontier-nomap` is the identical search with the `map` form removed and nothing
else changed — same guards, same lattice, same cross-fit, same residual rounds,
same MDL ordering, same calibrator, same gate. Comparing against `ilp` or
`corefer` instead would confound the resolver set with the whole rest of the
design.

| | `frontier-001` | `frontier-nomap` | what the map form is worth |
|---|---:|---:|---:|
| `acc \| derived, not copyable`, treatment | 0.5315 | **0.0000** | **+0.53** |
| the same, control `-perm` | 0.0722 | 0.0000 | — |
| pooled `label_acc`, base curriculum | 0.4042 | 0.2954 | **+0.109** |
| `label_bits`, base curriculum | 7.433 | 8.541 | 1.11 bits better |
| **renaming drop** | **−0.372** | **−0.066** | **−0.306 of equivariance** |
| `type_acc` | 0.863335 | 0.863335 | 0.000 — as it must be |

Predicted before the run and confirmed: **0.000 on the derived non-copyable
bucket**, which is where fifteen registered models already sit, because a copy
cannot produce a symbol no visible node carries. The type head is bit-identical
to six decimals, which is the check that the `forms` knob did not leak into a
head that never had the form.

**This replaces the inference in the previous section with a measurement.** H5
guessed the renaming drop was concentrated on the derived bucket; it is not, and
now the size is known rather than argued: the map form costs **0.306 of the
0.372**, and the derived slot is 0.20% of positions, so essentially all of that
cost is the map firing where no derivation was required. It buys 0.109 of pooled
accuracy and 1.11 bits for it.

Both readings of that trade are defensible and the repo should hold both:
`frontier-001` is the best label model here and the second least equivariant;
`frontier-nomap` at 0.2954 with a −0.066 drop is an ordinary, honest,
nearly-equivariant model that beats `brill` and cannot touch the channel.

One thing the control does that is **not** explained: `frontier-nomap` scores
0.0000 on the *copyable* derived half too, where copying is available and every
pointer scores 0.14–0.41. So it is not abstaining onto the back-off there (that
would be 0.155, as `brill` and three others are) — some copy or const rule fires
and is wrong. Recorded as an open defect rather than explained away.

## The failure a refuter should look at first

On the **copyable** half of the derived bucket, `frontier-001` goes 0.496 →
0.078 between treatment and control. Every pointer holds its score there —
`corefer` 0.410 → 0.399, `ptrgen` 0.329 → 0.305 — because a copyable fill is
answerable in *both* arms by copying, which is exactly why the pre-registration
said that half could not separate the arms. It separates for this model by
0.418.

The reading: **the frontier replaces an available copy with a derivation
whenever the derivation verifies better in training**, and in the control that
trade is strictly worse than copying. It is rational under the training
distribution and brittle under the one thing designed to break it. Whether a
resolver-preference tie-break toward `copy` fixes it without costing the 0.532
is the obvious next experiment and has not been run.

## What would make this true and uninteresting

1. **The floor already scores 1.000.** Matching part of a lookup table is not a
   discovery on its own. What is new is that a model *in the sweep, under the
   same contract, fitted the same way on every curriculum, never told the arm
   exists* recovers it — and that the same fitting procedure produces a model
   without the rule when the correspondence is removed.
2. **Six pairs is a small table.** If this collapses at twelve, the result is
   about table size and not induction.
   `notes/questions/2026-08-15-how-many-pairs-can-a-model-here-hold.md` is the
   curve and is now measurable.
3. **The derivation is six entries of a 399-entry table**, not an isolated
   six-entry hypothesis. MDL ranks the coarse rule first because nothing more
   specific was proposed that beat it. So the model did not *separate* the
   derivation from the rest of its memorisation, it merely contains it.
