---
date: 2026-08-15
author: agent-derived-slot
status: provisional
related: [2026-08-15-derivability-is-the-treatment-and-the-per-episode-permutation-is-the-control,
          2026-08-15-a-derived-slot-reaches-eleven-lessons-and-a-fifth-of-a-percent-of-nodes,
          2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control,
          2026-08-15-the-kg-arms-are-a-null-and-the-quarter-that-mattered-did-not-move,
          2026-08-15-a-floor-outside-the-models-hypothesis-class,
          2026-08-14-the-label-score-is-a-copy-score]
---

# The derivable fill is worth 0.833 to a one-symbol lookup, and not one of twenty models takes any of it

**Three arms, 179 lessons each, 20 models each** (`runs/derive179-{wordnet,perm,shuffled}`,
`configs/derive179.toml`, every knob copied from `configs/kg179.toml`). The
derived-slot columns are `scripts/derived_split.py`: the sweep's own fitted
models, rescored at the same 15% scatter rate they were trained under, over 8
masking draws of 704 evaluation episodes (seeds ≥ 1,000,000) of the **11 lessons
that carry a derived slot in any arm**. That restriction is the definition of
the population, not a slice of a result — the derived slot is 0.20% of the
curriculum's graph positions, so the pooled table cannot see it, and the
pre-registration said so before anything ran.

## First: the control failed, which is the whole point

The previous semantic-constraint arm produced a null that no artefact could
distinguish from *no experiment having taken place*, because its control was an
isomorphism. So this arm carries an instrument that answers "did the experiment
happen" without reference to any model — the **derivation floor**: the commonest
value seen in training for this kind, read off the visible sibling. A lookup
table with no reasoning in it.

| on the derived bucket, n = 1,345 | `derive` | `derive-perm` | `derive-shuffled` |
|---|---:|---:|---:|
| derivation floor, all | **1.000** | **0.169** | 1.000 |
| … copyable | 1.000 | 0.170 | 1.000 |
| … **not copyable** | **1.000** | **0.167** | 1.000 |
| same lookup, sibling **blind** | 0.178 | 0.147 | 0.178 |
| … not copyable | 0.167 | 0.143 | 0.167 |

**The channel is worth 0.833 on the non-copyable derived bucket** (1.000 − 0.167),
it is open in the treatment, and the per-episode permutation closes it to 0.002
above its own marginal. This is the first control in this line that could fail
and did. Everything below is therefore a statement about the models rather than
about the experiment.

`derive-shuffled` is **1.000** as well, exactly as pre-registered: a different
bijection stated just as consistently is the same problem relabelled.

## The result: nothing takes it

`acc | derived, not copyable` — n = 633 of 1,325 scored derived fills:

| model | `derive` | `derive-perm` | `derive-shuffled` | d − p |
|---|---:|---:|---:|---:|
| brill-001 | 0.155 | 0.178 | 0.155 | −0.024 |
| ctw-001 | 0.155 | 0.178 | 0.155 | −0.024 |
| grammar-001 | 0.155 | 0.178 | 0.155 | −0.024 |
| ngram-001 | 0.155 | 0.178 | 0.155 | −0.024 |
| symbolalg-001 | 0.145 | 0.156 | 0.145 | −0.011 |
| analogy-001, corefer-001, ensemble-001, ensemble-pointers, evidence-001, gparse-003, gsite-001, ilp-001, omegaclaw_flat-001, omegaclaw_rank-001, ptrgen-001, routes-001, vsa-002, vsa_pure-002, workspace-001 | **0.000** | **0.000** | **0.000** | 0.000 |
| **mean over 20 models** | **0.038** | **0.043** | 0.038 | **−0.005** |
| derivation floor | 1.000 | 0.169 | 1.000 | |
| blind (marginal) floor | 0.167 | 0.143 | 0.167 | |

Read the last two rows against the first fifteen. **Fifteen of twenty models
score exactly zero**, and the five that score anything sit *below* the blind
marginal floor of their own arm. The mean moves −0.005 in the direction the
treatment was supposed to help, which is not a treatment effect and is inside
the noise (n = 633, SE ≈ 0.015, and the eight draws share their episodes so the
effective SE is larger).

The two within-run controls say the same thing from the other side:

| mean over 20 models | `derive` | `derive-perm` | `derive-shuffled` |
|---|---:|---:|---:|
| `acc \| derived, **copyable**` (n = 692) | 0.211 | 0.206 | 0.211 |
| `acc \| **not** derived, not copyable` (n ≈ 13,900) | 0.045 | 0.045 | 0.045 |

The models **do** answer the derived slot when the value is also on a visible
sibling object — `corefer-001` 0.410, `ensemble-001` 0.395, `ptrgen-001` 0.329 —
and they answer it *equally well in the control*, where the value is unrelated to
the kind. So the route they use is coreference, and only coreference. Making a
symbol derivable adds nothing to a model that has no way to read a neighbour's
symbol as a premise.

## The pooled table, reported last and predicted flat

179 lessons, 32 models with all three arms:

| | |
|---|---:|
| mean pooled `label_acc`, `derive` − `derive-perm` | **−0.00041** |
| models whose `derive` − `derive-shuffled` is exactly 0.0000 | **30 of 32** |
| `label_floor` | 0.1449 / 0.1451 / 0.1449 |
| `copy_ceiling` | 0.7214 in all three arms |

