---
title: Ownership closure on filed data — fusing two relations beats either, and the third point puts the symbolic advantage across seven orders of magnitude
date: 2026-08-18
status: provisional
tags: [real-data, datalog, fusion, cost, gleif, economy]
---

## It also corrects something I said this morning

The column audit concluded the economy kernel could not run on real data because
no held source carries a **unit**. True, and it does not follow. **Consolidation
structure is relational and needs no units at all.** GLEIF publishes 124,460
`IS_DIRECTLY_CONSOLIDATED_BY` edges and 130,355 `IS_ULTIMATELY_CONSOLIDATED_BY`
edges, and the second is the transitive closure of the first.

The corpus is poorer than the source cards imply, and it is *richer than the
capability audit implies*, because the audit asked which profiles could be
populated and not which questions could be asked. Both directions of that error
are now on record.

## Why this task is worth more than the last one

**The labels are filed independently of their own inputs.** Each legal entity
reports its direct parent and its ultimate parent separately, so the closure is
checked against something that is not a restatement of the edges it consumed.

**The floor is high before anything starts.** 75.03% of entities are directly
consolidated by their ultimate parent, so "assume depth one" is a real answer.

## Predictions, before the numbers

1. Naive floor: **~0.75**.
2. Transitive closure: **~0.93**.
3. Depth-2 truncated closure (the swept floor): **~0.93**, so full closure buys
   only ~+0.03 over stopping at two hops.
4. Fused method: **~0.978**.

## What I found

| method | accuracy |
|---|---|
| floor — assume depth one | **0.7503** (predicted 0.75 — right) |
| **swept floor** — closure truncated at depth 2 | **0.9005** (predicted 0.93 — wrong) |
| depth 3 / 4 / 6 / 8 | 0.9350 / 0.9507 / 0.9565 / 0.9573 |
| unbounded transitive closure | **0.9573** (predicted 0.93 — wrong, under-called) |
| **fused: direct edges + others' filed ultimates** | **0.9785** (predicted 0.978 — right) |
| control: direct edges shuffled | **0.0003** |

The floor sweep matters exactly as the last one did. Against the naive floor the
closure looks like +0.2071; against a crude 2-hop version of the same capability
it is **+0.0569**. Depth 2 alone does most of the work, and I predicted its
value wrong by 0.03 in the direction that flattered the method.

Convergence is at depth 8 — 0.9573 and unchanged at 16 and 64 — so the tail of
deep ownership chains is real but thin.

## Two relations that disagree are not a contradiction

The closure disagrees with the filed ultimates on **4,998 entities (4.27%)**.
The breakdown is the finding:

| | count | share |
|---|---|---|
| our chain runs out early, and GLEIF's ultimate for **that endpoint** agrees | 2,500 | 50.0% |
| neither | 2,241 | 44.8% |
| GLEIF's ultimate is an **intermediate** on our chain, not its root | 251 | 5.0% |
| ownership **cycle** | 6 | 0.1% |

Half of the disagreements are a single missing link. Following the endpoint's
own filed ultimate — **another entity's label, never the predicted entity's,
enforced by a test** — takes 0.9573 to **0.9785**.

The 5.0% is a semantic finding rather than an error: **"ultimately consolidated
by" is not "root of the direct-consolidation chain".** GLEIF's ultimate is the
highest entity that files consolidated accounts, which can sit below the topmost
legal owner. Two relations that look like a base/closure pair are not quite one,
and a system that merged them into a single `owns` predicate would have lost
that distinction and been silently wrong on 251 entities. *The predicate is the
type*, again.

Circular ownership exists in filed data — 6 entities — and is returned as a flag
rather than truncated, because "A is ultimately owned by A" and "we gave up
after 64 hops" are different claims.

## The third point, and now there is a curve

| task | context an LLM must be **given** | advantage |
|---|---|---|
| country from a coordinate | ~40 tokens | **~6,750x** |
| shortest path in the route network | 233k tokens | **~1,500,000x** |
| ultimate parent from ownership edges | **1.99M tokens** | **~1.85e11** |

Ledger for this task: fused closure **$1.38e-10** per solved-above-floor at
1.0 µs/entity; an LLM at assumed equal accuracy, **$25.52**.

Three points, one corpus, one substrate, spanning **seven orders of magnitude**,
and one variable orders them: **how much of the answer lives in structure the
model must be handed rather than in knowledge it already has.** World geography
is in the weights; a coordinate is 40 tokens. The OpenFlights route graph is
not; it is 233k tokens. Private corporate consolidation filings are emphatically
not; they are 1.99M tokens.

**And past a point it stops being a price ratio.** 1.99M tokens exceeds a
1M-token context window, so the comparison is no longer "expensive versus
cheap" but "cannot be asked in one query versus 1.0 microseconds". That
threshold — not any ratio — is the real argument for this substrate.

## What would refute it

- The LLM accuracies are still **assumed equal and stamped NOT QUOTABLE**. For
  this task the assumption is generous to the model in a way the last one was
  not: it cannot memorise GLEIF, and the graph does not fit. But it is unrun.
- Retrieval changes the shape. An LLM with a graph tool is not being given 1.99M
  tokens — it is calling something like this substrate. That is the honest
  framing of the whole comparison, and it argues the substrate is *the tool*,
  not the competitor.
- The fused method's discipline is enforced by one test. If it ever reads the
  predicted entity's own filed ultimate, 0.9785 is meaningless.
