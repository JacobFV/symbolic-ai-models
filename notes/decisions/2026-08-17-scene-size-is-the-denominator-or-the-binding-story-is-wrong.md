---
date: 2026-08-17
author: lead
status: preregistration
related: [2026-08-16-premise-selection-is-free-inside-the-object-and-costs-0714-outside-it,
          2026-08-16-four-arms-and-none-of-the-headline-mechanisms-transferred,
          2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary]
---

# If argument binding is the residual, accuracy at whole-graph scope is 1/k in the scene's own object count

## The claim being tested

The premise-selection arm found that at whole-graph scope the exact lookup picks
a *kind label* on 99.9% of positions and the **right object's** kind on 23.3%.
23.3% is close to 1/4 and there are four objects in a scene, so the reading
written down was: the selector identifies what sort of fact answers the
question and then binds it to the wrong entity, uniformly at random among the
objects present.

That reading rests on one coincidence between two numbers. It deserves better
than a coincidence, and there is a way to get it without generating anything.

## Why not the experiment the note proposed

The follow-up question note proposed widening scenes to eight objects and
predicting the whole-graph rung moves to ~1/8. That is a curriculum change: new
episodes, a new fingerprint, and a population not comparable with any published
row — a lot of machinery to buy **one more point** on a line.

**The scene size already varies across the episodes that exist.** So the same
prediction can be read as a *curve* over the current data, at no generation cost
and on exactly the published population. A curve over five values of `k`
discriminates far better than two points, and
`notes/lessons/2026-08-14-record-the-curve-not-the-argmax.md` is the standing
argument for preferring it.

## The prediction, before the number

Let `k` be the number of **visible** nodes carrying a kind label in the episode
— the selector's effective choice set among premises of the right sort.
Restricted to the derived, non-copyable bucket at whole-graph scope:

1. **`picked_kind` — the share of positions where the selector picks the right
   object — is ≈ 1/k, falling monotonically in `k`.**
2. **Accuracy tracks it**, since picking the right object's kind is what makes
   the lookup right.
3. The **object-scoped** rung stays at ≈1.000 **for every `k`**, because
   restricting to the object's own children removes the choice entirely.
4. In the `-perm` control every row is flat in `k` near the blind marginal —
   there is nothing to bind to, so binding cannot be what is failing.

## What refutes it

- **`picked_kind` flat in `k`.** Then 23.3% is not 1/k, the uniform-wrong-object
  story is a coincidence between two numbers, and the residual is something
  else — most likely a fixed subset of scenes the selector always fails.
- **`picked_kind` falling but far from 1/k** (say 1/2k, or 1/k²). Then binding is
  involved but is not uniform, and the mechanism needs restating.
- **The object-scoped rung falling in `k` too.** Then scope is not what is
  buying 1.000 and the ladder's middle rung was measuring something else.

Any of those would also weaken the reinterpretation of `frontier-001` this line
implies — that its `[slot=1, nsib=4]` guard is buying *scope* rather than the
map. `nsib=4` is a scene-size condition, so if `k` does nothing, that reading
loses its mechanism.

## Bound before it starts, which is why it is cheap

Both ends are published: 1.000 told the premise, 0.167 blind, 0.286 whole-graph
pooled. Any curve has to average to 0.286 over the observed distribution of `k`,
so the arm cannot come back with a number that is unanchored — and if it does,
that is a bug in the binning rather than a finding.


---

## Amendment, written after the curve and before the next run

The curve refuted prediction 1, and finding out *why* refuted the arm's own
reading as well. Recording both here rather than opening a third note, because
it is one experimental line and the second prediction has to be on the record
before its number lands.

**What the curve said.** `picked_kind` at whole-graph scope, derived and not
copyable, by the count `k` of visible kind-label nodes:

| k | n | picked the right object | 1/k | acc |
|---:|---:|---:|---:|---:|
| 2 | 31 | **0.355** | 0.500 | 0.355 |
| 3 | 121 | 0.298 | 0.333 | 0.298 |
| 4 | 216 | 0.264 | 0.250 | 0.287 |
| 5 | 173 | 0.260 | 0.200 | 0.283 |
| 6 | 66 | 0.258 | 0.167 | 0.273 |

It falls with `k` and is nothing like `1/k` — **below** chance at `k=2` and
**above** it at `k=6`, converging to ~0.26 regardless of scene size. Refutation
condition 2 fired: binding is involved and is not uniform. The 23.3% ≈ 1/4 was a
coincidence between two numbers, exactly as feared. Prediction 3 held exactly —
the object-scoped rung is 1.000 at every `k`.

**Why, and it is not a tie-break.** First hypothesis: all six kind labels have a
purity-1.000 map, so every candidate ties and the positional tie-break decides.
Measured and false — the selector picks the lowest-indexed kind node only 0.346
of the time, and the purities are not 1.000. They are:

    auto 0.333   body 0.322   building 0.292
    garment 0.371   ship 0.326   shoe 0.341

A deterministic bijection fitted correctly gives **1.000**. These are the
marginal. `fit_selector` at `scope="graph"` credits *every visible label in the
episode* with the derived value, so `ship`'s counter accumulates the values of
every other object in every episode `ship` appears in.

**So the middle rung changes two things at once** — the candidate set at
inference *and* the pool the table was fitted over — and attributes the whole
gap to the first. It is not measuring how hard premise selection is. It is
measuring a selector whose table cannot express the relation it is selecting
among. Same family as
[[2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control]]:
a readable-looking number produced for a reason other than the one claimed.

## The isolated arm, and its prediction

Fit at **object scope** (the correct bijection, purity 1.000) and read at
**whole-graph scope**. Only the inference-time candidate set varies, so the
representation is held fixed and what is left is selection alone.

| fit | read | number |
|---|---|---|
| object | object | 1.000 (published) |
| **object** | **graph** | **the experiment** |
| graph | graph | 0.286 (published — confounded, per above) |
| — | — | 0.167 blind (published) |

**Prediction.** With the correct table every kind label scores ~1.000 and every
non-kind label scores near the marginal, so the six kinds tie and the positional
tie-break decides among them. Accuracy should land **near 1/k**, i.e. pooled in
the region of **0.25–0.35**, and `picked_kind` should this time track `1/k`
closely — because now the ties are real.

**What refutes it.** Landing near **1.000** means the correct table makes
selection trivial and CoTu's residual does not reproduce here at all. Landing at
**0.167** means even a perfect table cannot be aimed and the arm is a null.
Either would be a cleaner answer than the confounded 0.286, which is the point.

**And this is the number that decides the `frontier-001` reinterpretation.** If
object-fit/graph-read is near 1.000, scope is worth nothing once the
representation is right, and `frontier-001`'s guard is not buying scope — the
map is doing the work after all.
