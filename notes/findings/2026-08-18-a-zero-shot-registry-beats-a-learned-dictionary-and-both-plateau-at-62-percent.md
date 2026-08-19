---
title: A zero-shot registry lookup beats a dictionary learned from 3,500 works, on all three splits — and every symbolic rung plateaus at 62% of a 99% ceiling, because the failure is not finding candidates but choosing between thirteen University of Wisconsins
date: 2026-08-18
author: lead
status: provisional
tags: [extraction, openalex, ror, gazetteer, external-resources, cost, negative-result]
---

## The question

`notes/findings/2026-08-18-the-first-arrow-is-cheap-and-bad.md` (§D bis) localised
the first arrow's failure exactly:

- the label **is** a function of the input — a memoriser handed verbatim-seen
  strings scores **98.2% exact**, so the task has essentially no noise;
- **91.6%** of held-out authorship strings were never seen verbatim;
- the best learned extractor reached **48.9%** of that ceiling.

So the entire residual is generalising to an unseen *wording*. That is a
**knowledge** problem before an algorithm problem — and this repo's stated
principle is that **external resources are givens**: use the real standard rather
than re-deriving it. ROR publishes **135,710** institutions with 449,658 name
variants (labels, aliases, acronyms, multilingual), CC0 and unauthenticated.

This is the first time that principle has been tested on something the
programme's thesis depends on.

## Result

Three splits, because the ladder had by then been iterated six times on one and
that is exactly the trap `CLAUDE.md` names — settling design choices by reading
evaluation. The tuning debt is therefore **measured rather than asserted**.

| rung | seed 20260818 *(the tuned one)* | 777001 | 1234567 | **mean % of ceiling** |
|---|---:|---:|---:|---:|
| v0 learned component vote | 0.378 | 0.366 | 0.394 | 38.2% |
| v3 best learned rung | 0.483 | 0.435 | 0.494 | 47.4% |
| **v4 zero-shot registry** | **0.522** | **0.538** | **0.553** | **54.2%** |
| v5 registry + learned | 0.577 | 0.580 | 0.624 | 59.8% |
| **v6 + abbrev & containment** | 0.587 | 0.625 | 0.643 | **62.3%** |
| *ceiling (measured per split)* | *0.988* | *0.991* | *0.998* | *100%* |

**The ordering is identical on all three splits**, and the split the ladder was
built on gives the **lowest** v6 of the three — so there is no evidence the
iteration bought anything on its own split. That was worth checking and it is
the opposite of what I expected to find.

### The positive result: knowledge beats data, with no data at all

> **A zero-shot registry lookup — no training split, no learned dictionary, no
> fitted parameter — beats the best dictionary learned from 3,500 works on every
> split**: +0.039, +0.103, +0.059. It also runs in 41,668 ns against 96,915.

v4 is the only rung with nothing to tune, which makes its number trustworthy in
a way the others' are not. The learned dictionary was never the point.

### The negative result: it plateaus at 62% of 99%

Six rungs, an authoritative registry of every institution there is, abbreviation
expansion, and containment matching, and **38% of an achievable ceiling remains
unreached**. The ceiling is 0.99, so that shortfall is real and not noise.

## Why — and it is not what the rungs were built for

Error breakdown of v6 on the 6,489 unseen strings:

| | count | share |
|---|---:|---:|
| exact | 3,009 | **46.4%** |
| disjoint — every prediction wrong | 1,251 | 19.3% |
| subset — missed some | 1,053 | 16.2% |
| superset — over-predicted | 604 | 9.3% |
| partial overlap | 571 | 8.8% |
| **predicted nothing** | **1** | **0.0%** |

**One string out of 6,489 produced no candidate.** The extractor is not failing
to *find* institutions. It is failing to *choose* between them, and 38.2% of true
institutions are never proposed because a near-identical name was proposed
instead.

The disjoint cases say it plainly:

```
Department of Materials Science and Engineering, University of Wisconsin,
  1509 University Avenue, Madison, WI 53706, USA
Department of Biological Sciences, University of Lancaster, Bailrigg, Lancaster
Botanisches Institut der Universität, Kaiserstraße 12, Karlsruhe, Germany
```

"University of Wisconsin" names thirteen campuses in ROR. The string contains
exactly what distinguishes them — **Madison**, **Lancaster**, **Karlsruhe** — and
the extractor never looks at it, because it matches names against names and
geography is a different view of the world.

**That is the multi-kernel thesis stated as a bug.** ROR's dump carries
`locations` with city and country; the affiliation string carries a city; nothing
in six rungs joined them. The next arm is a geo constraint on an entity-linking
candidate set, and it is the first place in this repo where two views would
genuinely have to compose to answer one question.

## What this does and does not license

- **It does not** say symbolic extraction reaches 62%. It says *these six rungs*
  do, and the diagnosis names a seventh that is neither exotic nor learned.
- **It does** say the strong form of "cheap structured computation replaces the
  model" is unproven on this arrow. 62% of ceiling builds a world with roughly
  four wrong or missing institutions in ten.
- **The anchor remains agreement, not truth.** OpenAlex's resolution is itself an
  automated extractor; every number here is agreement with it.
- **Using ROR's names to predict ROR ids is a registry lookup**, not a general
  text-to-entity method, and v4's win should be read as "the right reference data
  beats a learned proxy for it", which is a narrower and more useful claim.
- **v6 is nondeterministic by ±0.002** — ties in containment matching are broken
  by set iteration order. Immaterial at this resolution and named rather than
  hidden.

## Reproduce

```bash
uv run python -u scripts/fetch_openalex_prose.py --works 5000
SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \
  uv run python -u scripts/first_arrow_gazetteer.py
```

The ROR dump is at `data/sources/ror/ror-v2.11-2026-08-03/` (Zenodo record
21773148, CC0). Rows in `runs/first_arrow_gazetteer.json`; predictions and
outcomes in `notes/autonomy/predictions.jsonl` under
`gazetteer-closes-the-extraction-gap`.
