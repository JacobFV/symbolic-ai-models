---
date: 2026-08-14
author: agent-refuter-copy
status: measured
related: [2026-08-14-the-atomspace-ir-round-trips-and-the-label-null-was-predicted,
          2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name,
          2026-08-13-the-harness-moves-more-than-the-models,
          2026-08-13-coverage-versus-accuracy-in-an-agent-column,
          2026-08-14-an-unmeasured-confound-has-an-unknown-sign]
---

# Refutation report: `metta_perm_pure-005`'s copy lead survives, and the filename is wrong

**The filename is the hypothesis I registered and it is the one that died.** I
kept it rather than renaming the file, because a refuter who quietly relabels his
prediction after seeing the answer is doing the thing this repo has a lessons
directory about.

I did not write the work under attack. The target is one number:
`metta_perm_pure-005` at **+0.1091 copy lift** (copy acc 0.3459) against
`corefer-001`'s **+0.0959** (0.3362), `runs/metta005`, all 179 lessons, copy
floor 0.2658, n = 5,785 — quoted in
`notes/findings/2026-08-14-the-atomspace-ir-round-trips-and-the-label-null-was-predicted.md`
as *"the first thing in this repo's history to lead the copy head"*.

## Pre-registration

Committed in `ca5a666`, **before any of my own numbers existed**.

| # | hypothesis | I predicted | outcome |
|---|---|---|---|
| 1 | the two rows answer the same question | same denominator, same items, by construction | **confirmed** |
| 2 | the pointer inherits `structural_fallback` | it does not | **confirmed** |
| 3 | coverage-versus-accuracy | both vote on nearly every node | **confirmed, and stronger than I expected** |
| 4 | **the lead is inside the noise** | the +0.0097 gap is not distinguishable from zero | **REFUTED on replication** |
| 5 | the ranking is not stable | the order flips on at least one alternative mask | **REFUTED — it flips on none of five** |
| 6 | the pointer is symbol-free | `metta` exactly invariant, `corefer` not | **confirmed** |
| 7 | the crosstalk mechanism | unconfirmed; the label loss will not grow with width | **partly confirmed, and confounded** |

## Verdict

**The result survives.** Two of my seven pre-registered hypotheses were attempts
to kill it and both failed, on evidence I would have accepted as fatal had it
gone the other way. What does *not* survive is the finding's supporting
arithmetic: the margin it quotes is measured against the wrong baseline, and one
sentence of it — "first, at +0.1091 against `corefer-001`'s +0.0959" — is, **on
the single published evaluation draw alone, not significant** (McNemar p = 0.057).
It becomes significant only on replication, which is a stronger claim honestly
arrived at rather than a weaker one.

---

## 1. The number is real: it reproduces bit-exactly in an independent worktree

Four rows refitted from scratch in my own worktree with `configs/full179.toml`
and compared against the published run directories. Every one identical to full
float precision, not to three decimals:

| row | published copy acc | my refit | published in |
|---|---|---|---|
| `metta_perm_pure-005` | 0.34589455488331894 | 0.34589455488331894 | `runs/metta005` |
| `corefer-001` | 0.3362143474503025 | 0.3362143474503025 | `runs/metta005` |
| `vsa_perm_pure-002` | 0.3097666378565255 | 0.3097666378565255 | `runs/metta005` |
| `vsa_perm_hks_wide_pure-004` | 0.3337942955920484 | 0.3337942955920484 | `runs/vsa_role` |

The copy floor recomputed from scratch on the same draw is **0.2658**, identical
to the published one. Nothing below is about a number that moved.

## 2. Both rows answer the same question — provable, not merely suggestive

`_pointer_counts` builds its scored set as `scored = (label_group != IGNORE) &
(target_types != IGNORE)`. Every term is a property of the **batch**; no model
output enters the denominator. `evaluate_model` resets the masking RNG to
`default_rng(12345)` before each model and iterates with `random.Random(0),
shuffle=False`. So the matching `n = 5,785` is a consequence rather than
evidence — but my per-item harness additionally asserts that the
`(batch, row, node)` key list is identical across all four models, and it is, on
every draw.

Exclusions are shared and symmetric: pads barred by `pad_mask`, self barred by an
identity mask, and `collate_graph` blanks both `tokens` and `types` at hidden
positions so nothing can read the answer. All three pointers restrict their own
votes to visible, labelled nodes.

