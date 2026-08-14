---
date: 2026-08-13
author: agent-spectral-roles
status: measured
related: [vsa_perm_002, learn-or-seed-the-vsa-codebook]
---

# Spectral role vectors for the VSA family (`-004`): what is predicted, and what would refute it

Written **before** the sweep ran. Numbers land in
`notes/findings/2026-08-13-spectral-roles-are-a-graded-partition.md`.

## The defect being addressed

`tests/test_vsa_perm.py::test_a_product_of_atoms_gives_a_hard_partition_not_a_similarity`
pins the fact that `vsa-002`'s role vector — the elementwise product of four
independent bipolar atoms indexed by `(ptype, slot, depth, arity)` — has an
inner product of exactly `d` against itself and a zero-mean random walk against
anything else. Measured at `d = 4096`: `4096 ± 0` versus `4 ± 60`. Since the
masked node's own binding is never in the trace, the candidate score reduces
exactly to

    score(s) = sum_{j : label_j = s} <role(i), role(j)>  +  crosstalk

so the model can only answer where a visible node shares the query's *exact*
role tuple. It is a table lookup with **no back-off**, and permutation
(`vsa_perm-002`) was bolted on to give it any reach at all.

## The construction chosen, and why this one

That identity — the score *is* the role Gram matrix — is what makes this
tractable: the codebook is bipolar so `cb[s]**2 == 1` elementwise, and therefore
**any** role vector at all, random or not, yields `score(s) = sum_j K(i, j)`
where `K` is the role Gram. Changing the role construction changes `K` and
nothing else in the algebra. So the experiment is: replace a `K` that is a hard
0/1 partition with a `K` that is a graded function of graph distance.

**Heat kernel of the tree's normalised Laplacian, factorised and randomly
projected.** Per episode, over the visible tree shape only:

1. `A` = undirected parent-child adjacency; `L = I - D^-1/2 A D^-1/2`.
2. `L = U diag(lam) U^T` (one `eigh`, `n <= 128`).
3. `psi_i = (U diag(exp(-t lam / 2)))_i`, then `phi_i = psi_i / ||psi_i||`.
4. `role_i = sign(phi_i @ R)`, `R` a fixed `(max_nodes, d)` bipolar matrix drawn
   from the model seed.

Then `<role_i, role_i> = d` exactly, as before, and
`<role_i, role_j> ≈ d · (2/pi) · arcsin(K_ij)` with
`K = D_h^-1/2 exp(-tL) D_h^-1/2` — the **diffusion kernel, correlation-normalised**,
which is PSD with unit diagonal, bounded in `[-1, 1]`, and free of any bandwidth
knob. Step 4's `sign` keeps the algebra bipolar so the crosstalk statistics are
*identical* to `vsa-002`'s and the only difference between the two models is the
Gram; the arcsine is monotone, so it cannot reorder candidates.

Rejected alternatives, and why:

- **Raw Laplacian eigenvectors as coordinates + a Gaussian RFF encoding.** Needs
  a bandwidth `sigma`, and eigenvector entries scale as `1/sqrt(n)`, so the
  bandwidth would silently mean different things on a 12-node and a 120-node
  graph. The correlation-normalised kernel has no such knob.
- **Commute-time / pseudo-inverse coordinates (`u_k / sqrt(lam_k)`).** Unbounded
  as `lam_k -> 0`; the heat kernel is the same family with a bounded weighting.
- **Including the `same_label` coreference edges of `rel` in `A`.** They are
  visible and would be legitimate, but `relation_matrix` *withholds* them for
  exactly the hidden nodes we query, so they can only move the query node's
  neighbours around, never the query itself. Confound with no upside. Noted as
  an open question rather than taken.
- **Keeping the projection real-valued instead of taking `sign`.** Preserves the
  kernel exactly rather than through an arcsine, but raises the crosstalk sd
  from `sqrt(d)` to `sqrt(3d)`, which would make the comparison against
  `vsa-002` a comparison of two things at once.

