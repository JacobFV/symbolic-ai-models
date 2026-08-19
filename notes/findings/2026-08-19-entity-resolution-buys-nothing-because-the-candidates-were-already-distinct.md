---
title: Entity resolution buys nothing here, because the candidates were already distinct
date: 2026-08-19
status: measured
arm: candidate-semantics
corrects: >
  "Entity resolution and entity typing are the missing capability for real text,
  named from three directions." One of the three routes is refuted outright and
  the mechanism behind it was wrong.
---

## The hypothesis, supplied as a given rather than built

Three failures had been read as pointing at entity resolution, and the strategic
frame said to use an existing structured resource as a **given** and then rerun
the particular hypotheses resolution is supposed to affect. So: every candidate
resolved to a Wikidata QID with its aliases — **identity only**, `P749` never
consulted — and the three hypotheses re-run.

## The candidates were already distinct

86 candidate pairs across 40 multi-candidate articles:

| relation | pairs | share |
|---|---:|---:|
| **distinct entities** | 45 | **0.523** |
| unresolved (one side has no QID) | 40 | 0.465 |
| **same entity** | **1** | **0.012** |

**I predicted 40–60% same-entity. It is 1.2%.** The *Sony Music Entertainment* /
*Sony Music Group* and *Amazon MGM Studios* / *Amazon* examples were memorable and
**unrepresentative**. When a company intro names two owners, they are usually two
genuinely different organisations.

## So none of the three hypotheses moves

| policy | coverage | correct | **precision** |
|---|---:|---:|---:|
| first match | 0.589 | **0.369** | 0.626 |
| + **string** corroboration | 0.429 | 0.310 | **0.722** |
| + **entity** corroboration (aliases) | 0.458 | 0.321 | **0.701** |
| string agreement | 0.369 | 0.220 | 0.597 |
| **same-QID** agreement | 0.262 | 0.143 | **0.545** |

- **Entity-level corroboration is worse than string-level** (0.701 vs 0.722).
  Counting a candidate's aliases adds matches from text about something else.
- **Same-QID agreement is worse than string agreement** (0.545 vs 0.597), and both
  are worse than first match. Requiring resolution *and* agreement compounds two
  filters, and 31% of candidate strings resolve to nothing at all.

## The mechanism, corrected

The published explanation for agreement's failure was that *"names are not
resolved — Sony Music Entertainment and Sony Music Group are one answer at two
granularities."* That is **wrong as a general account**, and the pair taxonomy is
the refutation.

> **Agreement fails because the facts are genuinely plural, not because identity
> is unresolved.** A company intro names former owners, sibling companies and the
> subject's own subsidiaries. Those are distinct real relationships, so there is
> no exclusivity for agreement to exploit — and no identity to recover either.

That is a simpler and better mechanism, and it changes what would help. Resolving
names cannot manufacture exclusivity that the world does not have. What *would*
help is knowing which **relation** each mention asserts — current versus former,
parent versus sibling versus child — which is relation typing, not entity
resolution.

## What survives of the earlier claim

Of the three routes that named entity resolution:

1. *agreement fails because names are unresolved* — **refuted**, 1.2% same-entity;
2. *ranking fails because non-entities are unfiltered* — **partly true**: real
   Wikidata typing lifts the ranker 0.535 → 0.638, its largest single gain, and it
   still loses to first match at 0.681;
3. *the signature discipline works only because entities are named `region_0`* —
   **stands**, but that is entity **typing**, not resolution.

So the corrected statement is **entity typing helps a little and entity
resolution buys nothing here** — and the thing actually missing is relation
typing.

## What would refute this

- One relation family and one genre. A task whose candidates *are* competing
  readings of one fact — a date, a quantity, a single-valued attribute — would
  restore exclusivity and with it agreement's meaning.
- 31% of candidates do not resolve, and unresolved pairs are 46.5%. A better
  resolver moves the taxonomy, though it would have to move it a very long way to
  reach 40%.
- Aliases were capped at eight per entity; a longer list would add both signal and
  noise, and the direction it moved is the one that says noise dominates.
