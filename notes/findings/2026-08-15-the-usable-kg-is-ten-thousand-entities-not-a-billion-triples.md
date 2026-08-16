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

## The named refutation was run, and it confirmed the finding 163x over

The condition written above before the run: *if Wikidata lifts the intersection
by an order of magnitude, the "don't normalise the rest" conclusion weakens.*
`entity` was then normalised — 259,773,342 rows seen, **194,756,799 kept** — and
the measurement repeated over all 216M triples:

| | 5 sources | + Wikidata | change |
|---|---:|---:|---:|
| triples read | 21,715,580 | 216,472,379 | **+194,756,799** |
| entities anchorable | 732,339 | 119,125,858 | **+118,393,519** |
| with a determined attribute | 78,642 | 78,642 | **+0** |
| **both — usable** | **15,977** | **15,977** | **+0** |
| single-valued | 9,849 | 9,849 | **+0** |

**A 163-fold increase in anchorable entities bought exactly zero usable ones.**
Not "a small gain" — the intersection is identical to the entity, and so is the
single-valued subset.

The mechanism is plain once seen. Wikidata's backbone here is `is-a`,
`instance-of` and `same-as`: taxonomy and identity. **Determined attributes come
almost entirely from CSKG/ConceptNet, which is 3.98M rows in total** — 1.8% of
the corpus now normalised, and the source of essentially every `has-property`,
`capable-of`, `used-for` and ATOMIC if-then edge in it.

So the scarce resource is not entities, not types, and not scale. It is
**statements about what follows from being something**, and general-purpose
knowledge graphs are not built to carry them. The conclusion is stronger than
what it replaced: normalising the remaining ~1 billion rows is not merely poor
value, it is measured to be worth nothing at all for this purpose.

## Correction: "coverage is ~100%" had a 69-word denominator

I wrote, here and in `RESEARCH_LOG.md`, that *"coverage of the curriculum's
vocabulary is already ~100%"* and used it to argue that more graph is the wrong
prescription. **The denominator was a hand-classified subset**, and I never said
so. `scripts/kg_coverage.py` builds three tables by hand — `STRICT` (69 words),
`WIDE` (180), `PROPER` (14) — and the headline is 100% of `STRICT`.

The repo ships an importable enumerator that nobody had pointed at the question:
`curriculum_vocabulary()` returns **423** words the generators can coin, and
`rendered_vocabulary()` **749** including field names that reach the page.
`WIDE ∪ PROPER` is 194 and a strict subset of the 423, so **229 coinable words
were never measured.**

Re-run against the real denominators and the 60.6 M normalised node labels —
which the first pass could not do, having thrown the node tables away
(`scripts/kg_coverage_full.py`, `kg/normalized/v2/stats-vocab.json`):

| | 423 coinable | 749 rendered |
|---|---:|---:|
| carries a label in the graph | 374 (**88.4%**) | 648 (86.5%) |
| that node is anchorable | 271 (64.1%) | 443 (59.2%) |
| **anchorable AND has a determiner** | **62 (14.7%)** | 97 (13.0%) |

**88.4%, not ~100%. And the number that matters is 14.7%.**

**The conclusion survives, and the reason I gave for it was wrong.** I argued
"coverage is complete, so a bigger graph cannot help". The truth is that coverage
of *determiners* is only 14.7%, so on its face there is enormous headroom — 85%
of the curriculum's words have no statement of what follows from them.

What closes that door is not coverage but the Wikidata result in the section
above: **+194,756,799 triples, +118,393,519 anchorable entities, +0 with a
determined attribute.** The headroom is real and **scale provably does not
reach it**, because general knowledge graphs carry taxonomy and identity rather
than consequences. That is a stronger claim than the one it replaces and it does
not rest on a hand-picked denominator.

Also noted by the agent that found this: `_words()`'s docstring in
`kg_coverage.py` claims every module-level closed word list in
`symbolic_ai_data/generators/` is in exactly one of its three tables. That is
**false as written** — `semantics.THINGS` and `ontology.VERB_ISA` are in none.

## The full corpus, and the number is 610x more sensitive to a definition than to scale

Re-measured on the complete normalised graph — **1,115,841,226 triples**, 5.2x
what the section above used:

| | v2, 216 M | v5, 1.116 B | change |
|---|---:|---:|---:|
| anchorable | 119,125,858 | 119,510,066 | +384,208 |
| with a determined attribute | 78,642 | 75,656 | −2,986 |
| **usable** | 15,977 | 15,495 | −482 |
| single-valued | 9,849 | **9,368** | **−481** |

**899 million additional edges moved the usable population by −481.** The sign is
negative because `has-part` became its own canonical in schema v3 — split out
when the `part-of` inverse-pooling bug was fixed — and is not in the determiner
set, so a few entities lost their only determiner to a *definition* change.

Adding it back, which the previous agent wired as an explicit arm precisely so
the two causes stay attributable:

| | v5 | v5 + `has-part` |
|---|---:|---:|
| with a determined attribute | 75,656 | **1,012,883** |
| usable | 15,495 | **944,007** |
| single-valued | 9,368 | **302,792** |

**+293,424 from one line of definition, against −481 from 899 million edges.**
The usable population is roughly **610x more sensitive to what counts as a
determiner than to a five-fold increase in corpus size.** That is the finding;
the 9,849 was never a property of the corpus alone and should not have been
quoted as one.

**And the narrow definition is the right one, for a reason worth having rather
than the accident it started as.** `has-part` here is 4.39 M edges from Wikidata,
and the majority original kind is **`contains-admin`** — administrative
containment. Two checks settle it:

* *It is instance-level, not kind-level.* Knowing something is a country does not
  determine which regions it contains. A determiner must be "what follows from
  being **this kind**"; `France contains-admin Île-de-France` is a fact about one
  entity, and nothing about the kind implies it.
* *Its entities are lexically unreachable.* Sampled subjects and objects —
  `Q205104`, `Q2088824` — **appear in no node table at all**, so they carry no
  label. They cannot join to a curriculum whose vocabulary is words, whatever
  the definition says.

So the exclusion stands, `9,368` is the number for kind-level derivability, and
the word-level join is unaffected either way because these entities have no
labels to join on.

## What would still refute it

- **Single-valued is the wrong criterion.** An entity whose relation has several
  objects may still be derivable if the lesson supplies context enough to pick
  one. That moves 9,849 toward 15,977 and does not change the order of magnitude.
- **Anchorability is under-counted.** Only `is-a` and `instance-of` count. Adding
  `member-of`, `part-of` or `classified-as` grows the base — but the base is
  already 119M and is demonstrably not the constraint, so this cannot matter.
- **A property-dense source nobody has looked at.** The remaining unnormalised
  sources are citation, patent-classification and financial-holding structure.
  If one of them carries `has-property`-shaped edges at scale it would move the
  number; none of their sampled relation vocabularies suggests it.
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
