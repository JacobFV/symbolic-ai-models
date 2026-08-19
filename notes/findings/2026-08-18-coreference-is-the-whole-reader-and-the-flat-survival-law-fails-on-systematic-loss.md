---
title: Removing coreference takes the reader from 1.000 to 0.000 while global recall only falls 1.000 → 0.895 — and the flat survival law cannot express that, because real readers lose systematically
date: 2026-08-18
author: lead
status: provisional
tags: [reader, text-to-world, coreference, theory, law-correction]
---

## The arms

`scripts/reader_arms.py`, 40 flood cases, five-paragraph surface, dependency
sets measured by ablation. Every reader sees **only the text**.

| arm | claim P | claim R | dep R | pooled | **non-empty** |
|---|---:|---:|---:|---:|---:|
| oracle world (ceiling) | 1.000 | 1.000 | 1.000 | 1.000 | **1.000** |
| 0 template reader, new surface | 0.000 | 0.000 | 0.000 | 0.450 | **0.000** |
| **1 rules, full** | **1.000** | **1.000** | **1.000** | 1.000 | **1.000** |
| **2 rules, no coreference** | 1.000 | 0.895 | 0.835 | 0.450 | **0.000** |
| 3 rules, distractors admitted | 0.823 | 0.881 | 0.932 | 0.700 | **0.682** |
| 4 lexical cue routing | 0.964 | 0.930 | 0.914 | 0.500 | **0.136** |
| empty world (no reader) | 0.000 | 0.000 | 0.000 | 0.450 | **0.000** |

**Arm 1 reaches the oracle exactly.** That is the benchmark's fairness check: the
surface is hard, not unfair, and a reader with coreference, unit handling and
entity linking can max it. (The `bridge_i` ids the text never states are
recovered by reproducing the generator's own `sorted((a,b))` ordering — a real
entity-linking step, and it works.)

## Coreference is not a refinement, it is the reader

> **Removing pronoun resolution takes the arm from 1.000 to 0.000** while global
> claim recall falls only from 1.000 to 0.895.

Three claims per case are stated through a pronoun: the superseded crossing's
*"it is now rated for N kg"*, the lightest vehicle's *"It can take a further N
kg"*, and the request's *"It is for N kg of supplies"*. The last is the
**demand**, present in every case — and without it no delivery can be sized, so
the system returns the empty set every time. It scores 0.450 pooled, which is
exactly the no-reader score.

That answers the programme's own question — *is reference resolution more
important than semantic parsing?* — for this task: **the parsing was already
perfect and the system still answered nothing.**

## Distractors cost far less than references

Arm 3 admits every distractor: the disused track between two regions outside the
area, the vehicle committed elsewhere, the superseded load limit. Precision falls
to 0.823 — and it still scores **0.682**. Bad claims are survivable here in a way
that missing ones are not, which is the enumerate-then-filter asymmetry the
earlier fidelity finding predicted, now visible from the reader side.

## The flat survival law fails, and the per-kind form fixes only the qualitative half

`S = q^k` with `k = 8.31` was fitted under **random** claim dropping. A reader
loses **systematically**:

| arm | dep R | flat `q^k` | **per-kind `Π q^d`** | measured |
|---|---:|---:|---:|---:|
| 1 rules, full | 1.000 | 1.000 | 1.000 | **1.000** |
| 2 no coreference | 0.835 | 0.222 | **0.000** | **0.000** |
| 3 distractors admitted | 0.932 | 0.555 | 0.440 | **0.682** |
| 4 lexical | 0.914 | 0.472 | 0.476 | **0.136** |

mean \|error\|: flat **0.137**, per-kind **0.116**.

- **The flat law is qualitatively wrong on arm 2**: 0.835 dependency recall
  predicts 0.222, and the truth is 0.000. No single-`q` model can produce a zero
  from 84% recall, because it assumes losses are exchangeable.
- **The per-kind form `S = Π_kind q_kind^{d_kind}` gets that exactly right** — a
  kind lost entirely sends its factor and the product to zero.
- **But the quantitative gain is small** (0.137 → 0.116) and **arm 4 is still
  3.5× over-predicted** (0.476 against 0.136). Recall of critical claims is not
  sufficient: it says nothing about a claim recovered with the *wrong value*, and
  nothing about a lost attribute removing an entity from the answer's domain
  entirely.

> **Status: the survival law is a screen, not a predictor.** It correctly rules
> out arms that lose a whole kind, and it should not be used to forecast a
> number. The per-kind form supersedes the flat one.

## What I got wrong, and what caught it

I predicted arm 1 would reach 1.000 and said that if it did not, *"the surface is
unfair, not hard"*. It came in at 0.682 with **capacity as its only error kind**
— and the surface was indeed unfair: the naming sentence said *"X is the lightest
of them"* while the capacity stated after it belonged to the first vehicle by id.
When those differed the text asserted something false, so the **ground truth was
wrong, not the reader**. Fixed, with two tests pinning that the named antecedent
owns the capacity the pronoun states and really is the lightest.

The alignment tests had checked that a quantity span contains its own value —
they had not checked that a *referent* matches. That is the class of defect a
span-level alignment can still hide.

## What would refute it

- **One task, 40 cases, four arms.** Arm 4 is one lexical design and a better one
  would score higher; the claim is not that lexical methods top out at 0.136.
- **Coreference matters this much because the demand is pronoun-stated.** That is
  a choice I made in the surface. It is a *fair* choice — reports really do say
  "it is for 1400 kg" — but the magnitude is a property of this surface, and a
  version stating the demand plainly would rank the ablations differently.
- **The per-kind law was fitted to nothing**: `d_kind` comes from ablation and
  `q_kind` from measurement, so its 0.116 error is out-of-sample. But four points
  is not a test of a functional form.

## Reproduce

```bash
uv run pytest tests/test_flood_surface.py
uv run python -u scripts/reader_arms.py
```
