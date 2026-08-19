---
title: The reader reaches the oracle at a 3% cost premium — and both things I published about it were wrong, because I drew a capability boundary around a missing branch in my own code
date: 2026-08-19
author: lead
status: provisional
tags: [reader, correction, text-to-world, milestone, self-correction]
---

## Two published claims, both wrong

**`notes/findings/2026-08-18-type-signatures-are-phrasing-invariant-and-stop-exactly-at-meaning.md`** said:

> Type signature and position recover every claim whose role is fixed by what it
> mentions and where it sits, and **stop exactly at reference mediated by
> meaning**. […] **This is the first place in the front where a lexical resource
> or a learned component is not a shortcut but the only mechanism available.**

**`notes/findings/2026-08-19-the-milestone-reader-loss-exceeds-every-kernel-loss.md`** said:

> **Reader loss is 0.682. The worst kernel loss is 0.500.**

Both were consequences of **one missing branch in my own reader.**

## What was actually wrong

The naming sentence — *"Turning to payloads, truck_0 is the lightest of them."* —
has type signature **(1 vehicle, 0 quantities)**. In the quantities paragraph the
reader handled `2 regions + quantity`, `vehicle + quantity`, and `bare quantity`.
**A vehicle with no quantity fell through every branch**, so `last_vehicle` kept
whatever the roster paragraph had left, and the following pronoun bound to the
wrong vehicle.

I read that as evidence that the antecedent was *"named by a superlative"* and
therefore needed meaning. It does not. **The antecedent is the nearest preceding
lone-vehicle mention, recoverable from position and signature with no content
word read at all.** The fix is one clause and consults no lexicon.

## What it does

| reader | V=1 | V=2 | V=3 | V=4 |
|---|---:|---:|---:|---:|
| rules, full | 1.000 | 0.000 | 0.000 | 0.000 |
| lexical cue routing | 0.136 | 0.000 | 0.000 | 0.000 |
| **type signature** | **1.000** | **1.000** | **1.000** | **1.000** |

Claim recall **1.000** and dependency recall **1.000** at every V. Still flat
across phrasings, because nothing lexical was added.

And the milestone table inverts:

| system | claim R | task acc | $/correct | grounded |
|---|---:|---:|---:|---:|
| oracle world (ceiling) | 1.000 | **1.000** | 1.97e-08 | 1.000 |
| **signature reader** | **1.000** | **1.000** | **2.03e-08** | 1.000 |
| oracle, no datalog | 1.000 | 0.818 | 4.06e-08 | 1.000 |
| oracle, **no SMT** | 1.000 | **0.500** | 3.37e-08 | 1.000 |
| oracle, no ASP search | 1.000 | 0.864 | 1.85e-08 | 1.000 |

> **Reader loss is 0.000, not 0.682.** A reader that consults no content word
> reaches the oracle on a surface with four phrasings per claim kind,
> distractors, references and split attributes — at a **3% cost premium**
> (2.03e-08 against 1.97e-08). The kernel losses now dominate: no SMT −0.500, no
> datalog −0.182, no ASP search −0.136.

## The thing to actually take from this

**The surface is saturated again.** A reader reaching the oracle means the
benchmark no longer discriminates — the same trap the rules arm hit at V=1, which
I diagnosed at the time and then walked into from the other side. 1.000 is not
"reading is solved"; it is "this surface's difficulty is exhausted by a
structural reader".

What the surface still hands the reader for free:

- **Section headings.** The reader keys paragraphs by `SITUATION REPORT` /
  `ROAD NETWORK` / … Position does most of the disambiguation work.
- **A fixed paragraph order**, so signature ambiguities resolve by where a
  sentence sits.

Removing those is exactly the regime measured in
`notes/findings/2026-08-19-carrying-ambiguity-is-always-sound-and-rapidly-vacuous.md`,
where the same reader with position ablated leaves 72 consistent worlds and a
bound that decides 0.0% of the fleet. **So the honest frontier is: a reader that
does not get position for free, and must emit ambiguity rather than resolve it.**

## What would refute the correction

- **The fix could be surface-specific.** The naming sentence is glue in *my*
  generator, placed immediately before the pronoun. A document where the
  antecedent is further away, or where two lone-vehicle mentions intervene, would
  break recency and might genuinely need meaning. That is untested and the
  boundary claim may be right for a harder surface — it was simply not
  established by the evidence I had.
- **One domain, 40 cases.**

## Reproduce

```bash
uv run python -u scripts/reader_generalisation.py
uv run python -u scripts/milestone_end_to_end.py
```
