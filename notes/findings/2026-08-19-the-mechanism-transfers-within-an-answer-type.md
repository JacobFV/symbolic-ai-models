---
title: The third domain sharpens a loose claim — the grounding mechanism transfers within an ANSWER TYPE, not merely as an idea, and the boolean check is now shared code between two domains
date: 2026-08-19
author: lead
status: provisional
tags: [renderer, grounding, transfer, scheduling, pipeline]
---

## The claim being sharpened

The solvency renderer concluded:

> What transfers is the contract — tokens, a domain-specific relation, and
> contradiction against the structured answer — **and not any line of code.**

That was drawn from two domains, and they had **different answer types**: flood
returns a set of vehicles, solvency a boolean. Scheduling is also boolean, so it
discriminates.

## It is reusable within an answer type

`symbolic_ai_generators/grounding.py` now holds `boolean_contradiction(text,
structured, *, yes, no)`, and **both** the solvency and scheduling renderers
import it. A test asserts they are literally the same function object.

> **The contradiction check is reusable within an answer type, parameterised by
> the verdict wording. It is not reusable across answer types** — flood's set
> answer needs per-element polarity and keeps its own.

The other two checks stay domain-specific by nature, and the middle one is a
different relation every time:

| domain | answer | middle relational check |
|---|---|---|
| flood | vehicle set | route **adjacency** |
| solvency | boolean | **date** validity |
| scheduling | boolean | **capability** validity |

So the honest decomposition is: **one check shared per answer type, one check
that is always bespoke, and a token vocabulary that is always bespoke.**

## The third domain works, and needs no coreference

`scheduling/surface.py` renders five aligned paragraphs — shop, capabilities,
work, requirements, question — with 20/20 claims covered, three distractors (a
withdrawn machine, a cancelled job, a capability nobody holds), and a job's
**duration in ¶3 and its required capability in ¶4**, so nothing about one job is
recoverable from one sentence.

`scheduling/read_surface.py` reads it by type signature alone:

```
(machine, quantity)        -> capacity
(job,     quantity)        -> duration
(machine, capability word) -> has_capability
(job,     capability word) -> needs_capability
```

**Claim precision and recall are exactly 1.000 at every phrasing setting
V = 1..4**, with **no coreference at all** — entity prefixes carry the type, so
the signatures separate outright. The distractors are rejected for free: the
withdrawn machine and cancelled job carry neither quantity nor capability, and
*"no machine is set up for anodising"* names a capability outside the vocabulary.

**The one piece of external knowledge is the capability vocabulary** — the
lexical counterpart of flood's numeric value registry. That is the second
instance of the same architectural need, and it does double duty as the
distractor filter.

## The paragraph distinguishes two ways of failing

40/40 grounded, and an infeasible order has to say *which* constraint bound:

```
The jobs cannot all be assigned. Total work is 13.63 hours against 17.72 hours
of capacity. Capability is available for every job, so the constraint is time:
the hours do not pack onto the machines that can take them, the largest being
machine_1 at 7.21 hours.
```

A test requires that clause on every infeasible case, so a paragraph that
announced the verdict without locating the constraint would fail.

## What would refute it

- **Three domains, two answer types.** A third answer type — a number, a ranking
  — would test whether "one shared check per answer type" is a real
  decomposition or an artefact of having only boolean and set.
- **Scheduling is the easiest of the three to read.** Entity prefixes carry the
  type, so 1.000 at V=4 says the signatures are clean here, not that reading is
  solved. Flood needed coreference and got 1.000 only after a bug fix; solvency
  needed dates.
- **The renderers are templates**, and their value is fixing the checkable
  contract rather than the prose.

## Reproduce

```bash
uv run pytest tests/test_scheduling_pipeline.py
```
