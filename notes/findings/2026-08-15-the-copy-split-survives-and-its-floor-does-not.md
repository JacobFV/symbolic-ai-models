---
date: 2026-08-15
author: agent-refuter
status: measured
related: [2026-08-14-the-label-score-is-a-copy-score,
          2026-08-13-a-control-that-could-fail,
          2026-08-13-a-ranking-is-a-property-of-a-metric,
          2026-08-13-the-harness-moves-more-than-the-models,
          2026-08-14-an-unmeasured-confound-has-an-unknown-sign]
---

# The decomposition survives every attack; the floor it is read against does not

**Independent refutation of
`notes/findings/2026-08-14-the-label-score-is-a-copy-score.md`, by an agent that
did not write it.** All 179 lessons, 716 evaluation episodes, 5,233 scored fills,
`mask_rate=0.15`, `mask_mode=scatter`. The weights of `runs/infill-node-r015` are
not tracked, so the arm was **re-run from scratch** into `runs/refute-node-r015`;
all twelve summaries are **bit-identical** to the published ones in `final`,
`floors` and `renaming`, and the split table below reproduces the note's to the
digit. Two new floors were added to `MaskedNode` for this
(`split_floor(fit_per_bucket=True)`, `split_copy_floor`) with three tests.

**Verdict: the decomposition is right and every attack on it failed. What dies
is the second of its three readings, and it dies to the floor rather than to the
data — the note quotes a memorising lookup as the floor in both buckets, when the
bucket boundary is exactly the line a renaming-invariant model cannot cross.**

## The table, with the floor the note did not quote

`c` and `n` are `acc | copyable` and `acc | not copyable`; `c−ptr` is the
copyable column against a **renaming-invariant** structure-only floor.

| model | c | n | all | c − lookup (0.1581) | **c − pointer (0.3345)** | n − lookup (0.1058) | renaming drop |
|---|---:|---:|---:|---:|---:|---:|---:|
| `corefer-001` | 0.4936 | 0.0034 | 0.3572 | +0.336 | **+0.159** | −0.102 | +0.0032 |
| `omegaclaw_rank-001` | 0.4690 | 0.0631 | 0.3560 | +0.311 | +0.135 | −0.043 | +0.0173 |
| `ptrgen-001` | 0.4616 | 0.0103 | 0.3359 | +0.304 | +0.127 | −0.096 | +0.0055 |
| `omegaclaw_ctx-001` | 0.4571 | 0.0508 | 0.3440 | +0.299 | +0.123 | −0.055 | +0.0179 |
| `routes-001` | 0.4481 | 0.0000 | 0.3233 | +0.290 | +0.114 | −0.106 | −0.0004 |
| `vsa_perm-002` | 0.4351 | 0.0432 | 0.3260 | +0.277 | +0.101 | −0.063 | +0.0096 |
| `ruleinduce-001` | 0.4248 | 0.0810 | 0.3291 | +0.267 | +0.090 | −0.025 | +0.0267 |
| `brill-001` | 0.3498 | 0.1366 | 0.2905 | +0.192 | +0.015 | +0.031 | +0.1301 |
| `evidence-001` | 0.3032 | 0.0014 | 0.2192 | +0.145 | **−0.031** | −0.104 | +0.0034 |
| `grammar-001` | 0.1907 | 0.1784 | 0.1873 | +0.033 | **−0.144** | +0.073 | +0.1589 |
| `ngram-001` | 0.1753 | 0.1544 | 0.1695 | +0.017 | **−0.159** | +0.049 | +0.1426 |
| `ctw-001` | 0.1157 | 0.0899 | 0.1085 | −0.042 | **−0.219** | −0.016 | +0.0878 |
| **lookup floor** (`split_floor`) | *0.1581* | *0.1058* | *0.1432* | | | | |
| **pointer floor** (`split_copy_floor`) | *0.3345* | ***0.0000*** | *0.2394* | | | | |
| **oracle pointer** | *1.0000* | ***0.0000*** | *0.7216* | | | | |

`all` matches each row's published `label_acc` to 1e-9. n = 3,776 copyable and
1,457 not, share 0.7216 — the run's own `copy_ceiling`.

## What I could not break

**1. It is not vocabulary coverage — the kill hypothesis I was sent to test, and
the one that would have made the finding true but trivial.** If the non-copyable
fills were the invented nonce symbols the vocabulary cannot name, "every model
scores ~0" would be a fact about the tokenizer. Measured **within each bucket**,
over all 5,785 label-bearing masked nodes of the published draw:

