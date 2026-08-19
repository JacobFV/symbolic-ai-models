---
superseded: 2026-08-19 -- the headline is WITHDRAWN, reader loss is 0.000
title: The end-to-end milestone — report to typed world to three kernels to a decision and a grounded paragraph — and reader loss (0.682) exceeds every kernel loss (0.500 at worst)
date: 2026-08-19
author: lead
status: provisional
tags: [milestone, text-to-world, kernels, renderer, cost, ablation]
---

## The milestone, delivered

> a multi-paragraph report is converted into a typed world representation,
> passed through multiple specialised symbolic kernels, and produces both a
> structured decision and a grounded answer paragraph.

`scripts/milestone_end_to_end.py`, 40 flood cases, surface at **V = 4** (four
phrasings per claim kind, drawn per case — at V = 1 a hand-written pattern set
scores 1.000 and the table cannot discriminate). Task accuracy is on the
**non-empty** population, because 45% of cases have an empty answer that survives
any reader failure for free.

| system | claim R | task acc | $/correct | grounded |
|---|---:|---:|---:|---:|
| **oracle world (CEILING)** | 1.000 | **1.000** | 1.39e-08 | 1.000 |
| **signature reader** | 0.971 | **0.318** | 3.95e-08 | 1.000 |
| rules reader | 0.280 | 0.000 | inf | 1.000 |
| lexical cue routing | 0.256 | 0.000 | inf | 1.000 |
| template reader | 0.000 | 0.000 | inf | — |
| | | | | |
| oracle, **no datalog** reachability | 1.000 | 0.818 | 3.06e-08 | 1.000 |
| oracle, **no SMT** load check | 1.000 | **0.500** | 2.31e-08 | 1.000 |
| oracle, **no ASP** route search | 1.000 | 0.864 | 1.35e-08 | 1.000 |

Reader rows vary the reader with the kernels fixed; ablation rows fix the reader
at the oracle world and remove one kernel, so a drop is attributable.

## The headline

> **Reader loss is 0.682. The worst kernel loss is 0.500.** World construction
> costs more than any single kernel contributes.

That is the programme's own thesis — *the glaring unresolved problem is
constructing the world state from observations rather than receiving it from an
oracle* — measured in one table rather than asserted. Every kernel earns its
place (no SMT −0.500, no datalog −0.182, no ASP search −0.136), and the reader
still costs more than any of them.

**And cost moves the wrong way as the reader degrades.** `$/correct` rises 2.8×
from the oracle to the best reader — 1.39e-08 to 3.95e-08 — because the kernels
run at nearly the same price and produce fewer correct answers. A weaker reader
does not save compute; it wastes it.

## What each column establishes

- **claim R vs task acc are not the same axis.** The signature reader recovers
  **0.971** of claims and answers **0.318** of tasks. Recall is not a proxy for
  capability, which is why the dependency-weighted and end-to-end columns exist.
- **The grounded column is 1.000 everywhere the renderer ran.** Groundedness is
  checked at token *and* adjacency level, and the checker is tested to fail on an
  invented quantity, an invented entity and a false ordering of real regions.
  The template reader shows `—` because it never produced a world to render.
- **The structured decision is canonical.** The paragraph is downstream of it, so
  a renderer cannot move the task score.

## What this does not show

- **One domain.** Solvency has a surface, readers and a transfer result but no
  renderer, so it has no milestone row.
- **The reader arms are hand-authored**, and three of them score 0.000 at V=4 for
  the reason already established: a pattern set is written against a phrasing.
  The signature reader is the only one that generalises, and its 0.318 is the
  honest state of the front rather than a good result.
- **$/correct prices the kernels only.** The reader's own compute is not in it,
  and for a learned reader it would dominate — which is exactly the misreading
  `symbolic_ai_core/cost.py` was written after, so the column is a lower bound on
  system cost and is labelled as such.

## Reproduce

```bash
uv run python -u scripts/milestone_end_to_end.py
```

## WITHDRAWN, same day: reader loss is 0.000, not 0.682

The headline rested on the signature reader scoring 0.318, which was caused by a
missing branch in the reader rather than by any property of reading. Fixed, the
table reads:

| system | claim R | task acc | $/correct |
|---|---:|---:|---:|
| oracle world (ceiling) | 1.000 | **1.000** | 1.97e-08 |
| **signature reader** | **1.000** | **1.000** | **2.03e-08** |
| oracle, no SMT | 1.000 | 0.500 | 3.37e-08 |

**Reader loss 0.000 at a 3% cost premium**, and the kernel losses now dominate.
The claims about what each *column* establishes survive; the claim about which
component is the bottleneck does not.
