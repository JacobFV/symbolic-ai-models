---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-scene-size-is-the-denominator-or-the-binding-story-is-wrong,
          2026-08-16-premise-selection-is-free-inside-the-object-and-costs-0714-outside-it,
          2026-08-16-four-arms-and-none-of-the-headline-mechanisms-transferred,
          2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control]
---

# The uniform-binding story was right, its evidence was not, and the confound was worth 0.023 of a 0.833 gap

Pre-registered in
[[2026-08-17-scene-size-is-the-denominator-or-the-binding-story-is-wrong]],
including the amendment written after the first curve and before the second run.
Same population as the published rungs — 1,345 derived fills, 11 carrying
lessons, 8 draws, reconstruction gated on reproducing all 7 published floors bit
for bit.

## The ladder, with the rung that was missing

`acc | derived, not copyable`. `fit` is the scope the lookup table was built
over; `read` is the candidate set at inference.

| rung | fit | read | acc | picked the right object |
|---|---|---|---:|---:|
| oracle premise | — | told | **1.000** | 1.000 |
| object-scoped | object | object | **1.000** | 1.000 |
| **isolated selection** | **object** | **graph** | **0.309** | **0.258** |
| published middle rung | graph | graph | 0.286 | 0.233 |
| blind | — | none | 0.167 | 0.000 |

## What was wrong with the published middle rung

It varied **two** things and attributed the gap to one. `fit_selector` at
`scope="graph"` credits *every visible label in an episode* with that episode's
derived value, so `ship`'s counter accumulates every other object's value too.
The six kind labels come out at purity **0.29–0.37** where a deterministic
bijection fitted correctly gives **1.000**:

    auto 0.333  body 0.322  building 0.292  garment 0.371  ship 0.326  shoe 0.341

So the rung was not measuring how hard selection is. It was measuring a selector
whose table could not express the relation it was choosing among — the family of
[[2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control]], a
readable-looking number produced for a reason other than the one claimed.

**The confound was worth +0.023 of a 0.833-wide gap.** That is the useful part
of the correction: the confound was real, it was found by a prediction failing,
and it was *small*. The published reading survives its own broken evidence.

## The scene-size curve, which is what separated them

`picked the right object`, by the count `k` of visible kind-label nodes:

| k | n | published rung (graph fit) | **isolated (object fit)** | 1/k |
|---:|---:|---:|---:|---:|
| 2 | 31 | 0.355 | **0.516** | 0.500 |
| 3 | 121 | 0.298 | **0.355** | 0.333 |
| 4 | 216 | 0.264 | **0.292** | 0.250 |
| 5 | 173 | 0.260 | **0.237** | 0.200 |
| 6 | 66 | 0.258 | **0.227** | 0.167 |

The published rung's curve is **flat** — below chance at `k=2`, above it at
`k=6`, converging to ~0.26 whatever the scene size. That refuted the original
prediction, and the original reading of 23.3% ≈ 1/4 was a coincidence between
two numbers.

The isolated rung **tracks 1/k at every point**, within 0.02–0.06 and with a
small consistent positive offset. So:

> **The uniform-wrong-object story is correct, and it only becomes visible once
> the representation confound is removed.** The published claim was right for the
> wrong reason, and the curve that refuted its evidence is the same curve that
> confirmed its conclusion.

## The controls

In `derive:wordnet-perm` the isolated rung sits at **0.167** — exactly 1/6, the
number the arm's own design says every rung must show when there is nothing to
select for — with `picked the right object` at 0.050 and falling to 0.000 by
`k=6`. The object-scoped rung holds **1.000 at every `k`** in the treatment,
which is prediction 3 of the pre-registration and the check that scope, not
something else, is what buys the top rung.

## What this settles, and what it does not

**CoTu's residual reproduces here.** Hand the deduction a provably perfect table
— the bijection, purity 1.000, verified — and a selector reading the whole
episode still scores **0.309** against **1.000** when told which node to read.
The 0.691 between them is selection alone, with representation held fixed. That
is the claim, and it is now measured rather than inferred from a confounded row.

**It does not rescue `frontier-001` from the reinterpretation.** The falsifier
named in the pre-registration was "if object-fit/graph-read is near 1.000, scope
is worth nothing once the representation is right". It is 0.309, so scope is
worth 0.691 even with a perfect table, and the reading that `frontier-001`'s
`[slot=1, nsib=4]` guard is buying scope rather than the map **stays live**. The
next thing to run is the direct version: ablate the guard's scope conditions and
keep the map.

**What would make this uninteresting.** The whole ladder lives on 1,345 fills in
11 of 179 lessons — 0.20% of graph positions. It is the entire derived
population rather than a slice of it, but it is a narrow instrument, and nothing
here says selection is the residual anywhere else in the curriculum.
