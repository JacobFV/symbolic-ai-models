---
date: 2026-08-15
author: agent-derived-slot
status: provisional
related: [2026-08-14-semantic-constraint-from-a-knowledge-graph,
          2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control,
          2026-08-15-the-kg-arms-are-a-null-and-the-quarter-that-mattered-did-not-move,
          2026-08-14-preregistering-the-curriculum-arms,
          2026-08-13-a-control-that-could-fail,
          2026-08-14-the-label-score-is-a-copy-score]
---

# Derivability is the treatment; a per-episode permutation of the same map is the control

Written before any arm ran. It fixes what each number would have to be for the
result to be readable, because the line this replaces produced a null that no
artefact could distinguish from no experiment at all.

## What was wrong with the last arm, in one sentence

It **re-labelled** the curriculum: where the generator drew `rng.choice(COLORS)`
it drew a KG-consistent colour instead, so an object became a *penguin* that is
*black* rather than a random object that is *purple*. The answer sat in the same
place, reachable by the same route, requiring the same operation. A
degree-preserving edge scramble then produces a different but equally consistent
naming, and a learner whose only input is this corpus sees an isomorphic
problem. The control tied at mean −0.0013 and **could not have done anything
else**. See
[[2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control]].

## The channel test, applied before building

> Is there any channel by which the treatment could reach this learner that the
> control does not also carry? Name the channel.

**Treatment (`derive`).** An object's attribute slot is not drawn at all. It is
*determined* by that object's kind through a fixed, corpus-wide map taken from
the graph: `pigboat --has-part--> anchor`, so a pigboat object's attribute is
`anchor` in every episode of the corpus. The channel is the **cross-episode
co-occurrence of two symbols in one term**. A model that saw `pigboat/anchor` in
training can name a hidden `anchor` at evaluation from the visible `pigboat`
beside it.

**Control (`derive-perm`).** The same six kinds, the same six values, the same
bijection — composed with a **fresh uniform permutation of the assignment in
every episode**. Within an episode the attribute is still a deterministic
function of the kind; across episodes it is noise. The channel named above is
**absent**, and nothing else is: the value multiset per episode is identical, the
collision structure is identical (a bijection composed with a permutation is a
bijection), so the copyable share, the marginal distribution of every symbol and
the scene statistics are identical by construction.

That is a control that can fail, and the size of the failure is predictable:
a learner that has the treatment's map scores at most **1/6** under the control,
because a uniform permutation agrees with the corpus map at a given kind with
probability 1/6.

**Isomorphism check (`derive-shuffled`).** The same six kinds, values taken from
the *scrambled* WordNet — a different but equally consistent map, still
corpus-wide. **This is predicted to tie with the treatment, and the prediction is
made here rather than after the fact.** For a learner with no outside knowledge
of English the two are the same problem under a relabelling of six words; the
only residual channel is the morphology of those six lemmas. It is run as a
*measured check of an argument*, not as a load-bearing control, and a tie is not
evidence about semantics.

## Why the map is six pairs and not thirteen thousand

The previous arm anchored a different family in every episode, so the kind
vocabulary was drawn from ~13,810 graph words. A map over that vocabulary is not
learnable from ~1,700 training instances, and an arm built on it would have been
a **second** null by construction — this time by data sparsity rather than by
isomorphism. The map is therefore fixed corpus-wide at six kinds and six values,
selected from the graph by a stated rule, so that the question asked is "can
these models use a conditional dependency between two symbols at all" and not
"can they memorise thousands of pairs from ten examples each".

The consequence is that this arm is **not** a bigger-vocabulary arm. `derive`
and `derive-perm` share every word in the corpus; they differ only in whether
the kind→value assignment is the same one twice.

## What the measurement has to be, and why the pooled table cannot be it

`label_acc` is 72% a copy score, and the derived slot is a **sub-population**:
the seam `bind_scene` reaches 12 of 179 lessons and **236 of 85,459 graph
positions (0.28%)** on eight training seeds — measured before any model was
built, see the coverage finding. So:

> **The pooled 179-lesson `label_acc` cannot move by more than about 0.003 even
> if the derived slot goes from 1/6 to 1.00.** A pooled null is therefore not a
> result about derivability, and reporting one as such would be the coverage
> error the decision note's rule 4 already warned about.

The reported statistics, in order of what they decide:

1. **`acc | derived, not copyable`** — the population the treatment acts on,
   with the answer nowhere visible. This is where the arms must separate.
