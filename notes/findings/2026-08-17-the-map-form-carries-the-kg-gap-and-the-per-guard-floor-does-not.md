---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-a-known-null-is-the-cheapest-test-of-a-permissive-floor,
          2026-08-17-the-per-guard-floor-keeps-the-channel-and-drops-the-chosen-constant,
          2026-08-15-the-kg-arms-are-a-null-and-the-quarter-that-mattered-did-not-move,
          2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control]
---

# A model with no `map` rules shows exactly zero gap on the null arms, and the per-guard floor is not the thing that does

Pre-registered in
[[2026-08-17-a-known-null-is-the-cheapest-test-of-a-permissive-floor]]. The
`frontier-008` finding named its own open weakness — the per-guard floor is each
guard's `const` precision, and a guard whose answers are merely *noisy* looks
identical to one whose answers are structured but not modal. The `kg:` arms are
the cheapest test that exists for it: `kg:wordnet` and `kg:wordnet-shuffled` are
one problem under a relabelling, so anything found between them is definitionally
noise.

## The verdict on the weakness: not detected

`acc | not copyable`, the column the whole `kg:` line was decided on:

| model | precision floor | `map` form | level (`kg:wordnet`) | `-shuffled` | **gap** |
|---|---|---|---:|---:|---:|
| `frontier-nomap` | global 0.5 | **none** | 0.072 | 0.072 | **+0.000** |
| `frontier-001` | global 0.5 | yes | 0.285 | 0.276 | +0.009 |
| `frontier-003` | global 0.5 | yes | 0.285 | 0.273 | +0.012 |
| `frontier-008` | **per guard** | yes | 0.326 | 0.308 | +0.018 |

The pre-registered refutation was *"a gap for `-008` where `-001` has none"*. It
did not happen. `frontier-003` carries the **same global floor** as `-001` at the
**same level** and shows +0.012, so a gap of this order exists without the
per-guard floor at all; `-008`'s +0.018 is close to what level-scaling from
`-003` predicts (0.012 × 326/285 = 0.0137). **The per-guard floor is not
distinguishable from the global one here.**

Fifteen published models on the same column: mean **−0.0013**, sd 0.0057, and the
highest non-copyable level among them is `grammar-001`'s 0.168 — half the
frontier family's. So the published spread cannot settle this on its own, which
is why the family comparison at varying level is the measurement and the
published row is only the scale.

## What the family comparison did find

**`frontier-nomap` has a gap of exactly 0.000, at three decimal places, on both
halves.** It is the one member of the family with no symbol-keyed `map` rules. So
within this family the gap is carried entirely by the `map` form, and it grows
with how much of the score the maps are producing: 0.072 → 0.000, 0.285 →
0.009/0.012, 0.326 → 0.018.

That has an ordinary explanation and it is worth stating because it slightly
qualifies a published claim. The two `kg:` arms are isomorphic **structurally** —
a degree-preserving scramble of a fixed graph is a fixed graph — but they are
built from **different words**, so their lexical statistics differ. A rule keyed
on symbol identity is exactly the component that can notice that; a structural
rule cannot. The isomorphism argument covers structure and does not cover the
lexicon.

**It is not as simple as "vocabulary-dependent models show a positive gap",
though, and that is the honest limit.** `grammar-001` (−0.009), `ngram-001`
(−0.005) and `brill-001` (−0.010) are the three most renaming-variant published
models and all three are *negative*. So symbol-keyed-ness is not sufficient for a
positive gap, and what distinguishes the frontier maps from those is not
established here.

## My pre-registration quoted the wrong column, and that is the second time today

Prediction 1 said `frontier-008`'s gap should be *"≤ 0.005 in absolute value —
the same region the twenty published models occupy (mean −0.0013)"*. The
`−0.0013` is the **non-copyable-quarter** mean; I attached it to a **pooled
`label_acc`** threshold. The published pooled mean is **+0.0041** with two models
over 0.010, which is a different distribution entirely, and my threshold was
therefore not the one the published work would have set.

That is the same mistake as the `_offer` conflation earlier today — reading a
number from the wrong column of a table I had in front of me — and it is twice in
one day. Both times the number was real and published; both times I attached it
to the wrong quantity. A reference figure needs its column named when it is
quoted, not just its value.

Incidental, and a small confirmation: recomputing the pooled gap over the same
fifteen models by an independent path gives **+0.0040** against the published
**+0.0041**.

## What this cannot show

A null result from a control is weaker than a failure. The `kg:` arms are a null
*by construction*, so they cannot distinguish "the per-guard floor is
well-behaved" from "this arm has too little structure for any floor to over-fit".
An arm with known noise of a *chosen* magnitude would settle it and does not
exist here. The weakness the `frontier-008` finding named against itself is
therefore **untriggered, not disproved**, and its note should keep saying so.
