---
date: 2026-08-14
author: agent-spectral-roles
status: provisional
related: [spectral-roles-preregistration, the-harness-moves-more-than-the-models,
          slices-have-inverted-results-eight-times, a-ranking-is-a-property-of-a-metric]
---

# Roles derived from the graph: structure works, locality is worse than nothing, and neither reaches permutation

**Full 179-lesson sweep** (`configs/full179.toml`, `runs/vsa_role`), not a slice.
Floors: label 0.143, type 0.860, copy 0.266; **copy ceiling 0.722**. Every
number below is `symbolic-ai-models sweep`; the diagnostics that shaped the
design were slices and are labelled as such. `status: provisional` — every
control here was designed by the same person who wrote the models.

Pre-registration: `notes/decisions/2026-08-13-spectral-roles-preregistration.md`,
including the amendment written after the diagnostics and before the sweep.

## The identity everything rests on

`vsa-002` builds a role as the elementwise product of four independent random
atoms indexed by `(ptype, slot, depth, arity)`. The codebook is bipolar, so
`cb[s]**2 == 1`, and a masked node's own binding is never in the trace, so

    score(s) = sum_{j : label_j = s} <role(i), role(j)>  +  crosstalk

**The candidate score is the role Gram matrix.** Swapping the role construction
and touching nothing else is therefore a controlled experiment by arithmetic
rather than by care. `tests/test_vsa_spec.py::test_the_candidate_score_is_the_role_gram`
pins it.

## The result, on the equivariant rows

`structural_fallback` donates a shared memorising lookup to every row, so the
`_pure` variants are the ones that say what the *algebra* is worth. All of them
are equivariant to within noise, which is the point of reading this column.

| model | role Gram | lbl acc | lbl lift | bits | bits lift | copy acc | copy lift | rename |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `vsa_spec_shuf_pure-004` | eigenmap, **shuffled** | 0.067 | −0.089 | 7.466 | 0.203 | 0.061 | −0.279 | −0.002 |
| `vsa_hks_shuf_pure-004` | signature, **shuffled** | 0.083 | −0.071 | 7.877 | 0.159 | 0.075 | −0.260 | −0.002 |
| `vsa_spec_pure-004` | Laplacian eigenmap | 0.105 | −0.044 | 7.380 | 0.212 | 0.096 | −0.232 | −0.001 |
| `vsa_pure-002` | product of atoms (partition) | 0.200 | +0.066 | 6.940 | 0.259 | 0.181 | −0.115 | +0.002 |
| `vsa_sum_pure-004` | **sum** of the same atoms | 0.214 | +0.083 | 6.724 | 0.282 | 0.194 | −0.097 | −0.000 |
| `vsa_hks_pure-004` | **heat-kernel signature** | 0.235 | +0.107 | 6.781 | 0.276 | 0.213 | −0.072 | +0.003 |
| `vsa_perm_pure-002` | partition + permutation | **0.337** | **+0.227** | 6.622 | 0.293 | 0.310 | +0.060 | −0.003 |
| `vsa_perm_hks_pure-004` | signature + permutation | 0.281 | +0.161 | 6.484 | **0.308** | **0.333** | **+0.092** | −0.002 |

With the fallback on: `vsa-002` 0.219/+0.089 at a +0.029 renaming drop,
`vsa_sum-004` 0.228/+0.098 at +0.012, `vsa_hks-004` 0.242/+0.115 at +0.009,
`vsa_perm-002` 0.326/+0.213 at +0.010, `vsa_perm_hks-004` 0.288/+0.169 at +0.008.
The fallback is worth +0.014 to +0.023 of accuracy and carries essentially all
of the family's renaming sensitivity, exactly as it does for `vsa-002`.

## Five things, and only the second was predicted

### 1. The pre-registered eigenmap is refuted, and the reason was available in advance

`vsa_spec_pure-004` scores **−0.044 lift — below the floor**, and its own
shuffled control is only 0.038 behind it. A diffusion kernel places its mass on
hop 1, and on 550 masked nodes of a training slice:

| question | answer |
|---|---|
| the graph-**nearest** visible node carries the answer | **0.000** |
| hop distance to the nearest visible node that does | 2, 4, 6 or 7 |
| no visible node carries the answer at all | 0.575 |

A term tree alternates functor and argument levels, so a label-carrying node is
always an **even** number of hops from another one. Graph proximity is not
uninformative here, it is pointed at exactly the wrong nodes. The fitted
diffusion time ran to the **top** of its grid (`t = 16`), i.e. the likelihood
wanted the kernel smeared as close to "every node is the same role" as the grid
allowed — the model is best when its embedding is most nearly erased. By the
pre-registration's own rule that is a mis-specified grid rather than a fitted
value, and the *direction* of the boundary is the finding.

**This is the part the brief did not ask for and is the most useful thing here.**
"Embed the nodes in a space derived from the graph" is not one idea; it is two,
and they differ by which similarity the space encodes.

### 2. Graded beats partitioned — with no graph at all