`t` is the one knob and it is the whole story: as `t -> 0` the kernel goes to the
identity (a hard partition finer than `vsa-002`'s, which answers *nothing*, since
the query's own binding is absent); as `t -> inf` it goes to all-ones (every node
is the same role, and the model becomes a unigram over the episode's visible
symbols). In between it is a **graph-distance back-off**. `t` is fitted on
held-out *training* episodes by the log-mass the cleanup puts on the symbol that
turned out to be right — design rule 4, a quantity not an event, the same
procedure `vsa_full_gated-002` uses. Grid `0.25 … 8.0`; a fit landing on either
end is reported as a mis-specified grid, not as a result.

## The models registered

| name | what it changes |
|---|---|
| `vsa_spec-004` | `vsa-002` with spectral roles. **The experiment.** |
| `vsa_spec_shuf-004` | the same spectral coordinates, **permuted across nodes**. **The control.** |
| `vsa_spec_mix-004` | discrete role atoms **plus** spectral role, superposed |
| `vsa_perm_spec-004` | `vsa_perm-002` with spectral roles in the role channel |
| `*_pure-004` | each of the above with `structural_fallback` off |

The shuffle is drawn from a permutation seeded by the model seed and the graph's
own shape, so it is deterministic and identical between fitting and prediction.
It preserves the multiset of spectral coordinates and hence the *entire
distribution* of pairwise kernel values, while destroying which node holds which.
If the shuffled control matches the real one, the embedding contributed nothing.

## Predictions, and what refutes each

Written down first so the reading cannot drift toward the write-up.

1. **`vsa_spec-004` beats `vsa-002` on label accuracy.** A graded back-off should
   answer the ~62% of questions where no visible node shares the query's exact
   role tuple, which `vsa-002` answers from pure noise.
   *Refuted if* `vsa_spec-004` <= `vsa-002` on `label_acc`. Reported as a null,
   with the reading that graph proximity is the wrong similarity for this
   curriculum, not that "the embedding needs tuning".
2. **The shuffled control lands at or below `vsa-002`.** It has a graded kernel
   with the right distribution and the wrong attachment, so it should retrieve a
   graded mixture of irrelevant nodes.
   *Refuted if* `vsa_spec_shuf-004` matches `vsa_spec-004` to within the seed
   noise of this harness (~0.005 on `label_acc`). That outcome kills the whole
   line and is the honest reason this control exists.
3. **Both stay exactly renaming-equivariant with `structural_fallback` off.**
   Roles are a function of the *tree shape* and never of a label; the codebook is
   random. So the `_pure-004` drop should be within noise of zero, exactly as
   `vsa_pure-002` is at +0.002 and `vsa_perm_pure-002` at -0.003.
   *Refuted if* any `_pure-004` drop exceeds ~0.01. That would mean the
   embedding is reading symbol identity through some path I have not seen, and
   the whole family would have to be re-derived.
4. **`vsa_spec_mix-004` beats both of its parts.** Superposing the two roles is a
   back-off ladder in one vector: exact-tuple match scores `d`, graph proximity
   scores `d·K` under it.
   *Refuted if* it lands below `max(vsa-002, vsa_spec-004)`, which would be the
   fourth time in this repo that superposing a weaker channel onto a stronger one
   made the pair worse, and would be reported as such.
5. **Quality saturates in `d` around the point where the projection noise falls
   below the kernel's own resolution.** The random projection puts a `1/sqrt(d)`
   error on every kernel entry, so `d = 256` should be visibly degraded
   (`±0.06` on a kernel bounded by 1) and `d >= 4096` (`±0.016`) should be flat.
   Throughput is `O(d)` throughout.
   *Refuted if* the curve keeps climbing past `d = 16384`, which would say the
   binding capacity rather than the kernel resolution is binding.

## Amendment, written after the diagnostic and before the sweep

Everything above stands as written. What follows was added after two
hypothesis-forming diagnostics on a three-lesson slice and **before any sweep
was run**; nothing below was informed by an evaluation-seed number.

### The eigenmap is pointed at the wrong nodes, and it is measurable in advance

550 masked nodes, three lessons, training seeds:

| question | answer |
|---|---|
| the graph-**nearest** visible node carries the answer | **0.000** |
| hop distance to the nearest visible node that does | 2, 4, 6 or 7 |
| no visible node carries the answer at all | 0.575 |
| a visible carrier shares the query's exact role tuple | 0.140 |

