---
date: 2026-08-15
author: agent-derived-slot
status: provisional
related: [2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control,
          2026-08-13-a-control-that-could-fail,
          2026-08-15-the-derivable-fill-is-worth-0833-to-a-lookup-and-nothing-takes-it,
          2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property]
---

# Ship the control with a floor that separates the arms, or a null is unreadable

## The gap this closes

[[2026-08-13-a-control-that-could-fail]] says build the condition under which the
signal cannot exist. [[2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control]]
adds the mirror failure: a control so strong the treatment cannot win either,
because the two are one problem relabelled.

Both are rules about *design*. Neither leaves anything behind in the artefacts.
When the semantic-constraint arms came back flat, four sweeps and a curriculum
had established a number that was derivable from the design — and the run
directories, the tables and the write-up were **identical to what a real null
would have produced**. The pre-registration had called the risk in advance, which
is the only reason the null was read correctly, and that is a prose defence
rather than a measured one.

## The guard

> **Every arm should ship with a predictor, weaker than any model in the sweep,
> whose score is high in the treatment and at chance in the control.** Compute it
> from the same episodes, the same masking regime and the same bucket the models
> are scored on, and print it in the same table. Its separation is the
> experiment's *measured* power, and it is a precondition on reading anything
> else — not a footnote.

For the derivability arm that predictor is the **derivation floor**: the
commonest value seen in *training* for this kind, read off the visible sibling
node. A lookup table with no reasoning in it. It scores **1.000** in
`derive:wordnet` and **0.169** in `derive:wordnet-perm`, on the same 1,345 fills.
That one row is what turns "twenty models scored the same in both arms" from an
uninterpretable flat table into a finding about the models: the channel was open,
it was worth 0.833, and nothing took it.

Had that row come back 1.000 against 1.000, or 0.17 against 0.17, the correct
report would have been "no experiment took place" — and it would have been
readable off the artefact by anyone, a year later, without reconstructing the
argument.

## Two corollaries worth stating separately

**Ship the *blind* version of the floor too.** The same lookup with the
conditioning term dropped is the arms' marginal, and it is the only way to see
whether the arms differ in the conditional or merely in the distribution of the
answer. Here it caught a real asymmetry the design could not remove — 0.167
against 0.143, because a value that is a fixed function of the kind inherits the
kind's frequency while a permuted one is uniform. Small next to 0.833, pointing
against the treatment, and it would have been invisible without the row.

**A floor that scores 1.000 is not a broken floor.** The instinct is to weaken it.
It is doing its job: it says the answer is fully determined by information the
models are given, so any shortfall is theirs. Weakening it to make the table look
more interesting would delete the only evidence that the experiment happened.
