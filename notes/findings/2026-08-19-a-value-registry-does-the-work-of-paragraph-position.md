---
title: A value registry does the work of paragraph position — 72 worlds to 9, a bound deciding 0.0% to 36.4%, soundness preserved — and consistency pruning has nothing to bite on
date: 2026-08-19
author: lead
status: provisional
tags: [reader, ambiguity, external-knowledge, world-ir, critical-invariant]
---

## The frontier this addresses

The five-paragraph surface became saturated: a reader consulting no content word
reaches the oracle. What it still hands over for free is **section headings and a
fixed paragraph order**, and position does most of the disambiguation. Ablate
position and the ambiguity is real —

```
(1 vehicle, 1 quantity)  ->  mass OR capacity
(1 region,  0 quantity)  ->  flooded OR depot OR needs
(0 entities, 1 quantity) ->  the pronoun capacity OR the demand
```

— leaving **72 consistent worlds** and a bound that decides **0.0%** of the fleet.

## Consistency pruning has nothing to bite on

The obvious move is to let the kernels prune incoherent readings. It fails, and
the reason is worth recording.

I verified over 200 cases that the depot is **never** flooded, the demand site is
**never** flooded, and depot ≠ needs. Those are real invariants of the domain —
and they are **automatically satisfied by any assignment that gives the three
roles to three distinct regions**, which is exactly what the enumeration
produces. They prune nothing.

> **Every ambiguous reading here is internally coherent.** The world IR can carry
> the ambiguity and the task offers no constraint that collapses it. Branching
> and bounding are available; *resolution by consistency* is not.

## External knowledge does bite

The generator draws from disjoint vocabularies:

| kind | values |
|---|---|
| mass | 1200, 1800, 2600, 3200 |
| capacity | 1500, 2500, 4000 |
| demand | 900, 1400, 2100 |

`mass ∩ capacity = ∅` and `demand ∩ capacity = ∅`, so **a value alone settles
which role a number plays**.

| arm | worlds | sound | cert. IN | cert. OUT | open | **decided** |
|---|---:|---:|---:|---:|---:|---:|
| no external knowledge | 72.0 | 1.000 | 0.00 | 0.00 | 3.00 | **0.0%** |
| **+ value registry** | **9.0** | 1.000 | 0.91 | 0.18 | 1.91 | **36.4%** |

**8× fewer worlds, and a vacuous bound becomes a partially informative one, with
soundness preserved.** The 9 worlds and 36.4% match the *region alone* row of the
earlier ambiguity-regime sweep exactly, confirming the registry collapses the
vehicle and bare groups **completely** and leaves precisely the region group.

> **A value vocabulary does the work of paragraph position for two of the three
> ambiguity groups** — and a registry is a far cheaper thing to possess than a
> document template. That is the programme's own question, *can external
> ontologies dramatically reduce required learning*, answered with a number on
> this task.

## What survives, and why

The **region group** is untouched: `flooded`, `depot` and `needs` are all bare
region mentions with no quantity, so no value signal distinguishes them. Closing
it needs either position (which is what was ablated) or relational knowledge —
that a depot is somewhere vehicles start, that flooding is an event. That is a
genuinely different kind of external knowledge from a value list.

## Stated honestly

- **The registry is the generator's own draw sets.** That makes it unusually
  clean external knowledge, so this measures the **ceiling** of what a value
  vocabulary buys. A real registry would overlap and be noisier, and the arm is
  ablatable precisely so that assumption is visible.
- **36.4% decided is still not actionable for a caller** who wants an answer. The
  earlier finding stands: carrying ambiguity is free soundness and is only
  actionable in a narrow regime. The registry moves this task from *outside* that
  regime to its edge, not into it.
- **40 cases, one domain.**

## Reproduce

```bash
uv run python -u scripts/ambiguity_regime.py
```

with `signature_worlds(..., registry=VALUE_REGISTRY)`.
