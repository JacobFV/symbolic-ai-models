---
title: Corroboration counts strings, not entities
date: 2026-08-19
status: measured
arm: corroboration-as-ranker
---

## Spending the same information better should have worked

Corroboration is a **filter**: answer only when the candidate is mentioned twice,
which buys precision (0.626 → 0.718) by giving up coverage (0.589 → 0.423). But
the reader still picks `candidates[0]` — the *first* match, which is document
order, and which is the branching the packing work said not to do.

So: accumulate instead. Cluster the candidates by shared core token and answer
with the **most-mentioned** cluster. Same information, no coverage given up.

| policy | coverage | correct | **precision** |
|---|---:|---:|---:|
| first match (published) | 0.589 | **0.369** | **0.626** |
| first match, corroborated only | 0.423 | 0.304 | 0.718 |
| **ranked by corroboration** | 0.589 | **0.315** | **0.535** |
| ranked + corroborated only | 0.440 | 0.262 | 0.595 |

**Ranking is worse than taking the first match** — 0.535 against 0.626. Not equal:
worse.

## And the reason is not the one I guessed

I predicted the ranker would prefer **former** parents, on the grounds that
history is verbose and the current state is terse. It does not: of the 14 articles
where the two policies disagree, each picks a former parent exactly **once**.
First-match wins those 14 by **10 to 2**.

What the ranker actually picks:

```
EMI                       first: Universal Music Group   ranked: Sony Music Publishing
Blohm+Voss                first: Lürssen                 ranked: Rheinmetall
Hachette Livre            first: Lagardère Group         ranked: French
Deutz-Fahr                first: Klöckner-Humboldt-Deutz ranked: Italian
Canadian Pacific Railway  first: Canadian Pacific KC Ltd ranked: CPR
```

**Nationality adjectives and the subject's own abbreviation.** These are regex
noise, and they are mentioned often precisely *because* they are what an article
about a French company repeats.

> **Corroboration counts mentions of a string, not of an entity.** As a
> **threshold** it removes candidates too rare to be real, which is genuine
> information. As a **ranking** it selects for whatever the document repeats most
> — in an encyclopedia intro, the subject itself, its abbreviation and its
> nationality — every one of which the extractor has mistaken for an owner.

The filter survives this because it only *removes*; it still takes the first
candidate, and an intro leads with the current owner.

## Three routes, one missing capability

This is the third independent piece of evidence for the same gap:

1. **Agreement** fails because names are not resolved — *Sony Music Entertainment*
   and *Sony Music Group* are one answer that no string relation merges.
2. **Ranking** fails because non-entities are not filtered — *French* and *CPR*
   are not organisations and nothing here knows it.
3. The **signature** discipline works at all only because entities are named
   `region_0`, which is entity typing handed over for free.

**Entity resolution and entity typing are the missing capability**, and it is now
named from three directions rather than argued from one. A ranker over *plausible
organisations* is a different experiment and might well win; a ranker over regex
hits does not.

## What would refute this

- 14 disagreeing articles. The direction is 10–2 and the examples are diagnostic,
  but the margin rests on a small set.
- The clustering key is the first non-stopword token, so *Sony Music Publishing*
  and *Sony Music Entertainment* share a cluster while *Lagardère Group* and
  *Lagardère Publishing* also do — the key is doing some resolution already, and a
  better one changes both arms.
- The stoplist that produces *French* and *Italian* as candidates is the
  extractor's, not the ranker's. A capitalisation-plus-gazetteer filter would
  remove them and the comparison would have to be re-run.