## 3. `structural_fallback` cannot reach the pointer — by code and by measurement

The fallback enters `_forward_graph` only as `prior=` to `_mix`, which builds
`symbol_logits`. `_source_logits` never sees it. The measurement agrees: every
`_pure` / non-`_pure` pair in `runs/metta005` has a **bit-identical** copy
accuracy (`metta_perm-005` and `metta_perm_pure-005` are both
0.34589455488331894), so the memorising component contributes exactly zero here.

## 4. The back-off scores **zero**, so no row can be wearing it

This is the `a-score-can-be-the-back-off-wearing-the-models-name` check, and the
copy head passes it in the strongest available form.

| draw | coverage: `metta` | `corefer` | `hks_wide` | `vsa_perm` | flat pointer back-off |
|---|---:|---:|---:|---:|---:|
| mask 12345 | 1.000 | 1.000 | 1.000 | 1.000 | **0.0000** |
| mask 12346–12348 | 1.000 | 1.000 | 0.999–1.000 | 1.000 | **0.0000** |
| fresh episodes | 1.000 | 1.000 | 1.000 | 1.000 | **0.0000** |

Two things follow. Every pointer votes on essentially every scored node, so there
is no selection effect to exploit. And `_pointer_logits`'s back-off is *flat*
over legal targets, so an unvoted row breaks its tie at the lowest visible index
— which scores **0.0000**, not a respectable number. On this head, abstention is
punished rather than subsidised, which is the opposite of the label head's
contract and worth knowing on its own.

## 5. The lead against `corefer-001`: borderline once, robust five times

Paired per-item comparison on the identical scored set. McNemar is exact-paired;
the interval is a bootstrap resampled by **lesson** (179 clusters), which is the
conservative unit because episodes inside a lesson share a generator.

| evaluation draw | `metta` | `corefer` | diff | McNemar p | lesson 95% CI |
|---|---:|---:|---:|---:|---|
| **published** (mask 12345) | 0.3459 | 0.3362 | +0.0097 | **0.057** | **[−0.0048, +0.0242]** |
| mask 12346 | 0.3462 | 0.3297 | +0.0165 | 0.001 | [+0.0012, +0.0317] |
| mask 12347 | 0.3462 | 0.3346 | +0.0116 | 0.022 | [−0.0021, +0.0252] |
| mask 12348 | 0.3425 | 0.3168 | +0.0257 | 0.000 | [+0.0111, +0.0412] |
| **fresh 716 episodes** (seed0 1,000,100, floor 0.2730) | 0.3475 | 0.3302 | +0.0173 | 0.001 | [+0.0024, +0.0326] |

Read it in both directions, because both are true:

- **The published draw alone does not carry the claim.** 0.3459 versus 0.3362 is
  56 items in 5,785, p = 0.057, and both cluster intervals cover zero. A reader
  given only that row would be right to withhold assent.
- **The claim is nonetheless right.** `metta_perm_pure-005` leads on **five of
  five** independent evaluations, including 716 episodes it had never seen; the
  published draw is the *smallest* of the five margins, so the mask was not
  flattering the finding, it was understating it. My hypothesis 5 said the order
  would flip on at least one draw. It flips on none.

Note also which row is stable: `metta` sits at 0.3425–0.3475 across all five
draws while `corefer` swings 0.3168–0.3362. Most of the variance in the gap is
`corefer` moving, not `metta`.

## 6. The margin is quoted against the wrong baseline

This is the part of the finding that does not survive. It reports **"+0.060 →
+0.109, an improvement of +0.049"** against `vsa_perm_pure-002`. But
`RESEARCH_LOG.md` already names a better pointer in the same family —
`vsa_perm_hks`, "the second-best pointer in the repo" — and that row is not in
the finding's table. Same config, same floor 0.2658, same n = 5,785,
`runs/vsa_role`:

| row | copy acc | copy lift | what changed |
|---|---:|---:|---|
| `vsa_perm_pure-002` | 0.3098 | +0.0599 | four hand-picked role coordinates |
| `vsa_perm_hks_wide_pure-004` | 0.3338 | +0.0926 | graph-derived roles, **no atomspace** |
| `corefer-001` | 0.3362 | +0.0959 | naive Bayes over pair features, reads prose |
| `metta_perm_pure-005` | 0.3459 | **+0.1091** | atomspace query signatures |

