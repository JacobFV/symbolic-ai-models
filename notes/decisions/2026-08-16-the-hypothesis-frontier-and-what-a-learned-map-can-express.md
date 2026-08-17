---
date: 2026-08-16
author: lead
status: preregistration
related: [2026-08-15-derivability-is-the-treatment-and-the-per-episode-permutation-is-the-control,
          2026-08-15-the-derivable-fill-is-worth-0833-to-a-lookup-and-nothing-takes-it,
          2026-08-15-a-floor-outside-the-models-hypothesis-class,
          2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name,
          2026-08-13-a-control-that-could-fail]
---

# The derivability channel is closed by the hypothesis language, and a verifier-guided frontier is the smallest thing that opens it

## Where this comes from

Four papers were handed to the repo as candidate directions. All four exist and
were checked before any of this was written:

| arXiv | what it proposes | date |
|---|---|---|
| [2608.10843](https://arxiv.org/abs/2608.10843) Hypothesis Frontier (Batzoglou) | LLM proposes first-order formulas, an **exact verifier** scores them against the data, residual errors drive the next round; valid formulas are simplified without changing training predictions | 2026-08-11 |
| [2607.20402](https://arxiv.org/abs/2607.20402) SoftReason (AbdAlmageed) | a differentiable immediate-consequence operator `T_P` over soft truth values | 2026-07-22 |
| [2607.16727](https://arxiv.org/abs/2607.16727) CART (Cheng, Dai, Sun) | reasoning interleaved with machine-checkable assertions, Boolean constraint propagation, backtrack to the last consistent checkpoint | 2026-07-18 |
| [2607.14735](https://arxiv.org/abs/2607.14735) CoTu | delegate deduction to a solver; the residual hard problem is **premise selection** | 2026-07 |

Only the first is being built now, and the reason is not that it is the newest.
It is that **this repo already has the experiment it needs, pre-registered, with
a control that provably can fail, and a channel measured at 0.833 that nothing
takes.** Adopting an architecture into a repo whose sharpest open result is
sitting unclaimed is worth more than adding a fourth direction nobody has a
floor for. The other three get `notes/questions/` entries and no code.

## The observation that made this the right target

`RESEARCH_LOG.md` reports the derived non-copyable bucket as: fifteen of twenty
models at exactly 0.000, five at 0.145–0.155, mean 0.038 against a derivation
floor of 1.000. Re-reading `runs/derive179-*/derived_split.json` sharpens it, and
the sharpened version is the reason for this note:

| model | derive | perm | shuffled |
|---|---:|---:|---:|
| fifteen models | 0.00000 | 0.00000 | 0.00000 |
| `brill` / `ctw` / `grammar` / `ngram` | **0.154574132** | 0.178 | **0.154574132** |
| `symbolalg` | 0.145110410 | 0.156 | 0.145110410 |

Four models agree to **nine decimal places**, and every non-zero row is
*bit-identical between the treatment and the shuffled arm*. That is the
signature of [[2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name]]:
these are not five models partially deriving, they are five models abstaining
onto `structural_fallback`, which is the same table in all three arms. The
correct statement is stronger than the published one:

> **Not one of twenty models produces a single correct derived fill from its own
> machinery.** The 0.038 mean is entirely the shared back-off, and it sits
> *below* the arm's own blind marginal of 0.167.

## Why: it is the hypothesis language, not the search

Every rule-based model here concludes one of two things at a hidden node:

* **a copy** — the label of some node reached by a structural path
  (`copy:peer`, `copy:parent`, a pointer, a retrieval);
* **a constant** — a symbol named outright, or a modal label for a context.

`ilp-001` is genuinely first-order and genuinely induces the *chain*: it will
discover "two steps up and one across" without being told. But the head of its
clause binds `L` to **another node's label**. It is a better search over the
same conclusion space. `ruleinduce-001` enumerates conclusions from a list
somebody wrote down.

The derive arm plants a rule of a third form:

    label(X) = m(label(Y))     Y = the kind sibling, m a finite corpus-wide map

`m` is neither a copy nor a constant. No model in the registry can *state* this
hypothesis, so no amount of search finds it, and the 0.000 column is what the
absence of a syntactic form looks like from the outside. `ilp` scoring exactly
0.000 next to a FOIL search that works is the cleanest evidence available that
the failure is expressive and not procedural.

**A corollary, stated now because it is what makes the result interesting rather
than a floor being matched.** Predicting a symbol that no visible node carries
requires storing an association between symbol identities across episodes. A
renaming-invariant model stores no symbol identities. Therefore *no
renaming-invariant model can score above chance on the derived non-copyable
bucket* — the fifteen 0.000s are a theorem, not a failure, and this is the same
shape as [[2026-08-15-a-floor-outside-the-models-hypothesis-class]]: a floor
outside the class decides the comparison before the run. **Taking this channel
requires being renaming-variant.** That is a cost, and the interesting question
is whether it buys anything a slot-memoriser does not.

## What is being built

`frontier-001`. Batzoglou's loop with the LLM replaced by enumeration, because
the proposal distribution is over a hypothesis space small enough to enumerate
here and because the repo runs on CPU with a real training job on the box.

A hypothesis is `(guard, resolver)`.

* **guard** — a conjunction over symbol-free structural conditions on the target
  (parent type, parent label, slot, depth, sibling count, has-children).
* **resolver** — three forms, and the third is the new expressive power:
  * `copy:P` — the label at structural path `P`. Renaming-invariant.
  * `const` — the modal label under the guard. Memorises a slot.
  * **`map:P`** — a learned finite map from the label at `P` to the answer.
    Memorises a *relation between symbols*.

**The verifier is exact and held out, and this is the load-bearing design
choice.** A map fitted and scored on the same fills verifies at 1.000 by
construction — it is a lookup of the answers. So the training episodes are split
into two folds by index: resolver parameters are fitted on one fold and
precision is measured on the other, both directions, and a hypothesis is kept
only if its **cross-fitted** precision clears its support threshold. Deployment
refits on everything. Without this the model would pass the treatment *and* the
control and prove nothing.

**Residual guidance.** Round 1 proposes guards from all training fills. Later
rounds propose only from fills the current frontier still gets wrong — the
paper's move, and the one that distinguishes this from a single greedy pass.

**Simplification.** Guard literals whose removal does not change training
predictions are dropped; map entries that never fire are deleted. This is the
paper's "compress while preserving predictions" and it is also the MDL tie-break
between two hypotheses of equal precision.

`frontier-001` is registered **beside** everything else. Nothing is edited.

## Pre-registered predictions, and what refutes each

**H1 — the planted rule is recovered.** `acc | derived, not copyable` on
`derive:wordnet` is **≥ 0.80**. *Refuted below 0.50.* It will not reach the
floor's 1.000: under 15% scatter the kind sibling is itself sometimes hidden,
and a map with no input abstains.

**H2 — the control closes it, and this one voids the result.** On
`derive:wordnet-perm` the same model scores **≤ 0.20**, i.e. at or below that
arm's blind marginal (0.143) and back-off (0.178). *If it scores above 0.35, H1
is not a derivation result and nothing here should be read.* The mechanism is
internal and checkable rather than asserted: under a fresh per-episode
permutation the map's held-out precision collapses to ~1/6, the hypothesis fails
verification, it is not kept, and the model abstains. `render()` will print
whether a `map:` hypothesis survived in each arm, so the claim is inspectable
without trusting the score.

**H3 — the open question, and the one nobody can predict.** On the **base**
curriculum, does any `map:` hypothesis survive held-out verification at all?
I do not know, and both outcomes are publishable:

* *nothing survives* → `frontier` degenerates to a guarded copy model, and the
  finding is about the **curriculum**: it contains no cross-episode symbol
  correspondence that survives verification. That is the honest explanation for
  fifteen models scoring 0.000, and it says the derive arm planted the only
  derivable structure in the corpus.
* *something survives* → the induced rules get read before anything is claimed.
  The obvious trap is a lesson-identity leak — a lesson that always uses the
  same predicate symbol makes `map:` a lesson detector, not a derivation. The
  guard is to print the surviving hypotheses and check them by eye.

**H4 — the pooled table cannot move, and this is arithmetic.** The derived slot
is 0.20% of graph positions in 11 of 179 lessons, so pooled `label_acc` cannot
move by more than ~0.003 in either arm however well H1 goes. **A flat pooled row
is not evidence about derivability**, and is being written down here so that it
cannot later be read as one.

**H5 — renaming drops where the map fires and nowhere else.** Permute all
symbols without refitting. Predicted: `frontier`'s drop is large on the derived
bucket (the map is a table over symbol identities) and small elsewhere (the copy
resolvers carry the rest). *Refuted if the drop is uniform*, which would mean
the whole model is a memoriser and the `map:` form bought nothing that `const`
did not.

## What would make all of this true but uninteresting

Named now, per the standing rule:

1. **The floor already gets 1.000.** Matching a one-symbol lookup is not a
   discovery. What is being tested is not "can the channel be walked" — the
   floor settled that — but whether a model *in the sweep, under the same
   contract, fitted the same way, with no knowledge of the derive arm* recovers
   it. If `frontier-001` only works when told where to look, it is a fixture.
   The guard: it is fitted identically on every curriculum and never sees the
   arm name.
2. **A map over six pairs is a small table.** If H1 passes only at six pairs and
   collapses at twelve, the result is about table size and not about induction.
   `notes/questions/2026-08-15-how-many-pairs-can-a-model-here-hold.md` already
   parks the curve; this is the model that makes it measurable.
3. **The rest of the curriculum may not move at all**, in which case `frontier`
   is a one-arm model and should be reported as one.