`vsa_sum-004` superposes the same four atoms instead of binding them, so
`<role_i, role_j> = d * (how many of the four coordinates agree)`. That is the
back-off ladder `omegaclaw` and the copy floor write as a stack of `if`
statements, expressed as one superposition. It fits nothing `vsa-002` does not.
`*` → `+` is worth **+0.017 label lift, +0.023 bits lift, +0.018 copy lift**, and
it *reduces* the renaming drop from +0.029 to +0.012.

Without this row a win for any graph embedding would be unattributable between
"graded helps" and "graph-derived helps".

### 3. The graph beats the hand-built coordinates, and the control says it is the graph

`vsa_hks_pure-004` uses **no hand-built coordinate of any kind** — no parent
type, no slot, no depth, no arity. Each node's role comes from its heat-kernel
signature `h_i(t) = sum_k e^{-t λ_k} u_k[i]²` read at eight diffusion times: a
spectral quantity, invariant under graph automorphism, high for two nodes in
*similar local structure* however far apart they sit. It scores +0.107 against
the hand-built partition's +0.066 and the hand-built graded ladder's +0.083.

The control is decisive. `vsa_hks_shuf_pure-004` permutes the signature rows
across nodes: the Gram's value multiset survives **bit-identically** (asserted in
the tests), only the correspondence to the graph dies. It falls from **+0.107 to
−0.071**, from the best non-permutation row in the family to below the shuffled
eigenmap. The embedding's entire contribution is the correspondence between a
coordinate and the node it describes.

### 4. It does not reach permutation, and the metrics disagree about what happens when you compose them

`vsa_perm_pure-002` remains the row to beat at +0.227, and reproduced its
published numbers to three decimals in this sweep, as did `vsa-002` (0.219,
+0.089, 6.796, 0.181, +0.029 — every digit). **A better role Gram is worth less
than half of what a positional channel is worth**, at 11x the cost.

Composing them is where the honest reading gets uncomfortable, because the three
heads rank the pair differently:

| | label lift | bits lift | copy lift |
|---|---:|---:|---:|
| `vsa_perm_pure-002` | **+0.227** | 0.293 | +0.060 |
| `vsa_perm_hks_pure-004` | +0.161 | **+0.308** | **+0.092** |

The signature costs 0.066 of label lift and buys 0.032 of copy lift and 0.015 of
bits lift. `vsa_perm_hks-004`'s +0.092 copy lift is the **second-best pointer in
this repo**, behind `corefer-001`'s +0.096 and ahead of everything else. There is
no single ranking of these two models; which one is better is a property of the
metric, and quoting either alone would be the mistake this repo has made before.

### 5. The harness trap I found was itself a slice artifact — the ninth

On a three-lesson diagnostic, fitting the softmax temperature alongside the
construction knob collapsed held-out training accuracy from 0.126 to 0.040: a
flat softmax over a graded Gram is an *episode unigram*, good bits and a bad
classifier. `vsa_hks_ll-004` was registered to price that at full scale.

**On 179 lessons the likelihood picks sharpness 12 by itself and the row comes
out bit-identical to `vsa_hks-004`** — 0.242, +0.115, 6.643, 0.213, +0.009, every
digit. The trap is real on three lessons and absent on a hundred and seventy-nine.
Holding the temperature fixed is still right, but for the design reason (it keeps
a `-004` row from fitting a degree of freedom the `-002` rows cannot), not for the
rescue reason the slice claimed.

## The dimension / quality / throughput curve

`scripts/vsa_dim_curve.py`. Quality is read out of the per-dimension sweeps
(`runs/vsa_dim/d*`); only the timing is measured in the script, on the very model
the sweep fitted. **Throughput is CPU time on the model's own inner loop** —
build the view, run the algebra, clean up — because `RuleBasedModel.forward`
also materialises a dense `[B, L, V]` tensor whose cost is O(vocabulary) and
completely independent of `d`. The end-to-end rate is reported beside it; the
ratio says how much of a symbolic model's deployed cost is its reasoning and how
much is the interface it speaks through. Two independent timing passes; the
spread is quoted where it exceeded 5%.

| model | d | lbl acc | lbl lift | bits | reasoning tok/s | end-to-end tok/s |
|---|---:|---:|---:|---:|---:|---:|
| `vsa-002` | 256 | 0.178 | +0.041 | 6.984 | **240,780** | 14,528 |
| `vsa-002` | 1,024 | 0.215 | +0.083 | 6.813 | 29,150 | 4,731 |
| `vsa-002` | 4,096 | 0.219 | +0.089 | 6.796 | 17,084 | 3,606 |
| `vsa-002` | 16,384 | 0.217 | +0.086 | 6.789 | 368 | 231 |
| `vsa-002` | 65,536 | 0.218 | +0.087 | 6.786 | 244 | 137 |
| `vsa_sum-004` | 256 | 0.219 | +0.088 | 6.718 | **282,170** | 14,595 |
| `vsa_sum-004` | 1,024 | 0.227 | +0.097 | 6.602 | 34,302 | 4,791 |
| `vsa_sum-004` | 4,096 | 0.228 | +0.098 | 6.583 | 18,995 | 3,628 |
| `vsa_sum-004` | 16,384 | 0.226 | +0.097 | 6.568 | 489 | 264 |
| `vsa_sum-004` | 65,536 | 0.226 | +0.097 | 6.563 | 293 | 155 |
| `vsa_hks-004` | 256 | 0.231 | +0.103 | 6.767 | 1,334 | 504 |
| `vsa_hks-004` | 1,024 | 0.244 | +0.118 | 6.659 | 995 | 379 |
| `vsa_hks-004` | 4,096 | 0.242 | +0.115 | 6.643 | 848 | 344 |
| `vsa_hks-004` | 16,384 | 0.241 | +0.114 | 6.643 | 420 | 222 |
| `vsa_hks-004` | 65,536 | 0.241 | +0.114 | 6.638 | 233 | 104 |