The term tree alternates functor and argument levels, so a label-carrying node is
always an **even** number of hops from another one, and a diffusion kernel puts
its mass on hop 1. Prediction 1 above is therefore not merely wrong, it was
wrong for a reason available before the experiment: graph proximity is
anti-correlated with where the answer is. Raw arg-max over the Gram, no gate, no
back-off, same slice: ``vsa-002`` 0.100, diffusion locality at ``t = 4``
**0.005**.

The eigenmap arm ships anyway, with its shuffled control. A pre-registered
prediction that failed is a result.

### Two arms added, and why each

**`vsa_sum-004` — superpose the four atoms instead of binding them.** The
thesis "a hard partition cannot interpolate" does not require a graph at all:
``role = ptype + slot + depth + arity`` gives
``<role_i, role_j> = d * (how many of the four agree)``. Raw top-1 **0.185**
against the product's 0.100. Without this row, a win for any graph embedding
would be unattributable between "graded helps" and "graph-derived helps". It
fits nothing ``vsa-002`` does not, so it is an *exactly* matched contrast: `*`
against `+`.

**`vsa_hks-004` — the heat-kernel signature.** ``h_i(t) = sum_k e^{-t lam_k}
u_k[i]^2`` is a node's own diffusion profile read at eight times: a spectral
quantity of the graph, invariant under automorphism, and high for two nodes in
*similar local structure* however far apart they are. Raw top-1 **0.149**, using
no hand-built coordinate of any kind. This is the "structural equivalence rather
than homophily" distinction, and the measurement above says it is the one that
matters here. Its Gram is *anti*-correlated with hop distance where the
eigenmap's is correlated, which is the cleanest statement of the difference.

### The harness trap, which cost more than any architecture here

The scalars were originally to be fitted by the log-mass of the **bare cleanup**.
That is wrong twice over and both were caught before the sweep:

1. A bare cleanup that is confident and wrong pays `log(1e-6) = -13.8`. The
   deployed model never does — the calibrator mixes it with the back-off — so
   the criterion priced a risk the model does not take. Fixed by selecting on
   the **calibrated mixture's** held-out likelihood, which is the objective
   `MassCalibrator` already maximises.
2. Fitting the softmax **temperature** on that criterion still chose the
   degenerate corner, because *a flat softmax over a graded Gram is an episode
   unigram* — an excellent density estimate and a terrible classifier. Held-out
   *training* accuracy for `vsa_hks-004`: **0.126** at `(knob 1.0, sharp 12)`,
   **0.040** at `(4.0, 3)`, and the joint fit chose `(4.0, 3)`.

Resolved by holding the temperature at `vsa-002`'s fixed 12 — so a `-004` row
fits at most one scalar more than a `-002` row — and registering
**`vsa_hks_ll-004`** to price the decision on the full curriculum. With the
temperature fixed, the mixture likelihood picks the accuracy optimum for both
spectral constructions, so the criterion is sound and the temperature was the
confound. Pre-registered for that row: it should **win on `label_bits` and lose
on `label_acc`**. If it loses on both the temperature is merely mis-fitted; if
it wins on both, the slice above was the misleading thing.

`vsa_randfit-004` from the plan above is **dropped**: with no fitted
temperature it would be bit-identical to `vsa-002` under a second name.

### Predictions replacing 1 and 4

1'. `vsa_spec-004` loses to `vsa-002`, and loses to its own shuffled control.
    *Refuted if* it clears either.
4'. `vsa_sum-004` and `vsa_hks-004` both clear `vsa-002`; `vsa_hks_shuf-004`
    lands far below `vsa_hks-004`. *Refuted if* the shuffled control matches,
    which would make this a finding about graded Grams and not about graphs.

## Costs stated in advance

Per episode the model now pays one `eigh` on an `n x n` matrix (`n <= 128`) plus
an `(n x n) @ (n x d)` projection, against `vsa-002`'s four table lookups per
node. That is a real and deliberate cost — the point of the dimension curve is to
price it — and it is quadratic-to-cubic in *nodes* while everything else here is
linear. The repo's cost thesis has 15-30x of headroom against the $1/1B target,
so the question is not whether this is affordable but what the exchange rate is.
