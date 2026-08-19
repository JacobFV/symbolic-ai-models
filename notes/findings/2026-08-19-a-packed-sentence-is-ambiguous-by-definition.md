---
title: A packed sentence is ambiguous by definition
date: 2026-08-19
status: measured
arm: packed-surfaces
---

## The constructive half of the Wikipedia result

Real prose puts several claims in one sentence; none of the generated surfaces
ever did. So each generator now takes a **`packed`** option that renders two
claims as one sentence — *"group owns sub_0, which reported 105.87 USD, filed 29
May 2026"*, *"machine_0 is set up for cut and has 5.51 hours available"* — with a
**span for each claim over the same text**. Default `False`, so every published
number keeps its meaning.

| domain | packed | ambiguity mass | accuracy | floor |
|---|---|---:|---:|---:|
| solvency | no | **0.000** | 1.000 | 0.567 |
| solvency | **yes** | **0.741** | **0.567** | 0.567 |
| scheduling | no | **0.000** | 1.000 | 0.658 |
| scheduling | **yes** | **0.279** | **0.658** | 0.658 |

**Both readers collapse to their floor, exactly.** They stop answering and start
guessing: solvency returns one constant verdict on every case, and scheduling
loses half the floor's capabilities so every instance reads infeasible.

## The mechanism is the branch, and it is visible in one diff

`read_signature` branches on shape with an `elif` chain. A packed sentence matches
the **first** branch and the second never runs. Scheduling, seed 0:

```
unpacked  has_capability [(machine_0, cut), (machine_0, weld),
                          (machine_1, cut), (machine_1, paint)]
packed    has_capability [(machine_0, weld), (machine_1, paint)]
```

The capacities are all still there. The packed capability is **silently dropped**,
which is the unsound direction — an infeasible floor reading as feasible is what
that channel does, and here the loss runs the other way and refuses schedules that
exist.

## And the audit predicts it, offline, which it has not managed all day

Ambiguity mass goes **0.000 → 0.741** and **0.000 → 0.279** before any reader runs,
and it ranks solvency as the worse case, which is what the packed share of its
claim spans says. That is the first thing today the instrument gets **ahead** of —
it could not predict which channels are erroneous, nor vocabulary fragility, nor
real-prose determinacy.

It gets ahead of this one because packing is the thing the audit is *about*, and
that is worth stating as a theorem rather than a measurement:

> **A signature is a function of the sentence.** If a sentence realises two claim
> kinds, its signature maps to both, so it is ambiguous by definition and
> `ambiguity_mass` is bounded below by the share of multi-claim sentences.
> **No signature reader can be packing-robust**, and real prose is packed.

That closes the loop from the Wikipedia finding: the sentence is the wrong unit
*and* the signature is defined on it.

## Flood is the control, and the reason is a design rule

Given one sentence carrying a road **and** its limit, `read_content_roles` recovers
both kinds. It survives because at that point it is **not** signature-based: it
writes crossings into a dict and later folds them into links, rather than choosing
a branch.

> **Accumulate, do not branch.** A reader that assigns into per-kind stores can
> take several claims from one sentence; a reader that selects one branch per
> sentence cannot, and no amount of signature refinement changes that.

That is the actionable rule this whole line produces, and it is a property of the
reader's control flow — which is exactly what the audit is blind to, so the two
results sit either side of the same boundary.

## What would refute this

- Two domains packed, one pairing each. A different pairing — one whose union
  signature is *not* shared with another kind — might survive, and that would
  sharpen the theorem into a statement about *which* packings hurt.
- Both accuracies land exactly on their floors, so accuracy cannot discriminate
  between them; only the mass does. The claim that the audit *ranks* them
  correctly rests on 2 points.
- The flood control is one hand-written packed sentence, not a surface option.
