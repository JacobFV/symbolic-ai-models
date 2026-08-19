---
title: A value error silences rather than fabricates
date: 2026-08-19
status: measured
arm: noisy-registry
---

## Testing the limit I stated on my own component

`render.uncorroborated` flagged **88 of 88** false citations, and I named the
limit in the same breath: recall is 1.000 only because no reader error there lands
on a **value**, and what prevents that is flood's `VALUE_REGISTRY` — whose own
docstring calls its sets *"the generator's own draw sets, unusually clean; a real
registry would be noisier and would overlap"*.

So overlap them. `NOISY` lists every capacity value as a possible mass, so the
vocabularies stop being disjoint exactly where the reader relies on disjointness.
`EMPTY` removes value knowledge altogether.

| registry | accuracy | citations | false | flagged | **marker recall** |
|---|---:|---:|---:|---:|---:|
| clean (published) | **0.673** | 2,266 | 88 | 0.075 | **1.000** |
| overlapping | **0.189** | 1,452 | 27 | 0.061 | **1.000** |
| none | **0.000** | 280 | 27 | 0.361 | **1.000** |

*false by predicate: clean `link` 61, `flooded` 14, `depot` 13 · overlapping
`flooded` 14, `depot` 13 · none `flooded` 27*

## The prediction was wrong, and the reason is the finding

I predicted the marker's recall would fall to 0.5–0.8 as value fabrications
appeared. It stays at **1.000** in all three, and no `mass` or `capacity`
falsehood appears at any registry.

**A value error does not fabricate; it silences.** A mis-slotted mass makes a
vehicle fail to qualify, so no route is computed, so nothing is cited about it.
Citations fall 2,266 → 1,452 → 280 as the registry degrades, and the `link`
fabrications vanish with them — 61 → 0 → 0 — not because the reader got better but
because it stopped answering.

That was the refutation condition I wrote down before running: *"a mis-slotted
mass may simply make the answer empty rather than wrong-with-a-citation."* It is
what happened, and it is a property of how the flow **uses** a value — as a
qualification test rather than as a routing input.

## Two numbers worth keeping

**The value registry is worth the entire capability on the honest surface:
0.673 → 0.000.** It had only ever been priced as a *ceiling* on the easy surface.
Every flood number in this repo rests on a vocabulary of eleven numbers being
exactly right, and nothing measures what a realistic one would cost.

**Fabrication counts fall as capability falls.** 88 → 27 → 27 false citations
while accuracy goes 0.673 → 0.189 → 0.000. A count of falsehoods per explanation
is confounded by coverage: the most broken reader here fabricates least in
absolute terms because it says almost nothing. Per citation it is 0.039 → 0.019 →
0.096 — not even monotone. **Report fabrication against coverage or not at all.**

## What this does and does not settle about the marker

It settles that the marker's recall is robust to the *value* channel, for a
better reason than the one I assumed: that channel cannot produce a false citation
in this pipeline.

It does **not** settle the general limit. A domain whose values are routing
*inputs* rather than qualification *tests* — a cost to minimise, a capacity to
divide — would carry a mis-read value straight into the answer and into the
citations, and the marker would miss it silently because it marks values
corroborated.

## What would refute this

- One domain, and the mechanism is specific to it. The claim to carry is the
  conditional: *values that gate qualification silence; values that feed the
  computation fabricate.*
- `EMPTY` reaching 0.000 accuracy makes its 27 false citations hard to interpret;
  they come from the 280 citations of answers that are all wrong.
- The overlapping registry is one perturbation, chosen to break the mass/capacity
  distinction the reader depends on. A registry noisy in the demand set would
  break a different thing.