2. **`acc | derived`** — the same population including the copyable fills, where
   both arms have an in-episode route and are expected to be close.
3. **`acc | not copyable`** over all 179 lessons — comparable with the previous
   arm's table, expected flat, reported so the dilution is visible rather than
   argued.
4. **pooled `label_acc`** — reported last and expected flat, for the reason above.

n is bought by averaging over **many masking draws of the same evaluation
episodes**, at the same 15% scatter rate the models were trained under, not by
masking the derived positions specially: an evaluation regime the models never
saw would confound the arms with a distribution shift.

## Floors, refitted, and one new one

Floors and the copy ceiling are properties of a curriculum and are refitted per
arm, never carried across. Two floors matter here:

* the **structural floor** (`task.split_floor`) sees `(parent type, slot, depth,
  arity, sibling type)` and no symbol, so on the derived slot it is the same in
  both arms — about 1/6, the marginal of a six-word list. A model beating it on
  the derived bucket in `derive` and not in `derive-perm` is the result.
* the **derivation floor**, new and reported separately: the commonest value seen
  in *training* for this kind, applied to the visible sibling kind. It uses more
  than the structural floor does, on purpose — it is the score of a lookup table
  with no reasoning in it, and it is the number a model has to reach before
  anything here is about inference. Predicted ~1.00 under `derive` and ~1/6
  under `derive-perm`. If the two arms do not separate *on this floor*, the
  curriculum is broken and no model number should be read.

## What would mean the control still cannot fail

Stated now, so it cannot be decided after the numbers land:

* **The derivation floor does not separate the arms.** If a kind-conditioned
  lookup gets the same score in `derive` and `derive-perm`, then the channel this
  design claims to open is not open, and every model number is uninterpretable.
  This is the precondition, and it is checked before anything else is read.
* **Every derived fill turns out to be copyable.** If another object of the same
  kind is almost always visible with its value, the answer is available
  in-episode in both arms and the two must tie. Reported as the copyable share of
  the derived bucket, per arm; the arms are matched on it by construction, so a
  high share is a statement about the experiment's power, not a difference
  between arms.
* **n on the derived, non-copyable bucket is under ~200.** Then a difference of
  the size at stake is inside the noise and the arms are not separable whatever
  they show.

If any of those holds, the honest report is "no experiment took place", which is
what the last one should have said.

## What would refute the treatment's *interest* rather than its validity

* **Every model scores 1/6 in both arms.** Then a conditional dependency between
  two symbols in one term is outside every hypothesis class in the registry, the
  derivation floor is another
  [[2026-08-15-a-floor-outside-the-models-hypothesis-class]], and the finding is
  about the models rather than the curriculum. This is a real possibility and
  would be a publishable negative: the exactly-equivariant models
  (`vsa_pure-002`, `routes-001`, `corefer-001`) **cannot** represent
  `pigboat→anchor` at all and are predicted to score 1/6 by construction, which
  is itself a prediction this arm can check.
* **`derive` and `derive-shuffled` separate.** Would mean something reads the
  lemma strings; it would be the first evidence in this repo that any model here
  brings outside knowledge of English. Predicted not to happen.

## Rejected

* **A per-episode KG family with a global map.** Rejected: unlearnable at this
  data scale, a null by sparsity.
* **A corpus-wide permutation as the control** (same words, assignment permuted
  once for the whole corpus). Rejected because it is *provably* the treatment
  relabelled — the exact isomorphism the last arm died of — and running it would
  spend a sweep to re-derive an argument.
* **A dedicated mask mode that hides derived slots.** Rejected: the models are
  trained at 15% scatter and evaluating them at a rate and shape they never saw
  confounds the arms with a regime change. More draws of the same regime buys the
  same n with none of that.
* **Widening `bind_scene` to the other colour/shape sites.** 965 of the
  curriculum's graph positions have a colour and a kind under one parent and only
  236 are reachable through the existing seam, so hooking the rest would roughly
  quadruple coverage. Rejected *for this arm* because it edits vendored
  generators in seven more places while the question is whether the mechanism
  works at all, and n is sufficient without it. Recorded as a question note.
* **CSKG rather than WordNet.** Its `property` relation is the semantically right
  one ("a lemon is sour") and its values under a deterministic selection rule are
  noise (`chair → alcoholism`), while WordNet's `part` gives `monastery → annex`,
  `pigboat → anchor`. WordNet is also the graph the published arms already use.