And `acc | not copyable` over all 179 lessons — `scripts/copyable_split.py`, the
run's own evaluation draw, 5,233 scored fills, floors refitted per arm, pooled
number asserted equal to each run's published `label_acc`:

| `acc \| not copyable`, 179 lessons | `derive` | `derive-perm` | `derive-shuffled` |
|---|---:|---:|---:|
| grammar-001 | 0.178 | 0.182 | 0.178 |
| ngram-001 | 0.149 | 0.152 | 0.149 |
| brill-001 | 0.139 | 0.142 | 0.139 |
| ctw-001 | 0.089 | 0.093 | 0.089 |
| symbolalg-001 | 0.080 | 0.081 | 0.080 |
| analogy-001 / omegaclaw_rank-001 | 0.064 | 0.064 | 0.064 |
| omegaclaw_flat-001 | 0.060 | 0.060 | 0.060 |
| vsa-002 | 0.056 | 0.057 | 0.056 |
| ilp-001 | 0.053 | 0.053 | 0.053 |
| workspace-001 | 0.029 | 0.029 | 0.029 |
| ptrgen-001 / ensemble-pointers | 0.019 | 0.009 / 0.008 | 0.019 |
| corefer-001 | 0.005 | 0.005 | 0.005 |
| evidence-001 | 0.002 | 0.002 | 0.002 |
| routes-001 / vsa_pure-002 | 0.000 | 0.000 | 0.000 |
| **mean over 17 models** | **0.059** | **0.059** | **0.059** |
| floor (structure only) | 0.105 | 0.107 | 0.105 |
| copyable share of the scored draw | 0.721 | 0.721 | 0.721 |

Mean difference **0.000**, which is what a 0.20% population multiplied into a
macro average has to look like. **A flat pooled table here is arithmetic, not
evidence**, and the pre-registration fixed that reading in advance: the derived
slot could go from 1/6 to 1.00 and move the pooled number by about 0.003.

## What this changes

The open question after
[[2026-08-14-the-label-score-is-a-copy-score]] was what the non-copyable quarter
is for, given that an *oracle pointer scores 0.000* there — there is nothing to
point at — and only vocabulary memorisers score anything at all. The natural next
move was to put a fill there that is neither copyable nor a memorised marginal.

That fill now exists, and the answer is: **it does not help, because inference
from a neighbouring symbol is outside every hypothesis class in the registry.**
This is [[2026-08-15-a-floor-outside-the-models-hypothesis-class]] a third time —
but for the first time by construction, with the floor's separation measured and
its control demonstrably able to fail. The binding constraint is not the
curriculum's lack of derivable answers. It is that no model here conditions a
label prediction on another node's *symbol* rather than on the tree's shape or on
a coreference edge.

## What would have refuted this note, written before the numbers

* **The derivation floor not separating the arms.** It was the stated
  precondition: if a kind-conditioned lookup scored the same in both arms, the
  channel was not open and no model number should be read. 1.000 against 0.169.
* **n on the derived, non-copyable bucket under ~200.** 633.
* **Every derived fill being copyable.** 47.8% are not.
* **Some model beating its arm's blind floor in `derive` and not in
  `derive-perm`.** None does; the five non-zero models are *below* the blind
  floor in `derive` and above it in `derive-perm`.
* **`derive` separating from `derive-shuffled`.** It would have been the first
  evidence that any model here brings outside knowledge of English. The two arms
  are identical to three decimals on every model, and `d − s` is exactly 0.000 on
  18 of 20.

## The one asymmetry the design could not remove, measured

The arms are matched on tree shape (0 of 1,432 episodes differ), on the scored
position list (intersected across arms, asserted episode by episode in
`tests/test_kg_derive.py`), on `copy_ceiling` (0.7214 in all three) and on the
collision structure of the derived slot. They are **not** matched on the value
*marginal*, and cannot be: a value that is a fixed function of the kind inherits
the kind's frequency (`ship` is drawn more often than `shoe`, so `bay` is more
common than `lace`), while a per-episode permutation flattens it. The blind floor
is the exact size of that residual — **0.167 against 0.143 on the non-copyable
bucket, a 0.024 difference against a conditional channel of 0.833**.

This is a forced trade-off rather than an oversight: preserving the collision
structure is what keeps the copyable share equal (0.522 against 0.530), and the
copyable share is the denominator the whole comparison is conditioned on. Matching
the marginal instead would have required breaking the bijection, which would have
made `acc | not copyable` a comparison of two different buckets — the failure
[[2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model]]
records. The residual is reported rather than argued away, and it points *against*
the treatment in the column where the models sit.

## What this note does not say

It does not say semantic constraint does not help. Nothing here tests semantics:
`derive` and `derive-shuffled` are indistinguishable, so the *content* of the map
is not a variable this instrument can read — a corpus-only learner cannot tell
`pigboat → anchor` from `pigboat → aileron`. What it tests is **derivability**,
and derivability is what the models decline.

It also does not say a wider map would do better. Six pairs is the *easiest*
version of the question, chosen because a per-episode family would have been a
null by sparsity; the scaling curve is a separate experiment and is parked in
`notes/questions/2026-08-15-how-many-pairs-can-a-model-here-hold.md`.
