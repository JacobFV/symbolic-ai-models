---
title: Geography recovers 81% of the damage that admitting ambiguous candidates does, and never gets ahead of abstaining — a second view informative enough to undo a mistake and not to be worth making one
date: 2026-08-18
author: lead
status: provisional
tags: [composition, multi-kernel, extraction, ror, openalex, negative-result, slices]
---

## The claim under test

The previous finding diagnosed the extraction plateau and I promoted the
diagnosis to the top of `HANDOVER.md` §7 as *"the single highest-value arm in the
repo right now"*:

> One string in 6,489 produced no candidate. The extractor is not failing to
> **find** institutions, it is failing to **choose** — "University of Wisconsin"
> names thirteen ROR campuses, and the string carries exactly what separates them
> (*Madison*, *Lancaster*, *Karlsruhe*), which nothing reads, because they match
> names against names and **geography is a different view of the world**.

Built as a genuine composition rather than a better matcher, and with the control
that decides between the two written first:

    NAME view   proposes every ROR id whose registry name matches a component,
                including the ambiguous ones the earlier rungs discarded.
    GEO view    disposes, scoring each candidate's ROR-recorded city,
                subdivision and country against the places the string names.

**It does not work, in any of three constructions.**

## Measured, three splits, means

| variant | mean F1 unseen | vs v6 |
|---|---:|---:|
| **v6** names only, abstains on ambiguity | **0.618** | — |
| B — abstention relaxed, **no** geography | 0.582 | **−0.036** |
| v7 — abstention relaxed **+** geography | 0.611 | −0.007 |
| v8 — v6's abstention kept, geography may only **admit**, and only on city or subdivision evidence | 0.617 | −0.001 |

The ablation is the finding. **Relaxing abstention costs −0.036. Geography
recovers +0.029 of that — 81%. It never gets ahead.**

> **The second view is informative enough to undo a mistake and not informative
> enough to be worth making one.**

**The control, written before the run:** geography changed the answer on
**9.8%** of unseen strings and was better on **23.0%** of them, worse on
**46.4%**, neither on 30.6%. That is what a decoration looks like when you
measure it instead of reporting the F1 and calling it neutral.

## Why it fails, and it is not that geography is uninformative

**65% of ambiguous components — 2,227 of 3,429 — carry no geographic evidence at
all.** The string names no place ROR records at the granularity needed. Where
geography does speak it is useful, which is why it recovers 81% of the
relaxation's damage; there is simply not enough of it, and the flat version made
things worse still by counting a country match (`usa`, which every US institution
matches) the same as a city.

## The part worth more than the result

**I designed this arm from five printed examples.** The error breakdown sampled
five of 1,251 disjoint cases; all of them named a city; the diagnosis wrote
itself and went to the top of the roadmap. The population does not look like the
sample, and the number that would have said so — the 65% — was computable from
the same breakdown, before any of the three variants existed.

That is a **slice inversion**, which is this repo's oldest and most expensive
documented mechanism, and I walked into it while writing a finding that cites the
abstention lesson twice. Lesson recorded separately at
`notes/lessons/2026-08-18-i-designed-an-experiment-from-five-printed-examples.md`,
with the guard: *a diagnosis derived from a slice must be sized on the population
before it is built on.*

## What this leaves standing

- **The extraction plateau is a harder number than it was.** ~62% of a 0.99
  ceiling now survives a serious attempt at its diagnosed cause. It is no longer
  "nobody tried the obvious thing".
- **Composition is not free.** The multi-kernel claim in `APPROACH.md` is that a
  second view changes what the first does. It did — on 9.8% of answers — and was
  wrong about it twice as often as right. **A second view has to beat
  abstention, not merely beat guessing**, and that is a higher bar than the
  architecture makes it look.
- **Abstention wins for the third time today.** The word-overlap fallback (v2),
  the relaxed admission (B), and this: three separate mechanisms this session
  where guessing where the system knows least cost more than it bought.

## What would refute it

- **A better geo signal.** Only ROR's `city`/`subdivision`/`country` strings were
  matched. Postcodes, street addresses and GeoNames alternate names are all in
  the input or reachable, and would raise the 35% of components where geography
  speaks. The ceiling on any such method is that coverage number, which is the
  quantity this finding says to measure *first*.
- **A different corpus.** Affiliation strings are short and postal. Sentence-level
  extraction — the CourtListener task still blocked on a free token — may carry
  far richer disambiguating context.
- **The anchor is still agreement with OpenAlex**, not truth, as in every finding
  in this arm.

## Reproduce

```bash
SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \
  uv run python -u scripts/first_arrow_geo.py
```

Rows in `runs/first_arrow_geo.json`; prediction, ablation and outcome in
`notes/autonomy/predictions.jsonl` under `geo-disambiguates-entity-linking`.
