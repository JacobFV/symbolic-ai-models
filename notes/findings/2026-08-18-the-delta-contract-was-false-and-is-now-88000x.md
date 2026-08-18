---
title: The incremental contract was false as implemented — 1,231 ms to add one edge became 0.06 ms, and the cost finally tracks the delta
date: 2026-08-18
status: provisional
tags: [datalog, performance, world-delta, engine, real-data, negative-result]
---

## The claim under test

`engine.add_facts` carries this in its docstring, and the whole `WorldDelta` and
streaming design rests on it:

> *This is the incremental path and it is why datalog sits next to the
> `WorldDelta` contract: a delta arrives, and the cost is proportional to what
> it actually changed rather than to the size of the world.*

It had never been measured on real data.

**Prediction: it beats recompute, but the per-call index rebuild caps the win
near 10–50x, short of the ~1000x that "proportional to the delta" implies.**

## Measured, and worse than predicted

GLEIF ownership, 124,260 base edges closing to **285,596 facts**. Adding held-out
edges:

| delta | `add_facts` | full recompute | speedup | facts derived |
|---|---|---|---|---|
| 1 edge | **1,230.7 ms** | 6,967 ms | **5.7x** | 2 |
| 10 | 2,456.0 ms | 6,998 ms | 2.8x | 37 |
| 100 | 4,137.1 ms | 6,928 ms | 1.7x | 614 |
| 200 | 5,206.2 ms | 7,069 ms | 1.4x | 1,488 |

**A two-fact change cost 5.7x less than rebuilding a 285,596-fact model, and by
two hundred edges the incremental path was within 40% of recomputing
everything.** The documented property was false, in the kernel the roadmap calls
the hot-path workhorse.

## Two causes, and the second was the real one

**1. The index was rebuilt every round.** `add_facts_report` called
`_index(total)` inside its loop, so each round paid for the whole model. Fixed by
building once and maintaining it (`FactIndex.add`), plus an `IncrementalModel`
that **owns** its index across calls — because a stateless function must rebuild
by definition, and that is why no amount of tuning inside `add_facts` could have
honoured the contract.

That got one edge from 1,230.7 ms to **210.0 ms**. Still not proportional.

**2. Semi-naive was starting the join at the wrong end.** Semi-naive requires
each derivation to use a fact new this round, but the engine required it *at
body position j* while still solving left to right. On
`ult(X,Z) :- par(X,Y), ult(Y,Z)` with the delta on `ult`, position 0 enumerated
**all 124,260 `par` facts** to find partners for two new ones. Starting the join
at the delta binds its variables immediately and makes every later literal an
indexed lookup.

| delta | original | + index reuse | **+ delta-first** | vs recompute |
|---|---|---|---|---|
| 1 edge | 1,230.7 ms | 210.0 ms | **0.06 ms** | **88,927x** |
| 10 | 2,456.0 ms | 400.2 ms | 0.23 ms | 22,632x |
| 100 | 4,137.1 ms | 678.0 ms | 2.18 ms | 2,344x |
| 200 | 5,206.2 ms | 857.9 ms | 4.39 ms | 1,165x |

**20,500x on the incremental path itself**, and — the part that is the actual
claim — **the cost now tracks the delta**: 2 derived facts in 0.06 ms, 1,488 in
4.39 ms, essentially linear in what changed rather than in what exists.

Safety is preserved by construction in the reordering: all positive literals are
emitted before all negated ones, so every variable in a negated literal is still
bound when it is reached, which is the condition that lets `not p` be a ground
membership test rather than a search.

## How I know it is correct

The oracle from yesterday still applies to `evaluate` (25 generated programs
against a brute-force fixed point, unchanged). For the incremental path:

- **20 randomised deltas** must give a model byte-identical to recomputing from
  scratch.
- **A 15-step sequence** of deltas against one recomputation, because state
  accumulating quietly wrong over many plausible steps is how an incremental
  engine actually rots.
- **A delta that closes a cycle**, since ownership cycles are real here.
- **Full scale**: at every delta size above, `m.facts == evaluate(program, base
  | delta)` was asserted on the real 285,596-fact model.

`IncrementalModel.add` **refuses** an addition that can reach a negated
predicate rather than returning an unsound model, and names the rebuild in the
error. A wrong incremental result is indistinguishable from a right one, which
is the same reason retraction is still absent.

## What this does not change

No published number moves: every finding to date used the purpose-written
closure or `evaluate`, never `add_facts`. The property that was false was
documented and unused — which is its own small lesson, since **a claim nothing
exercises is a claim nothing checks**, and this one sat in a docstring across
every design decision that cited it.

## What would refute it

- One rule shape, one relation. `ult` is a near-forest with fan-out 1; a rule
  with genuine fan-out derives far more per delta fact and the ratio falls.
- The 88,927x is against **full recompute**, which is the honest comparison for
  "should I maintain or rebuild" and not a general speed claim.
- Deletion remains unimplemented and unmeasured. Under negation a retraction can
  both remove and create conclusions, and that needs derivation counts the
  engine does not keep.