### What the curve says

**Quality saturates at d = 1,024 for every construction, and the last 64x of
dimension buys nothing whatsoever.** `vsa-002` moves 0.215 → 0.218 from 1k to
64k; `vsa_sum-004` 0.227 → 0.226; `vsa_hks-004` 0.244 → 0.241 — all three
*decline* slightly. The right-hand end exists precisely so this can be said:
going overboard on dimension costs a factor of 120 in throughput and returns
nothing. Pre-registered prediction 5 said quality would saturate once projection
noise fell below the kernel's resolution and be flat past 4,096; it is flat past
1,024, so the saturation is earlier than predicted and the direction was right.

**The throughput cliff is between 4k and 16k, and it is not O(d).** 256 → 4,096
costs 14x for 16x the dimension; 4,096 → 16,384 costs **46x** for 4x. A role
matrix at `d = 16,384` is 128 × 16,384 × 4 B = 8 MB and stops fitting in cache;
past that the algebra is memory-bandwidth-bound and dimension is nearly free to
*add* and ruinous to *use*.

**The embedding's cost is not the dimension — it is the eigendecomposition.**
`vsa_hks-004` is nearly flat in `d` (1,334 → 233 tok/s over a 256x range, where
`vsa-002` moves 240,780 → 244, a factor of 987). Its floor is the per-episode
`eigh`, which is O(n³) and independent of `d` entirely. At the dimension where
quality saturates the signature runs at ~1,000 tok/s against the partition's
~29,000: **a 29x tax, all of it spent before a single hypervector is touched.**

**Against the cost thesis.** `APPROACH.md` puts the target at ~200k tokens/sec
for 15-30 billion tokens per dollar, and `vsa-002` at d = 256 lands at 240,780 —
which is a useful check that this script's definition reproduces the repo's
published figures. At ~1,000 tok/s a billion tokens is 278 core-hours, so the
signature is **100-300x past the budget** while `vsa_sum-004` at d = 256 is
comfortably inside it.

### The practical row

**`vsa_sum-004` at d = 256 matches `vsa-002` at d = 4,096 on accuracy (0.219
against 0.219) at 282,170 tok/s against 17,084 — 17x cheaper for the same
score**, better bits (6.718 against 6.796) and half the renaming drop. One
character, `*` → `+`, and no eigendecomposition anywhere. If anything here goes
into production it is that.

## What would refute this

- **The shuffled control matching its treatment.** It does not: +0.107 → −0.071.
  This is the load-bearing control and it is the one that could have ended the
  line cheaply.
- **The signature reading symbol identity.** It cannot: a role is a function of
  the tree's shape, asserted per node in
  `test_a_role_is_a_function_of_the_tree_and_of_nothing_else`, and every `_pure`
  row measures within 0.003 of zero renaming drop.
- **The `-002` rows failing to reproduce.** They reproduce to every printed digit
  (`vsa-002` 0.219/+0.089/0.181/+0.029, `vsa_perm_pure-002`
  0.337/+0.227/0.310/−0.003), which is also what licenses the behaviour-preserving
  split of `_cleanup` in `vsa_002/model.py`.
- **A wider diffusion-time grid rescuing the eigenmap.** Not run. The fit sits on
  the grid's top and the top is measured to be near the all-ones kernel, so
  extending it can only move further toward "the embedding contributes nothing" —
  but this is an argument, not a measurement, and it is the loosest claim here.

## Open, and worth someone else's hands

- The signature and the permutation channel are **complementary on the copy head
  and antagonistic on the label head**. Nobody has fitted the balance between
  them; `vsa_full_gated-002` is the precedent for how to and for how a boundary
  fit gets misread.
- `_laplacian_spectrum` uses parent-child edges only. The `same_label`
  coreference edges are visible and were rejected as a confound
  (`relation_matrix` withholds them for the queried nodes), but a signature
  computed on the richer graph is a different and untried model.
- The `eigh` is 29x of tax for +0.024 of lift. A cheap approximation to the
  signature — Chebyshev on the Laplacian, or plain WL colour refinement, which
  is the discrete limit of the same idea — would test whether the *quantity* or
  the *exactness* is what pays.
