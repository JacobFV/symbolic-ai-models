---
title: The repo's only reader goes 1.000 → 0.000 on the same worlds when the words change — and the pooled metric cannot tell it apart from having no reader at all
date: 2026-08-18
author: lead
status: provisional
tags: [reader, text-to-world, benchmark, baseline]
---

## What was built

`symbolic_ai_generators/flood/surface.py` — a **five-paragraph observation
surface with exact span→claim alignment**, in the shape the programme asked for:
actors and places, infrastructure, current events, quantities and constraints,
query context.

It is deliberately not a rephrasing. It carries:

- **Distance.** A vehicle's mass is in the fleet roster (¶1), its capacity in the
  quantities paragraph (¶4). Nothing about one entity is recoverable from one
  sentence.
- **References.** *"It can take a further 1500 kg"*, *"the vehicle listed as
  truck_1"*, *"that crossing"*. The pronoun's antecedent is a naming sentence
  that realises **no claim**, so resolving it is a step the reader has to take.
- **Distractors.** Regions outside the affected area, a vehicle committed
  elsewhere, a disused track, and a **superseded load limit** — checked at
  generation time not to collide with any real quantity, so "take every number"
  is never accidentally right.
- **Indirect statements.** Flooding as negation (*"no longer passable"*), limits
  as *"rated for"*, links as *"joined by a surfaced road"*.

**Every claim is realised by at least one span, and every span carries the index
of the claim it realises or `None`.** `tests/test_flood_surface.py` (12 tests)
holds that: full coverage, non-overlapping offsets, quantity spans containing
their own value, mass and capacity in different paragraphs, distractors aligned
to nothing, determinism.

## Arm zero

`scripts/reader_arms.py`, 40 cases, dependency sets measured by ablation.

| arm | claim P | claim R | dep R | acc pooled | **acc non-empty** |
|---|---:|---:|---:|---:|---:|
| oracle world (ceiling) | 1.000 | 1.000 | 1.000 | 1.000 | **1.000** |
| template reader, **old** report | 1.000 | 1.000 | 1.000 | 1.000 | **1.000** |
| template reader, **new** surface | 0.000 | 0.000 | 0.000 | 0.450 | **0.000** |
| empty world (no reader) | 0.000 | 0.000 | 0.000 | 0.450 | **0.000** |

> **The repo's only reader recovers 100% of the world from one surface and 0% of
> the same worlds from another.** That is the honest starting point of the
> text→world front, and it is what "a template reader proves nothing about
> parsing" means as a number.

### The pooled metric is dead on this task

**A reader that recovers nothing scores 0.450 pooled** — identical to having no
reader at all — because 45% of flood cases have an empty correct answer that
survives any failure for free
(`notes/findings/2026-08-18-the-flood-floor-is-the-empty-answer-share-...md`).

The harness therefore prints both and treats **non-empty** as the result. No arm
from here is reportable on the pooled column.

## What the harness gives every later arm

A reader is a `case → WorldSnapshot`, and it is scored on claim precision/recall,
**dependency-weighted recall** (against the ablation-measured dependency set,
mean 6.95 claims), and end-to-end accuracy split by population, with the oracle
world as ceiling. So reader loss and reasoning loss are separated by
construction rather than left in one opaque score.

## What would refute it

- **The surface could be gratuitously hard.** It is not paraphrase — it is a
  different register with references and distractors. The check that it is *fair*
  is the alignment: every claim is stated somewhere, and the pronoun's antecedent
  is present. A reader with coreference and unit handling can reach 1.000.
- **40 cases, one domain.**
- **Claim identity is exact-match on predicate, polarity, roles and rounded
  quantities.** A reader recovering a claim in a different but equivalent form
  scores zero for it, which will understate near-miss arms.

## Reproduce

```bash
uv run pytest tests/test_flood_surface.py
uv run python -u scripts/reader_arms.py
```