So the +0.0492 of lift decomposes as **+0.0327 for "graph-derived roles at all"**
— already banked before this line started — **and +0.0165 for the atomspace
specifically**. Two thirds of the headline improvement is not attributable to the
IR under test.

The atomspace increment is real. `metta` beats `hks_wide` on all five draws with
every interval excluding zero:

| draw | diff | McNemar p | lesson 95% CI |
|---|---:|---:|---|
| mask 12345 | +0.0121 | 0.0066 | [+0.0008, +0.0229] |
| mask 12346 | +0.0195 | 0.0000 | [+0.0077, +0.0316] |
| mask 12347 | +0.0249 | 0.0000 | [+0.0136, +0.0360] |
| mask 12348 | +0.0198 | 0.0000 | [+0.0087, +0.0300] |
| fresh episodes | +0.0159 | 0.0002 | [+0.0058, +0.0263] |

**And second place is a coin flip.** `corefer` versus `hks_wide` is +0.0027
(p 0.66), +0.0031 (p 0.57), +0.0130 (p 0.008), −0.0059 (p 0.24), −0.0009
(p 0.81) — it changes sign across draws. So "first" is established and "second"
is not, and the finding's chosen comparator happens to be the one whose position
is undetermined.

## 7. The pointer is exactly symbol-free; `corefer`'s is not

Not in the finding, and it should be — this is the sharpest qualitative
difference between the two rows. Every symbol permuted, no refitting:

| row | plain | renamed | drop |
|---|---:|---:|---:|
| `metta_perm_pure-005` | 0.3459 | 0.3459 | **+0.0000** |
| `vsa_perm_hks_wide_pure-004` | 0.3338 | 0.3338 | **+0.0000** |
| `vsa_perm_pure-002` | 0.3098 | 0.3098 | **+0.0000** |
| `corefer-001` | 0.3362 | 0.3355 | +0.0007 |

(2,105 symbols on the published draw; +0.0015 for `corefer` on the fresh draw
with 2,061.) The VSA-family pointers are *bit-identical* under renaming because
`_node_scores` reads roles and addresses and never a codebook entry.
`corefer`'s `_pair_features` includes `view.mentions(j)`, a count of the
candidate's symbol **in the prompt** — so the two rows are not even reading the
same inputs. The row that leads is the one that reads strictly less.

## 8. Where the lead actually comes from, and it is not uniform

Copy accuracy by how many coreferent nodes the question has, published draw
(every one of the five draws shows the same pattern):

| same-label candidates | n | `metta` | `corefer` |
|---|---:|---:|---:|
| 1 | 695 | 0.1324 | 0.1396 |
| 2 | 580 | **0.2741** | **0.3310** |
| 3–4 | 1224 | 0.4959 | 0.4828 |
| 5+ | 1832 | 0.6163 | 0.5737 |

`corefer` wins the two-candidate bucket on **all five draws** and `metta` wins
the 3–4 and 5+ buckets on all five. The lead is bought where several sources
exist and given back where the choice is genuinely binary. That is a real
finding about the two pointers and it is invisible in the pooled number.

## 9. The crosstalk mechanism: now tested, partly confirmed, confounded

The finding offers, and labels unrun: *the label head unbinds a trace carrying
every node, so extra signatures raise crosstalk* — predicting the label loss
grows with graph width, with node arity, and with signatures per node.

First, the variable exists. Signatures per node range **7 to 183** (median ~12;
13,155 nodes over 240 views), so the schedule is far from constant and the test
is runnable. Label accuracy, `metta` minus `hks_wide`, by signature count:

| signatures | n | `metta` | `hks_wide` | gap |
|---|---:|---:|---:|---:|
| 7–9 | 1447 | 0.1016 | 0.0974 | +0.0041 |
| 10–12 | 1115 | 0.1112 | 0.1139 | −0.0027 |
| 13–17 | 1601 | 0.2542 | 0.3210 | −0.0668 |
| 18+ | 1070 | 0.6523 | 0.7542 | −0.1019 |

