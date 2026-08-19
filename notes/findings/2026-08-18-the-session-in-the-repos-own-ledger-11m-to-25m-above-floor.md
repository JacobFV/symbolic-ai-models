---
title: This session in the repo's own ledger — 1.1M× to 2.5M× per answer above floor, charging ourselves for building the world and granting the model perfection
date: 2026-08-18
author: lead
status: provisional
tags: [cost, north-star, ledger, floors, openalex]
---

## Why this exists

Everything measured this session was priced with hand-rolled arithmetic in
scripts, while `symbolic_ai_core/cost.py` — which exists to compute exactly this
— sat unused for the whole session. That module is not a convenience. It encodes
the conventions a number must satisfy to be **comparable with what the repo has
already published**, chiefly that it divides by `rate − floor` and not by `rate`,
so a system at its floor reports *infinite* cost per unit of capability.

`scripts/query_floors.py` supplied the floors. This puts the numbers through the
ledger.

## The row

`scripts/session_ledger.py`. Price sheet: $0.02/core-hour, frontier $15/Mtok in.
Symbolic extraction measured at **1,409,342 tok/s** on one core.

| capability | rate | floor | above floor | **$/answer above floor** | model $ (perfect) | **ratio** |
|---|---:|---:|---:|---:|---:|---:|
| `collaborators(institution)` | 0.417 | 0.120 | 0.297 | 4.01e-09 | 4.54e-03 | **1,130,152×** |
| `works_at(institution)` | 0.671 | 0.027 | 0.644 | 1.85e-09 | 4.54e-03 | **2,450,564×** |
| `works_at_both(A,B)` | 0.465 | 0.022 | 0.443 | 2.69e-09 | 4.54e-03 | **1,685,714×** |
| `institutions_of(work)` | 0.576 | 0.034 | 0.542 | 2.20e-09 | 4.54e-03 | **2,062,431×** |

## What each row is charged, which is the point

**The symbolic side pays for building the world it answers from.** The extraction
pass is a component of the query system, not a free precondition — which is the
module's stated reason for existing (*"there is no way to express 'our part is
free' without also expressing what the other parts cost"*) and is exactly the gap
this session found in every previously published advantage.

**The model is granted perfection.** Rate 1.0, floor 0, input tokens only, zero
output, no hallucination, reading only the 302.3-token dependency rather than the
corpus. The accuracy comparison is blocked on credentials (`ROADMAP.md` 0b), and a
bound that assumes the opponent is *perfect* needs none to stand.

So **1.1M×–2.5M× is a lower bound**, and it is the first number from this session
expressed in the repo's north-star metric rather than beside it.

## The cross-check that matters

The hand-rolled extraction bound published earlier today was **1,766,210×**. The
ledger, computed independently through a different module with floors applied,
lands at **1.1M–2.5M×** across four capabilities. They agree in order of magnitude
and bracket the hand-rolled figure — so the earlier arithmetic was **off-basis,
not wrong**, which is the useful version of that correction.

## What would refute it

- **The rates are agreement with OpenAlex**, not truth, as everywhere in this arm.
  A ledger row inherits its capability's anchor.
- **Extraction throughput is one measurement on one box**, and `cost.py`'s own
  docstring says timing on this box measures the box. 1.4M tok/s is a symbolic
  string-matching pass, not a parse.
- **The model row assumes it needs only the dependency.** A real retriever must
  *find* the dependency first, which this repo measured at a 46× over-fetch — so
  the honest opponent is dearer still, and the bound is loose in our favour on
  that axis too.
- **The floor is a popularity guess.** A cleverer floor — a learned prior over
  co-occurrence — would be higher, and `collaborators` is the row most exposed to
  it, having already lost 28.8% of its score to the simple one.

## Reproduce

```bash
SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \
  uv run python -u scripts/query_floors.py      # the floors
uv run python -u scripts/session_ledger.py      # the ledger row
```

`runs/query_floors.json`, `runs/session_ledger.json`.
