---
date: 2026-08-14
author: agent-generation
status: provisional
related: [2026-08-14-the-curriculums-own-question-asked-on-the-graph,
          2026-08-14-the-infilling-ladder-preregistration,
          2026-08-13-a-ranking-is-a-property-of-a-metric,
          2026-08-13-slices-have-inverted-results-eight-times,
          the-readout-survives-both-attacks-and-its-comparison-row-does-not]
---

# Every renaming-invariant model is below the floor on the quarter of fills it cannot copy

**All 179 lessons, 716 evaluation episodes, 5,233 scored fills, `runs/infill-node-r015`,
`mask_rate=0.15` — the published masked-node setting, on the run's own masking
draw.** Computed by `scripts/copyable_split.py`, which reloads the sweep's fitted
model and reproduces `evaluate_model`'s draw exactly, so **every `acc (all)`
below is bit-identical to the row's published `label_acc`** and the split is a
decomposition of the published number rather than a second measurement of it.

`label_acc` has been this repo's central number from the beginning. It is a
mixture of two questions in a 72:28 ratio, and nothing has ever reported them
apart: does some **visible** node of the same graph already carry the answer's
label (`target_source`, the same bit the copy ceiling is built from)?

| model | acc \| copyable | acc \| **not** | acc (all) | gap | renaming drop |
|---|---:|---:|---:|---:|---:|
| `corefer-001` | 0.494 | **0.003** | 0.357 | **0.490** | 0.003 |
| `omegaclaw_rank-001` | 0.469 | 0.063 | 0.356 | 0.406 | 0.017 |
| `ptrgen-001` | 0.462 | 0.010 | 0.336 | 0.451 | 0.005 |
| `omegaclaw_ctx-001` | 0.457 | 0.051 | 0.344 | 0.406 | 0.018 |
| `routes-001` | 0.448 | **0.000** | 0.323 | 0.448 | −0.000 |
| `vsa_perm-002` | 0.435 | 0.043 | 0.326 | 0.392 | 0.010 |
| `ruleinduce-001` | 0.425 | 0.081 | 0.329 | 0.344 | 0.027 |
| `brill-001` | 0.350 | 0.137 | 0.290 | 0.213 | 0.130 |
| `evidence-001` | 0.303 | 0.001 | 0.219 | 0.302 | 0.003 |
| `grammar-001` | 0.191 | **0.178** | 0.187 | **0.012** | 0.159 |
| `ngram-001` | 0.175 | 0.154 | 0.170 | 0.021 | 0.143 |
| `ctw-001` | 0.116 | 0.090 | 0.109 | 0.026 | 0.088 |
| **floor** (structure only) | *0.158* | *0.106* | *0.143* | *0.052* | — |

The floor is the same `_ContextRule` ladder, the same masking draw and the same
fitting as `MaskedNode.floor`, bucketed instead of pooled —
`MaskedNode.split_floor`, whose pooled value is asserted equal to the run's own
`label_floor` (0.14321518927482088) so that it cannot quietly have become a
second floor.

## The three readings, in order of how much they cost

**1. `corefer-001`'s masked-node competence is coreference and nothing else.**
Where the answer is in plain sight somewhere in the same graph it gets half of
them; where it is not it gets three in a thousand — 0.103 *below* a lookup table
that cannot read a single symbol. That 0.003 is the same nothing it scores on the
curriculum's own answer (0.001, `runs/infill-ans`), which is 0% copyable by
construction. The two measurements are one fact seen twice.

**2. Every renaming-invariant model is below the floor on the non-copyable
quarter, and every vocabulary model is above it.** Sort the table by renaming
drop and the gap column sorts with it. The nine rows with drops ≤ 0.027 have gaps
of 0.302–0.490 and land at 0.000–0.081 against a 0.106 floor; the three rows with
drops ≥ 0.088 have gaps of 0.012–0.213 and land at 0.090–0.178. This is the
repo's own renaming table, seen from the other side: the models that read
structure read *coreference*, and where there is no coreferent to read they are
worse than a table.

**3. The published ranking inverts on the sub-population.** `corefer-001` is
first of twelve overall and **eleventh** on the non-copyable quarter;
`grammar-001` is eighth overall and **first**. `a-ranking-is-a-property-of-a-metric`
said a ranking belongs to its metric; this says it also belongs to its
sub-population, and the repo has only ever published the pooled one.

