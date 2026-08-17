---
date: 2026-08-16
author: cart scouting arm
status: measured
pre-registration: 2026-08-16-cart-preregistration-order-propagation-backtracking
related: [2026-08-16-constraint-anchored-infilling-and-the-backtrack,
          2026-08-13-the-harness-moves-more-than-the-models,
          slices-invert-results-six-times]
---

# Infilling errors clump at 0.77 and cascade at 0.005; CART is a null, and the ordering is the whole of the +0.004

Adapting CART (arXiv:2607.16727, Cheng/Dai/Sun) to masked-node infilling: fill
the most-constrained hole first, propagate each fill's consequences, backtrack
when the partial graph goes inconsistent. Three arms registered together, all
wrapping `frontier-001` so they differ **in the decoder alone**. Predictions
written down first in
`notes/decisions/2026-08-16-cart-preregistration-order-propagation-backtracking.md`.

## 1. The cascade rate, which is a property of the task and had never been measured

`frontier-001`, 300 eval episodes of `configs/full179.toml`, 1,675 receiver
holes. Hypothesis-forming script, not the sweep.

**Observationally the CART premise looks confirmed.** Taking an episode's holes
in index order:

| conditioning | P(hole correct) | n |
|---|---|---|
| marginal | 0.3749 | 1675 |
| previous hole correct | 0.5500 | 760 |
| previous hole wrong | 0.2295 | 915 |

so **P(wrong | previous wrong) = 0.7705 against a marginal 0.6251**. That is the
same shape and nearly the same magnitude as the 0.65 CART reports before its
intervention. Errors clump, hard.

**Interventionally it evaporates.** Pick one hole as the donor, commit a value
there, rescore every other hole of the episode three ways:

| condition | receiver accuracy | n |
|---|---|---|
| (a) donor left masked | 0.4185 | 1675 |
| (b) donor filled with the **true** label and type | 0.4251 | 1675 |
| (c) donor filled with the model's own prediction | 0.4203 | 1675 |

* **headroom** (b − a) = **+0.0066**
* realised (c − a) = +0.0018
* **cascade cost** (b − c) = **+0.0048**

An *oracle* neighbour — the answer handed over for free — is worth 0.7 accuracy
points to the holes around it. That is the ceiling on everything any propagator,
constraint system or backtracker can win here, because none of them can do
better than knowing the answer. And a wrong fill costs 0.5 points, not the
collapse the observational table implies.

**The clumping is episode difficulty, not causation.** The 0.77 is the
twelfth instance of the mechanism in
`notes/lessons/slices-invert-results-six-times` and MEMORY's "a slice may form a
hypothesis, never report one": conditioning on a *sibling outcome* conditions on
the episode, and episodes differ enormously in how answerable they are. The
split by donor outcome shows it directly — receivers score 0.4514 when the
donor's own fill was right, 0.4286 when it was wrong, and **0.3721 when the
model abstained on the donor entirely**. The abstention bucket is the tell: an
abstention cannot cause anything downstream, and it is the bucket with by far
the worst receivers. What that column ranks is how hard the episode was.

The observational cascade rate is therefore a real number that measures the
wrong thing, and reporting it alone would have been this repo's next confident
wrong reading.

## 2. The three arms on `runs/full179`

`uv run symbolic-ai-models sweep --config configs/full179.toml --models
cart-001,cart-order,cart-noop --tasks node --out runs/full179`.
Floor `label_acc` 0.143; copy ceiling 0.722; label n = 5,233 for every row.

| model | label_acc | label_bits | type_acc | renaming drop |
|---|---|---|---|---|
| `frontier-001` (reference, already run) | 0.4042 | 7.4326 | 0.8633 | 0.406 -> 0.034 (−0.372) |
| `cart-noop` | **0.4086** | **7.3916** | **0.8706** | 0.409 -> 0.035 (−0.375) |
| `cart-order` | **0.4086** | **7.3916** | **0.8706** | 0.409 -> 0.035 (−0.375) |
| `cart-001` | 0.4074 | 7.3986 | 0.8701 | 0.409 -> 0.035 (−0.374) |

Read against the pre-registration:

