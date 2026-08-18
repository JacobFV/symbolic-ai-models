---
title: The 99,738x we retracted as "just the framing" is the amortisation constant — it is the number of queries the symbolic path must answer to pay for building the world, and the programme has never priced its own first arrow
date: 2026-08-18
author: lead
status: provisional
tags: [cost, approach, data, blocker, reframe]
---

## Two things noticed in the same hour

**One.** Looking for a prose corpus on which to re-price the ~5e7 constant —
`HANDOVER.md` §4 parks it as "a measurement, not a law … a corpus of prose facts
should move it" — I found there is not one. Checked across all 19 catalogued
sources, 14 GB:

- every table is `(id, label, kind, body, source_url)` or `(source_id, target_id, kind)`;
- `body` is key-value metadata (`issued=1971-12-01 type=Text`), a two-letter
  country code, or **empty** — patentsview's 8.5M patent bodies are 0 characters;
- the **longest natural-language field in the entire corpus is a patent title**,
  mean 59.4 characters, p50 54;
- courtlistener, the one source whose name promises prose, is a **77M-edge
  citation map** with no text column at all.

So every source arrives **already structured**, and the first arrow of
`APPROACH.md`'s own thesis —

> arbitrary observations → **typed world representation** → cost-aware
> heterogeneous computation → outputs

— has never been priced, because there is nothing on disk on which it could be.
`CLAUDE.md` is explicit that this is in scope: *"Cost is charged to the system:
if a reasoner only works because something upstream produced a graph, that
upstream component is in the ledger whether or not it exists yet."* It is not in
the ledger.

**Two.** Pricing it turns out to need no new experiment, and the answer is a
number already published — as a mistake.

## The identity

`scripts/extraction_breakeven.py`. If a language model has to read the corpus
once to turn it into facts, at the repo's own price sheet and the same
input-tokens-only, perfect-extraction convention every other cost row here uses:

| price sheet | extract corpus | LLM $/query (oracle) | saving/query | **breakeven** |
|---|---:|---:|---:|---:|
| frontier ($15/Mtok) | $61.20 | 6.15e-04 | 6.15e-04 | **99,512 queries** |
| cheap ($1/Mtok) | $4.08 | 4.10e-05 | 4.10e-05 | **99,512 queries** |

**The breakeven is the same on both price sheets**, and it has to be: our
per-query cost is 1.56e-11, eleven orders below either, so

```
breakeven  =  (corpus_tokens x rate) / (dependency_tokens x rate)
           =  corpus_tokens / dependency_tokens
           =  4.08e6 / 41  =  99,512
```

It is not a price at all. It is the **over-fetch ratio of the naive framing** —
and that is a number this repo already published, and already retracted:

> `HANDOVER.md` §5: *"the advantage curve spans seven orders of magnitude,
> 1.85e11 on ultimate parent" — arithmetic right, framing load-bearing:
> **99,738x** of it was handing the model the whole graph.*

99,512 against 99,738, a 0.23% gap that is rounding on the two inputs. **They are
the same quantity, by construction.** The factor discarded as an artefact of a
bad framing is the amortisation constant: it is exactly how many queries the
symbolic path must answer before it has paid for building the world it answers
from.

The retraction was right about the *claim* and wrong about the *number*. Handing
a model the whole graph per query is indefensible. Handing it the whole graph
**once** is not a framing error — it is the build step, and it is what our side
gets for free.

## What follows

**The symbolic advantage is an amortisation argument, and it always was.** The
~5e7 per-query figure is not overstated; it is real, and it lives entirely on the
far side of a crossover nobody had located. Below ~100,000 queries against a
corpus, a model reading the dependency wins. Above it, we win by the constant.

**And facts change, so the bar is a rate rather than a total.** At 13F's measured
quarterly churn of 32% (744,136 of 2,282,570 edges), a corpus that must be
re-extracted as it moves needs **31,844 queries per quarter — about 350 a day**
— just to stay ahead of its own rebuilding. That number is the join between this
finding and the certificate arm: the maintenance work says *how much* of a world
must be re-derived per update, and this says *what re-derivation costs*.

**The boundary condition of the whole programme, stated precisely:**

> The advantage is measured, real, and large for domains where the structure is
> **already filed** — regulatory (GLEIF, SEC), bibliographic (OpenAlex,
> PatentsView), geographic (GeoNames, OpenFlights). There, a regulator or a
> registry has already paid the extraction cost and externalised it, which is a
> legitimate answer and is why nothing published here is wrong.
>
> It is **unmeasured** for domains where structure must be derived from
> observation — which is the domain `APPROACH.md` names as the target.

## What would refute this

- **The arithmetic assumes extraction costs one read of the corpus at input
  rates.** Real extraction needs output tokens too, probably several passes, and
  it does not achieve perfect accuracy — so $61.20 is a **lower bound** on the
  build, which makes the breakeven a lower bound too. It moves in one direction.
- **It assumes extraction must be done by a model.** A rule-based extractor
  would be orders cheaper, and whether one exists for a given domain is the
  entire open problem. Where one does, the crossover collapses toward zero and
  this note stops mattering.
- **It is computed on the GLEIF ownership corpus**, whose facts are 20-character
  identifiers. A corpus of prose has a different `corpus_tokens/dependency_tokens`
  ratio, and since that ratio *is* the crossover, re-pricing the constant and
  locating the crossover are the same experiment. There is still no corpus on
  disk to do it on.

## The blocker this names

**Acquiring a corpus of raw observations with ground-truth structure is now the
highest-value data need in the repo**, and it is not a nice-to-have: without one,
the first arrow of the thesis cannot be measured at all, and every cost number
this programme publishes is conditional on somebody else having built the world.
Candidates that pair text with derived structure: UD treebanks (text → parse),
SEC filings in raw HTML rather than the extracted `13f` tables already here
(text → holdings, and the extracted version is on disk as ground truth),
courtlistener opinions in full text rather than as a citation map.

The SEC one is the cheapest and the strongest: **the ground truth is already in
this repo**, as the 3.8M-row holdings tables. Only the raw filings are missing.

## Reproduce

```bash
uv run python -u scripts/extraction_breakeven.py     # instant; arithmetic only
```

`runs/extraction_breakeven.json`. Every input is a number already published and
is named in the script beside the finding it came from.