## The control that could have failed, and the axis I pre-registered wrongly

**`grammar-001` is flat: 0.191 against 0.178, a gap of 0.012.** A vocabulary
model names, and naming works about equally well whether or not a copy happens to
be visible. So the split is not "copyable fills are easier" — for the three
counting models the two halves are within 0.026 of each other, while the floor
itself only differs by 0.052. What separates the columns for everyone else is the
mechanism, not the difficulty.

**And the axis is not the pointer head.** The pre-registration split the twelve
models by whether they override `source_votes`, because the expectation was about
pointers. `omegaclaw_rank-001` and `omegaclaw_ctx-001` have **no pointer head at
all** and show gaps of 0.406 — indistinguishable from `corefer-001`'s 0.490 and
larger than `ruleinduce-001`'s 0.344, which does have one. The pre-registered
axis was wrong and the axis that works is renaming-invariance. Recorded rather
than quietly re-drawn.

## What this explains

- **The 0.423 readout gap.** `repair` masks scattered nodes, so 72% of its
  decisions are copyable, and reading `corefer-001` as a move scores 0.508.
  Reading it as text asks it to *spell*. Both numbers are what "this model
  copies" predicts.
- **Rung 3.** The curriculum's answer is the non-copyable case in its purest
  form, and every equivariant model lands on the abstention row there.
- **The 0.722 copy ceiling**, already published as "more than half the reachable
  signal is untouched". The sharper reading: essentially *all* the signal these
  models reach is inside the ceiling, and outside it they are below a lookup.

## The artefact explanation, tested and dead

The obvious objection: copyable fills might simply be an easier *kind* of node —
`ident` leaves, say — so the gap would be about difficulty and not mechanism.
Conditioning on the node type answers it. Same run, same draw, same 5,233 fills:

| node type | n | copyable share | `corefer-001` copyable / not | `grammar-001` copyable / not |
|---|---:|---:|---:|---:|
| `ident` | 2,023 | 0.712 | 0.228 / **0.000** | 0.181 / 0.122 |
| `pred` | 1,749 | 0.882 | 0.834 / **0.000** | 0.183 / 0.184 |
| `num` | 821 | 0.674 | 0.297 / **0.000** | 0.222 / 0.127 |
| `field` | 386 | 0.065 | 0.640 / 0.014 | 0.080 / 0.291 |
| `token` | 127 | 0.803 | 0.422 / **0.000** | 0.108 / 0.120 |
| `char` | 102 | 0.882 | 0.278 / **0.000** | 0.422 / 0.667 |

`corefer-001`'s gap is positive in **every** type, between +0.228 and +0.834, and
its non-copyable column is 0.000 in five of six. `grammar-001`'s gaps range from
−0.244 to +0.096 with no consistent sign. So the split is not a node type wearing
a copyability label — it is the mechanism, inside each type.

`field` is the sharpest case: only 6.5% of field-name fills are copyable, and
`corefer-001` gets 0.640 of those and 0.014 of the rest, while `grammar-001` —
which can simply learn that the field at this slot is usually called `query` —
gets 0.291 of the non-copyable ones, twenty times `corefer`'s.

## What would refute it
- **A renaming-invariant row with a small gap.** Twelve were tried; the smallest
  equivariant gap is `ruleinduce-001`'s 0.344.
- **A pre-registered prediction for the mask-rate curve, committed before those
  numbers existed** (the 0.35 arm was mid-flight): raising the mask rate lowers
  the copyable share mechanically, because `target_source` only accepts a
  *visible* same-label node. If this account is right, a pointer's `label_acc`
  should track `copyable_share(rate) × acc|copyable` with `acc|copyable` roughly
  flat. If `acc|copyable` itself collapses with the rate, the models are losing
  the ability to copy and not merely the opportunity, and that is a second effect
  this note does not predict.

## Provisional

Author-designed controls only. Three of them could have failed and did not: the
flat counting columns, the pooled-floor assertion, and the within-type split
(which was named as the refutation condition in the first version of this note
and then run). What is still missing is an *independent* attempt to break it —
the obvious next one being whether `acc | copyable` survives a renaming
permutation, i.e. whether even the copying is structural.