1. **`cart-noop` ≈ `cart-order`: confirmed, and exactly** — the two agree to four
   decimals on all three metrics. The backtracking machinery, run in full with a
   tautological assertion, changes nothing by itself. The table is readable.
2. **Decode order is worth +0.0044** `label_acc` and −0.0410 `label_bits`. The
   original prediction of +0.01 to +0.04 was wrong by roughly five times; the
   revision to +0.000..+0.005 made *after* the cascade measurement and before the
   sweep is the one that held. The oracle headroom of +0.0066 bounded it and did
   so correctly.
3. **The constraint logic is worth −0.0012** `label_acc` and +0.0070
   `label_bits`. Both metrics agree and both say the propagation and the
   backtracking make the model slightly **worse** than the same decoder without
   them.

The pre-registered refutation criterion was: *if `cart-001 − cart-order` is
smaller than `cart-order − frontier-001`, the gain is decode order and not
logic.* It is smaller and it is negative. **The claim that constraint
propagation is doing the work is refuted by its own controls.**

`label_acc` and `label_bits` rank these four identically, which is worth saying
because in this repo they usually do not — there is no metric disagreement to
hide behind here.

## The floor, the control, and what would have refuted this

* **Floor**: `label_acc` 0.143, `label_bits` floor 9.369; copy ceiling 0.722.
* **Reference arm**: `frontier-001`, the same reasoner with the repo's existing
  independent decoder. All three CART arms inherit its rules, gate, calibrator
  and back-off unchanged, so nothing here is a reasoning difference.
* **Propagation-free control**: `cart-order`. Isolates decode order.
* **No-op-constraint control**: `cart-noop`. Isolates the machinery.
* **What would have refuted the null**: `cart-001` beating `cart-order` by more
  than `cart-order` beats `frontier-001`, on either metric. It does not, on
  either.
* **What would have refuted the *harness* reading**: `cart-noop` separating from
  `cart-order`. It does not, to four decimals.
* **Renaming**: unchanged across all four rows (−0.372 to −0.375). The sequential
  decoder did not open a new symbol-memorisation channel; it is the same model
  reading slightly more context.

**The null is not an empty constraint set.** `runs/full179/cart-001/rules.txt`
records what was actually fitted: **909 slot domains, 5,220 arity entries, 5,220
known labels**, on top of frontier's own 427 label rules and 492 type rules. The
assertions existed, had support and were checked at every candidate. They did not
help.

## Why the logic could not have helped, in one sentence

A learned domain can only change an answer when the reasoner's argmax is outside
the domain *and* the reasoner has kept the right symbol in its vote table — and
`frontier-001` emits a single-symbol vote from one cross-fitted rule, so the
domain almost never has a second candidate to fall back to, and the backtracker
almost never has a checkpoint whose alternative is better.

## Verdict

**Not worth going deep on.** The gate is not the constraint language, the
propagator or the search: it is that on this curriculum an episode's holes are
very nearly independent given the visible graph. An oracle neighbour is worth
+0.0066 and the whole sequential decode delivers +0.0044 — the two are measured
over different denominators (receiver holes of multi-hole episodes against all
5,233 scored labels) so the ratio is not exact, but they are the same size, and
the size is "one twentieth of the gap between the best model and the floor".
Every part of CART that is actually CART — the assertions, the propagation, the
rollback — contributes a negative number on top of that.

What survives and is worth keeping: the **interventional cascade measurement
itself**. It is model-agnostic, costs one fit, and it turned a 0.77 that looked
exactly like a published headline into a 0.005. Any future proposal here that
depends on one fill informing another should be made to clear it first.

## Caveats

* The cascade numbers are from a scratch script on 300 episodes and are
  hypothesis-forming; the four-row table is from the sweep, which is the
  authority. Nothing in the verdict rests on the scratch numbers alone — the
  sweep independently reproduces the size of the effect the scratch script
  predicted.
* Coreference is **not** propagated, because `relation_matrix` withholds the
  coreference edges of hidden nodes. If those edges were visible the headroom
  might be larger, and that is a real limit on this measurement rather than a
  result. Worth a question note.
* One reasoner. The headroom is a property of `frontier-001`'s hypothesis class
  as much as of the task; a reasoner whose rules read further into the tree
  would have more to gain from a committed neighbour.