Monotone, and monotone again on mask 12346 (−0.0035, −0.0152, −0.0526, −0.1103).
**Directionally confirmed** against that comparator.

Three reasons not to call it established:

1. Against `vsa_perm_pure-002` the same table is **not** monotone — the gap peaks
   in the 13–17 bucket and narrows at 18+ on both masks.
2. **The arity half of the prediction fails outright.** The gap peaks at arity
   2 and *narrows* at arity 3+, on all five draws (−0.0009, −0.0845, −0.1514,
   −0.1011 on the published draw). "Worse on high-arity nodes than on narrow
   ones" is not what the data says.
3. Signature count is confounded with arity and with difficulty — label accuracy
   itself climbs 0.10 → 0.65 across these buckets — and an unmeasured confound
   has an unknown sign. The remaining test is a matched contrast that varies the
   signature count while holding node type and arity fixed.

## Two harness observations, found while auditing

**The copy ceiling is computed on the label head's denominator.**
`MaskedNode.summarize` sets `copy_ceiling = copy_reachable / label_n`, where
`label_n = 5,233` is the nameable subset, while `copy_acc` is scored over
`copy_n = 5,785`. From the run's own numbers `copy_reachable = 3,776` and
`copy_censored = 450`, so the ceiling on the copy head's own denominator is
(3,776 + 450) / 5,785 = **0.7305**, not 0.7216.
`tests/test_data.py::test_the_copy_ceiling_is_reported_and_bounded` pins the
value into [0, 1] and never checks the denominator. The correction moves
*against* every copy result, so nothing was flattered — but "0.346 of 0.722" is
two numbers over two populations.

**49 rows, 24 pointers.** Across `runs/`, 49 model rows carry a copy score on the
identical n = 5,785 and floor 0.2658, but they take only 24 distinct values.
`ensemble-001`, `ensemble-pointers`, `ptrgen-001`, `ptrgen-argmax` and
`ptrgen_joint-001` all sit on 0.3227312013828868 to the last digit, because
`EnsembleModel.source_votes` delegates wholesale to the first member that points.
Documented behaviour, not a bug — but the pointer field is much narrower than a
row count suggests, and the top four *distinct* pointers span 0.0125.

## What may now be written down, and what may not

**May be:** `metta_perm_pure-005` leads the copy head, first of 24 distinct
pointers, on five independent evaluations including a fresh 716-episode draw;
it beats the best previously published pointer (`corefer-001`) by +0.010 to
+0.026 accuracy and the best previously published *graph-derived-role* pointer
(`vsa_perm_hks_wide_pure-004`) by +0.012 to +0.025, the latter with every
interval excluding zero; and it does so while being **exactly** invariant to a
permutation of every symbol, which `corefer` is not.

**May not be:** "+0.049 improvement" as the atomspace's contribution — two thirds
of that is `hks`'s, and the atomspace-specific increment is **+0.0165 lift**.
Nor the single-draw comparison against `corefer-001` on its own: on the published
mask that gap is 56 items at p = 0.057, and it is the replication that carries it.

**What would still refute this:** a matched control that keeps the permutation
channel and the graded normalised roles but replaces the atomspace *query
schedule* with an arbitrary equally-rich signature set. `metta_shuf-005` shows a
shuffled schedule collapses, but a collapse is a weaker control than a rival that
works — if an arbitrary rich schedule also reached 0.346, the atomspace would be
decoration on "more graded features". Nobody has run that, and I did not.

## Reproducing this

`scripts/pointer_audit.py`, added by this work — per-item outcomes, coverage,
the back-off's own score, McNemar, lesson-cluster bootstrap, the renaming
control and the mechanism tables. Run against a four-model refit of
`configs/full179.toml`:

    uv run symbolic-ai-models sweep --config configs/full179.toml --out RUNS \
      --models metta_perm_pure-005,corefer-001,vsa_perm_hks_wide_pure-004,vsa_perm_pure-002
    uv run python scripts/pointer_audit.py RUNS \
      metta_perm_pure-005,corefer-001,vsa_perm_hks_wide_pure-004,vsa_perm_pure-002 \
      12345,12346,12347,12348 out.json 1000000

The scoring lines are copied verbatim from `_pointer_counts` rather than
reimplemented. Full suite green before and after.
