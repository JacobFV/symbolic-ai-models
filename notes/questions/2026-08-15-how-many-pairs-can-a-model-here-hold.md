---
date: 2026-08-15
author: agent-derived-slot
status: blocked
related: [2026-08-15-derivability-is-the-treatment-and-the-per-episode-permutation-is-the-control]
---

The derivability arm fixes the map at **six pairs** for a stated reason: the
previous `kg:` arm drew kinds from ~13,810 graph words, which is about ten
training instances per pair and unlearnable at this data scale, so a wider map
would have produced a second null-by-construction — this time by sparsity.

Six is therefore the easiest version of the question, not the interesting one.
The interesting one is the **curve**: register `derive:wordnet-k12`,
`-k24`, `-k60` (an episode still draws six kinds, but from a pool of k, with the
map fixed corpus-wide over the whole pool) and read where the derived-slot
accuracy falls off. That separates "these models cannot use a conditional
dependency between two symbols" from "these models can hold about n of them",
which the single point cannot.

Record the curve, not the argmax —
`notes/lessons/2026-08-14-record-the-curve-not-the-argmax.md`. Each rung needs
its own per-episode-permutation control, and the control's expected score falls
as 1/k rather than staying at 1/6, so the *lift* is the readable quantity and the
raw column is not.


---

**Blocked, 2026-08-17, and the block is the interesting part.** This cannot be
run as written. `DeriveBinder.vocabulary` applies the map only when the slot asks
for exactly as many words as the map holds, and the scene vocabularies are six
words each (`COLORS`, `SHAPES`, imported by 57 lesson modules). Measured: at
width 12 and 24 the kind slot returns the curriculum's own list and the binder
records a fallback, so a widened arm derives **nothing** and scores its baseline.

The curve would have come back flat at every rung and the flat curve would have
been a fact about the binder, not about the models — and nothing in the sweep,
the summary or `derived_split.py` surfaces the fallback count, so it would have
read as a real null. `_check_derive_width` now raises at registration.

The question is still the right one and it is now the derivability result's
biggest remaining threat — six pairs may be about table size rather than
induction. But the real cost is widening `COLORS` and `SHAPES` themselves, which
changes every scene in every lesson and therefore the substrate of every
published number. That is a curriculum-versioning job, not a curriculum-naming
one. See
[[2026-08-17-the-parked-experiment-was-a-null-by-construction-and-nothing-would-have-said-so]].
