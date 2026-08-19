---
title: A sentence gate takes a right answer and makes it wrong
date: 2026-08-19
status: measured
arm: stale-clause
---

## Making the real-text failure reproducible

On 168 Wikipedia company intros a sentence-level staleness gate answered *Miramax*
with **The Walt Disney Company** — a parent Wikidata records as **former** —
because one sentence carried a dead owner and a live one and the gate deleted the
wrong half. No generated surface here could produce that: each puts one claim in
one sentence, which is why the gate reads as free on all three.

`stale_clause` prefixes a **real** member's filing with a former-parent clause:

> *"sub_0, formerly a subsidiary of sub_97, reported 105.87 USD, filed 29 May
> 2026."*

The clause is irrelevant and the filing is needed. The second entity has to be a
real id — with an unmatched name the reader sees one entity and nothing is packed
at all, which is a way this case could quietly become easy and is pinned by a
test.

## Six cells, 120 seeds

| reader | gate | clean | **stale clause** |
|---|---|---:|---:|
| branch | none | 1.000 | **0.625** |
| branch | sentence | 1.000 | **0.625** |
| branch | **clause** | 1.000 | **1.000** |
| accumulate | none | 1.000 | **0.925** |
| accumulate | **sentence** | 1.000 | **0.625** |
| accumulate | **clause** | 1.000 | **1.000** |

**The sentence gate takes 0.925 to 0.625.** It does not merely fail to help: it
takes a reader that was mostly right and makes it wrong, which is the Miramax
mechanism exactly, now reproducible without leaving the repo.

## Three things the six cells say

**The branching reader loses the filing outright.** Two entities *and* money *and*
a date matches no branch in its `elif` chain, so the claim is dropped — 0.625,
which is the same collapse packing produced.

**Accumulation recovers most of it and not all.** 0.925, and the residual is the
binding: this reader attaches a filing to the entity **nearest the money**, and in
this shape the parenthetical sits closer to the number than the subject does, so
some filings bind to `sub_97`. The refutation condition I named for the
accumulating readers half-fired — the heuristic is right for
*"group owns sub_0, which reported …"* and wrong for
*"sub_0, formerly …, reported …"*, and the two shapes are equally natural. It
shows as 0.925 rather than 0.5 because the verdict is a threshold test and one
lost filing rarely crosses it.

**The clause gate gives 1.000 to both readers, and it does two jobs at once.** It
removes the dead claim, and it removes the **second entity** that made the binding
ambiguous — after filtering, the sentence is *"sub_0 reported 105.87 USD, filed 29
May 2026"*, with one entity and nothing to guess. A gate that cuts at the right
granularity does not just delete less; it *simplifies what is left*.

## Shipped

`filter_stale(text, gate, unit="clause")`, with `"sentence"` kept as the default
so every number measured before this keeps its meaning. The Wikipedia script now
calls the shipped function rather than its own copy, so there is one
implementation, and it reproduces the same ordering on real text: naive 0.589 /
0.369, sentence **0.548 / 0.339**, clause 0.583 / 0.357 with the former-parent
error 0.024 → **0.018**.

## What would refute this

- One clause shape, one domain. A stale clause that carried *no* second entity
  would leave nothing for the clause gate to simplify, and the gain would be
  smaller.
- The clause splitter is commas, semicolons, colons and contrastive conjunctions.
  It will split a list of members wrongly, and nothing here measures how often.
- The 0.925 residual depends on the threshold distribution: a tighter covenant
  would flip more of the mis-bound filings and make accumulation look worse.
