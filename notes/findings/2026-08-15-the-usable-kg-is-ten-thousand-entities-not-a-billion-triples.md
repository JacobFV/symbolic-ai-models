---
date: 2026-08-15
author: lead
status: provisional
related: [2026-08-14-semantic-constraint-from-a-knowledge-graph,
          2026-08-14-the-label-score-is-a-copy-score,
          2026-08-13-the-harness-moves-more-than-the-models]
---

# The corpus is 1.2 billion triples and 9,849 of its entities are usable

Measured before building anything, because the previous KG arm returned a null
nobody could interpret and the arm before it priced its reach only afterwards.

## What the corpus is

26 sources, **1,214,852,868 triples**, 247 distinct relation kinds, 18 id
namespaces (`kg/sources/manifest.json`). The first finding was that the plan did
not fit the data: **there is no unstructured text in it.** Every source is
already `(source_id, target_id, kind)` — Gutenberg and StackExchange included,
which are edge lists over catalogue entries rather than prose. The intended
local-LLM fact-mining path has nothing to mine, so the entire job is
normalisation.

Five priority sources normalised into one vocabulary and one id space:
**21,715,580 triples**, provenance on every row (`kg/normalized/v2/manifest.json`).

## The number that gates the line

A derivability curriculum needs an entity that is **both** anchorable — something
says what it is, so a lesson can bind it — **and** carries a *determined*
attribute, so a slot can follow from the anchor instead of being drawn. Either
alone is useless: a type with no consequences gives a slot nothing to derive, and
properties with no type cannot be anchored.

| | count |
|---|---:|
| triples normalised | 21,715,580 |
| entities anchorable (`is-a` / `instance-of`) | 732,339 |
| entities with a determined attribute | 78,642 |
| **both — the usable population** | **15,977** |
| of those, single-valued | **9,849** |

**The two relation families barely overlap.** 732K entities have a type and 79K
have a determined property, and their intersection is 16K — 2.2% of the
anchorable set, and **0.07% of the triples read**. The graph carries deep
taxonomy *or* rich properties, rarely both on the same node.

## The reading, and it cuts both ways

**Good enough to proceed.** 9,849 cleanly single-valued entities is far more than
a curriculum needs — the present one runs on **eighteen** words (six colours, six
shapes, six names). A derivability arm is not blocked by supply.

**And it kills the case for normalising the rest.** The remaining ~1.19 billion
rows are overwhelmingly citation structure — `cites` alone is 327M across four
sources, `scholar` is 430M — and a citation is neither an anchor nor a
determiner. Normalising it would add hundreds of millions of edges and **zero**
usable entities. The bulk of this corpus is irrelevant to the only thing the
repo currently needs from a knowledge graph.

That is the same shape as the finding that preceded it: coverage of the
curriculum's vocabulary was already ~100% and WordNet's 13,810-node projection
already reached it. **Twice now, "get more graph" has been measured to be the
wrong prescription.** What was missing was never facts; it is that nothing in the
curriculum is derivable *from* facts.

## What would refute this

- **The overlap is an artefact of the five sources chosen.** `entity` (Wikidata,
  260M rows) is not yet normalised and is the most likely source of nodes
  carrying both a type and properties. If it lifts the intersection by an order
  of magnitude the "don't normalise the rest" conclusion weakens — though the
  citation bulk is unaffected either way. **This is the cheapest test and it has
  not been run.**
- **Single-valued is the wrong criterion.** An entity whose relation has several
  objects may still be derivable if the lesson supplies enough context to pick
  one. That would raise 9,849 toward 15,977 and does not change the order of
  magnitude.
- **Anchorability is under-counted.** Only `is-a` and `instance-of` count here.
  If `member-of`, `part-of` or `classified-as` are admissible anchors the base
  grows — but those were kept out deliberately, since a lesson that binds "this
  is part of a car" does not thereby determine a colour.

## What this does not say

It does **not** say semantic constraint will work. The first arm's null was
uninterpretable because its control could not fail, and that experiment is being
rebuilt. This says only that **if** derivability is worth testing, the graph can
supply the entities to test it with, and that supplying more of them is not where
the remaining effort should go.
