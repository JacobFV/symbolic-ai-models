---
title: Hypothesis size was the wrong variable — dependency is
date: 2026-08-19
status: measured
arm: hypothesis-size-curve
---

## The claim being tested is my own

[[2026-08-19-refusing-to-collapse-costs-nothing-and-flags-every-error]] ended on
a general statement: **ambiguity is cheap to carry when the hypothesis about it
is small.** It rested on one comparison — unbounded role permutation was sound
and vacuous (72 worlds, 0.0% decided), bounded at-most-one-spurious-link was
sound and free.

Those two differ in the claim **kind** as well as the bound. The variable was
confounded and the principle was not earned.

## Varying only the bound

Same domain, same reader, same collision — flood's `depot`/`flooded`/`needs`
assignment, the one measured vacuous — with candidates enumerated within `k` role
reassignments. `hard_distractors` off, so the phantom-link failure cannot
confound a measurement about roles.

| k | worlds/case | soundness | decided |
|---:|---:|---:|---:|
| 0 | 1.0 | 0.433 | 1.000 |
| 1 | 3.6 | 0.867 | **0.067** |
| 2 | 6.2 | 0.867 | 0.067 |
| 3 | 10.5 | **1.000** | **0.017** |

**Decidedness collapses at the first step.** 1.000 → 0.067 going from k=0 to k=1,
and soundness does not reach 1.000 until k=3, where 1.7% is decided. There is no
useful middle, and the earlier vacuity result is the *limit* of a curve that was
never usable anywhere along it.

The principle is wrong as stated. I gave it 0.45 confidence and wrote that this
was the experiment that could embarrass it.

## What the variable actually is

**Dependency, not hypothesis size.**

A spurious **link** is often inert: the network has other paths, so adding or
deleting one edge frequently leaves the answer unchanged. A misassigned **role**
is never inert — it moves the depot, the destination, or the flooding, and the
answer depends on every one of them.

## The instrument already knew, and I did not connect it

The audit's **collision cost**, measured a few commits earlier from the world and
the surface with **no reader**:

| collision | collision cost | carrying it |
|---|---:|---|
| bridge_on + link | **0.000** (nothing permutable) | free — 0.383 decided at soundness 1.000, giving up nothing |
| depot + flooded + needs | **0.625** | vacuous — 0.067 decided |

That is the predictive relationship, and it is a **second use for the
instrument**: collision cost, computable offline before any reader exists,
predicts whether emit-rather-than-collapse will be usable on a given ambiguity.
Cheap collision → carrying is free. Expensive collision → carrying is vacuous.

The corrected statement: **carried ambiguity is cheap exactly when the ambiguous
kind has low collision cost** — which is a measurable property of the domain, not
a property of how the hypothesis is phrased.

## One honesty note on the baseline

`k = 0` reads 0.433 soundness, where `read_signature_roles` scores 0.000
interleaved on the headline population. Two differences: this is the pooled
population including empty answers, and the `k = 0` assignment is a **repaired**
version of the reader's output — regions it silently dropped are defaulted to
`flooded`, which is what a reader forced to commit would say. So the k=0 row is a
slightly *better* baseline than the reader itself, which makes the collapse from
k=0 to k=1 a conservative reading rather than a flattering one.

That drop-and-lose behaviour is itself worth recording: collapsed, this reader
sends every lone region to `needs`, and because `needs` is single-valued it keeps
the first and **discards the rest entirely**. Its own world does not carry the
candidates at all, which is why the enumeration has to go back to
`signature_readings` for them.

## What would refute the corrected version

A domain where a low-collision-cost ambiguity is nonetheless vacuous to carry, or
a high-cost one cheap. Scheduling and solvency both audit at zero collisions, so
neither can test it — the corrected principle currently rests on **two points in
one domain**, which is exactly the weakness that sank the first version. It
should be labelled as such until a third domain with a real collision exists.