| bucket | labelled | scored | censored | coverage |
|---|---:|---:|---:|---:|
| copyable | 4,226 | 3,776 | 450 | **0.8935** |
| not copyable | 1,559 | 1,457 | 102 | **0.9346** |

Coverage is **higher** on the non-copyable side. The censoring falls almost
entirely on the copyable bucket (450 of 552), exactly as `_copy_counts` already
documents — so if anything the split *understates* the copyable share of the
uncensored score. And the surviving non-copyable answers are ordinary symbols:
median **105** occurrences in the training draw (copyable: 365), 10th percentile
20, and **0.07%** never seen at all. They are memorisable, which is why a lookup
table reaches 0.106 there. Hypothesis dead.

**2. It is not a floor fitted pooled and reported bucketed.** Fitting one
`_ContextRule` per bucket instead of one scored in two *raises* the non-copyable
floor from **0.1058 to 0.1202** and the copyable one from 0.1581 to 0.1621. The
note's floor is generous to the models, not harsh. (That per-bucket object is a
ceiling and not a floor, and `split_floor`'s docstring now says so: copyability
is whether the **hidden** label sits on a visible node, so no predictor may
condition on it. Splitting the score by it is a decomposition; splitting the
predictor by it is reading the answer.)

**3. It is not one masking draw.** Lesson-cluster bootstrap, 2,000 draws over the
179 lessons, non-copyable bucket: `corefer-001` **0.0035** [0.0007, 0.0069],
`routes-001` 0.0000 [0.0000, 0.0000], `grammar-001` **0.1786** [0.1602, 0.1968],
`ngram-001` 0.1544 [0.1357, 0.1743]. `grammar` beats `corefer` in **2,000 of
2,000** draws. Paired exact McNemar on the same 1,457 fills: 255 discordant pairs
for `grammar`, **0** for `corefer`, p = 3.5e-77.

**4. It is not a lesson family and it is not tree depth** — two confounds the
note did not test (it tested node type). Within each of the 102 lessons with at
least five fills on both sides, `corefer-001`'s gap is positive in **102 of
102**, median +0.472, and its non-copyable accuracy is above zero in **2 of
102**; `routes-001` 101 of 102 and **0 of 102**. Split by graph depth instead,
`corefer`'s non-copyable column is 0.000 at every depth from 3 to 7 while its
copyable column runs 0.302–0.807.

So the 72:28 mixture is real, the columns are real, and reading 3 — the ranking
inversion — is as solid as a result in this repo gets.

## What dies: reading 2, and it dies to the floor

> *"Every renaming-invariant model is below the content-blind floor on the
> non-copyable quarter, and every vocabulary model is above it… where there is no
> coreferent to read they are worse than a table."*

**The non-copyable bucket admits no renaming-invariant predictor at all, so this
is true of the best possible one and says nothing about `corefer-001`.** The note
reasoned its way to the neighbouring question and did not run it; run, it gives
the opposite detail and a much sharper conclusion. Renaming every symbol — the
permutation the repo already applies — and re-splitting the *same* fills (a
permutation preserves label equality, so the partition and the scored set are
bit-identical, which the script asserts):

| model | c plain | **n plain** | c renamed | **n renamed** | all plain | all renamed |
|---|---:|---:|---:|---:|---:|---:|
| `corefer-001` | 0.4936 | 0.0034 | 0.4921 | **0.0000** | 0.3572 | 0.3551 |
| `routes-001` | 0.4481 | 0.0000 | 0.4486 | **0.0000** | 0.3233 | 0.3237 |
| `ptrgen-001` | 0.4616 | 0.0103 | 0.4560 | **0.0000** | 0.3359 | 0.3291 |
| `ruleinduce-001` | 0.4248 | 0.0810 | 0.4137 | **0.0000** | 0.3291 | 0.2985 |
| `grammar-001` | 0.1907 | 0.1784 | 0.0026 | **0.0000** | 0.1873 | 0.0019 |

`acc | not copyable` is **exactly 0.0000 for all five under renaming**, including
`grammar-001`, which had the best column in the table. It is not a hard question
that equivariant models happen to fail; it is the memorisation channel, and
naming it "the quarter of fills it cannot copy" hides that. The pointer floor
scores **0.0000** there and so does the **oracle** pointer, by construction: if
no visible node carries the label, a predictor that may only point has nothing to
point at. Meanwhile `acc | copyable` for the equivariant rows is untouched
(`corefer` 0.4936 → 0.4921) — the note inferred 0.489 from the assumption that
`acc | not copyable` stays "pinned near 0.003 in both". It does not; it goes to
zero, and both columns contribute to the drop.

