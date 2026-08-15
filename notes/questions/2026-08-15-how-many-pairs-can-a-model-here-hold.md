---
date: 2026-08-15
author: agent-derived-slot
status: idea
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