**And the floor the note quotes on the copyable bucket is half the right one.**
`split_floor` is a lookup table over *symbol identities* — renaming-variant, in a
strictly larger hypothesis class than seven of the twelve rows. The equivariant
structure-only floor is the one the repo already publishes as `copy_floor`, never
per bucket and never against `label_acc`: the commonest relative offset to a
same-label node per structural context, applied blind. Restricted to the fills
`label_acc` covers and required to land on a **visible** node, it is **0.3345**
on the copyable bucket. Against it, the mirror of reading 2 is equally true and
points the other way: **three of the four vocabulary models are below the
equivariant floor on the copyable three-quarters** (`grammar` −0.144, `ngram`
−0.159, `ctw` −0.219; `brill` +0.015 is the exception) **and seven of the eight
equivariant models are above it** (`evidence-001` −0.031 is the exception).
Reading 2 is a choice of floor, and the note chose the only floor under which the
naming models clear a bar on the only bucket where they can.

The ranking inversion survives all of this, but its location changes: the
copyable-bucket ranking is the pooled ranking with two adjacent swaps. The whole
inversion lives in the memorisation bucket.

## The part that is not about this note

`split_copy_floor`'s pooled value is **0.2394**, on the same 42,293-fill floor
sample and the same masking regime as `MaskedNode.floor`. The published
`label_floor` for this arm is **0.1432**. A structure-only, renaming-invariant
pointer therefore beats the floor every label lift in `runs/infill-node-r015` is
quoted against, by **0.096** — so every one of those lifts is overstated by at
least that, `corefer-001`'s +0.250 becoming **+0.118**, and four of the twelve
models (`grammar` 0.187, `ngram` 0.170, `ctw` 0.109, `evidence` 0.219) land
**below the strongest structure-only baseline outright**. This is
`audit-the-floor-before-quoting-a-lift` again, one level up: the object was in
every `summary.json` already, under `copy_floor`, and was never pointed at the
label score. 0.2394 is a **lower bound** on the correction — a baseline allowed
to pick between the table and the pointer per structural context can only do
better, and was not built.

Two smaller things fell out:

- **`copy_acc` credits pointing at a hidden node.** `_pointer_counts` and
  `_copy_floor` both score a landing on any same-label node, masked ones
  included, which is right for "which node corefers" and wrong for anything read
  as a label score — a symbol on a masked node cannot be read. Measured:
  `anynode_not_copyable` **0.0096** where the visible-only rule is exactly 0, and
  0.2804 against 0.2394 pooled. 0.041 of the copy floor is landings a model could
  not have used. Left in place, reported beside it; changing it would redefine
  every published `copy_acc`.
- **The prose does not rescue the bucket.** `node_text_leak` on this evaluation
  set: when the answer is absent from the visible graph the prompt names it
  **58.7%** of the time, pins it down **0.0%** of the time, and uniform guessing
  among the candidate words gives **0.0257**. So even an equivariant model handed
  the prose — none is, on this task — is bounded near 0.026 there, still 0.08
  below the lookup floor. The non-copyable bucket is a memorisation question
  under every reading available.

## What would have refuted *me*

- Coverage lower in the non-copyable bucket than in the copyable one. It is
  higher, 0.9346 against 0.8935.
- A per-bucket-fitted floor below 0.1058 on the non-copyable bucket, which would
  have meant the note's floor was too strong. It is 0.1202.
- `acc | not copyable` staying above zero for an exactly equivariant model under
  renaming. Five models, all exactly 0.0000.
- The equivariant floor on the copyable bucket coming out *below* the lookup
  floor's 0.1581, which would have left reading 2's choice of floor unarguable.
  It is 0.3345.
- A published run that did not reproduce. All twelve summaries are bit-identical.

## What the repo should take from it

`label_acc` is a 72:28 mixture and that stands. But the two questions are not
"coreference" and "everything else"; they are **"can this be copied"** and
**"was this memorised"**, and the second is one no renaming-invariant model was
ever able to answer — zero under permutation, zero for the oracle. So the
reframe the note proposed, *the symbolic models do coreference and nothing else
and are worse than a lookup table wherever there is no coreferent*, should not be
adopted: the second half is a property of the partition. The reframe that the
evidence does support is narrower and more expensive: **28% of every published
`label_acc` is a memorisation test the equivariant models score zero on by
construction, and the remaining 72% has been read against a floor 0.176 too
low.**
