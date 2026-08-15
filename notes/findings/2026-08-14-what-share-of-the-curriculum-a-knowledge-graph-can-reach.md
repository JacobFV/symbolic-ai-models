---
date: 2026-08-14
author: agent-kg-seam
status: provisional
related: [2026-08-14-semantic-constraint-from-a-knowledge-graph,
          2026-08-14-the-curriculum-has-one-object-sort,
          2026-08-14-five-of-seventeen-node-types-are-dead,
          2026-08-13-vendor-verbatim-rather-than-rename]
---

# A knowledge graph can reach two thirds of the lessons and a twentieth of the nodes

Rule 3 of
[[2026-08-14-semantic-constraint-from-a-knowledge-graph]] says to measure
coverage **before** building models on it, because macro-averaging over lessons
that did not change dilutes any effect to nothing and that is a fact you need
before anyone interprets a number. This is that measurement. It was taken twice:
once as a property of the curriculum with no graph in the room, and once as what
the graph actually vendored here does to it.

**Full 179 lessons in both passes.** Training seeds only (0-7 for the static
pass, 0-3 for the binder pass). No slice.

## The headline

| | strict | wide | actually reached |
|---|---:|---:|---:|
| lessons with a graph-addressable word anywhere | 55 (30.7%) | **121 (67.6%)** | **54 (30.2%)** |
| lessons whose *answer* is such a word | 16 (8.9%) | 27 (15.1%) | — |
| share of graph nodes carrying such a word | 4.19% | **10.00%** | **5.30%** |
| macro mean over lessons of answer share | 6.70% | 12.15% | — |

Read the last column first, because it is the one a sweep is going to be
divided by. **The vendored graph changes 54 of 179 lessons and 5.3% of all graph
node labels** (2,640 of 49,843 over 716 episodes). Everything else in every
episode is what it always was.

So an effect confined to what the graph touches arrives at the 179-lesson macro
average multiplied by roughly **0.05 on the node task**. A lift of 0.10 where the
graph reaches is a lift of 0.005 in the table. That is the number to hold in
mind before reading any of the three arms, and it was measured before they ran.

## What the two passes mean and why they differ

**Pass 1 — the curriculum's own vocabulary.** Every module-level closed word
list in `symbolic_ai_data/generators/` was classified by hand into three kinds:
real English words a WordNet-shaped graph has entries for (`COLORS`, `SHAPES`,
`semantics.OBJECTS`, `social.DETECT_CLASSES`, …), proper names (`NAMES`,
`ontology.PERSONS`, `epistemics.SOURCES`), and things nothing outside this repo
has an opinion about (`ontology.TYPE_NAMES` = `kes, mor, tav …`,
`OPTION_LABELS`, `social.WORDS`). Then every implemented lesson was generated at
eight seeds and its leaves matched against the first set.

The classification is a judgement, so it is reported as a **range** rather than
a point. `STRICT` is 69 concrete nouns and adjectives; `WIDE` is 180 words and
also counts verbs, directions, sizes and technical-but-English labels like
`selfmodel.SKILLS`. One word (`table`) is in both a real list
(`semantics.LOCATIONS`) and a nonce-ish one (`ontology.ENCODINGS`); it is
counted as real and the overlap is printed rather than hidden.

**Pass 2 — what the graph did.** `kg:wordnet` versus `base`, episode by episode,
counting labels that differ.

**The gap between 67.6% and 30.2% is not error, it is scope.** Pass 1 asks what a
graph *could* address; pass 2 asks what this seam *does* address, which is the
seven generator modules whose word lists were made bindable (`base`, `extra`,
`semantics`, `social`, `selfmodel`, `ontology`, `reflective`). The remaining gap
is mostly `epistemics` and the label vocabularies, and closing it is a data
change — one more row in `SLOT_SOURCES` — not a design change.

## The part of the gap that should not be closed

A large share of the curriculum's symbols are nonce **on purpose**.
`ontology.TYPE_NAMES`, `B_CONCEPT_NAMES`, `social.WORDS` and the `_nonce`
helpers exist because `lexical_novelty` is a declared difficulty axis and those
lessons are *about* learning a word you have never seen. Binding them to real
English would not enrich those lessons, it would delete what they teach.

So "5.3% of nodes" is not simply a to-do. Some meaningful fraction of the
curriculum is unreachable by any knowledge graph by design, and the honest
ceiling for this line of work is lower than 100% for a reason that is a feature.

## One exclusion, found the loud way

`name` is not bound and cannot be, on this graph. WordNet has no proper names,
so the six people would have to become occupations — and the language packs key
on the *specific* six words: `pronoun_coreference` reads `gender()[n]` for every
`n in NAMES` and raises `KeyError: 'initiator'`. The failure is loud, which is
the good case. What it says is that a name in this curriculum is **not a free
variable at all** but a key into a hand-written lexicon, and that binding it
needs a graph that carries people. It shows up in the binder's own fallback
table as a slot that falls back 95 times out of 95.

## The measurement that matters more than the coverage number

**The manipulation is symbols-only on 99.86% of episodes, and the exception has
a name.**

By construction every bound value is chosen by *indexing* into a candidate set
with the position the ordinary uniform draw already produced, never by a fresh
`rng` call, so the scene size, the coordinates, the question and the answer's
identity should be the ones the baseline drew. Without that, a score difference
between arms would be a difference in tree shapes and no reading of it would be
possible.

Checked, rather than assumed, on **179 lessons x 12 seeds** — eight training and
four eval — comparing `graph.types` and `graph.parent` cell by cell:

| | |
|---|---:|
| episodes compared, `base` vs `kg:wordnet` | 2,148 |
| episodes whose tree shape moved | **3 (0.140%)** |
| lessons involved | 3 (`symbol_grounding`, `ontology_revision`, `symbolic_generalist`) |
| total graph nodes, `base` | 148,814 |
| total graph nodes, `kg:wordnet` | 148,852 (**+0.026%**) |

### Why it is not zero, which is the interesting half

The first version of this note said "zero of 716", measured at four seeds. It is
zero at four seeds and it is not zero in general, and the mechanism is worth
more than the number.

**A rejection loop's acceptance test depends on the symbols drawn.**
`symbol_grounding` redraws its scene until the query uniquely identifies one
object; under the KG the attribute is constrained by the kind, so two objects
collide more often, so the loop rejects more often, so the accepted scene is a
different size. At seed 4 it is three objects in `base` and five under the KG —
25 nodes against 37.

Nothing about "consume the same random bits" can prevent this. The stream is
identical; what differs is how many times it is *drawn from*, because the
generator itself is looking at the values. Any lesson that filters on symbol
equality will diverge, and the only way to make it not diverge would be to
remove the constraint that is the whole point.

So the honest statement is: the arms differ in symbols and, on about one episode
in seven hundred, in one scene size. 38 extra nodes in 148,814. It is far too
small to carry a score difference and it is not zero, and both halves of that
sentence belong in any write-up of the arms.

(A second, smaller mechanism was seen during development and is not in the count
above: a lesson that spells a word into a `Str` field gets one graph node per
character, so a longer word is a longer graph. `few_shot_language_learning` did
this at one seed, 49 nodes -> 55. It cannot be fixed without length-matching the
vocabulary.)

## The graph, and its control

Vendored: **Princeton WordNet 3.0**, via the NLTK redistribution
(`sha256 cbda5ea6…`, 10,775,600 bytes), projected to the physical lexicographer
files under a rule stated in `symbolic_ai_kg/_vendor.py` and committed as
250,981 bytes gzipped (`sha256 8b456c5d…`). License permits redistribution with
the notice; the notice is in `symbolic_ai_kg/data/LICENSE.wordnet`.

| | nodes | edges | isa | similar | part | antonym | attr | substance | member |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `wordnet` | 13,810 | 18,926 | 10,442 | 5,622 | 1,408 | 652 | 623 | 156 | 23 |
| `wordnet-shuffled` | 13,810 | 18,926 | 10,442 | 5,622 | 1,408 | 652 | 623 | 156 | 23 |

The census is **identical**, which is the point. 7,174 nouns, 3,200 verbs
carrying WordNet's own sentence frames, 3,436 adjectives.

The control is a degree-preserving double-edge swap, per relation, with the
`isa` swaps constrained to a fixed topological order of the original DAG so the
taxonomy stays acyclic. Per-node in-degree and out-degree are identical in every
relation (asserted node by node in `tests/test_kg.py`). Share of original edges
surviving, at seed 20260814 and 20 attempts per edge:

| relation | edges | swaps | kept | kept share |
|---|---:|---:|---:|---:|
| `similar` | 5,622 | 111,199 | 14 | 0.0025 |
| `antonym` | 652 | 12,979 | 3 | 0.0046 |
| `attr` | 623 | 12,413 | 3 | 0.0048 |
| `part` | 1,408 | 27,979 | 10 | 0.0071 |
| `substance` | 156 | 3,025 | 2 | 0.0128 |
| `isa` | 10,442 | 41,224 | 212 | 0.0203 |
| `member` | 23 | 393 | 3 | 0.1304 |

`isa` keeps more than the rest because the acyclicity constraint rejects swaps;
`member` has 23 edges and a swap needs room. Both are reported rather than
averaged away.

## What the binder actually binds

An episode anchors a **family** (a graph node with 8-120 descendants within
three hyponym hops, about which the graph says at least four *different*
things — 157 such families on this graph), and then:

* `kinds` are the family's descendants — **bound**;
* `things` come from a *sibling* family — **bound**;
* animacy is **derived** from the taxonomy, and the verb slots are filled from
  the verbs whose WordNet frames admit a subject of that animacy — **bound**;
* each scene object's second attribute is drawn from the subset of the episode's
  attribute vocabulary that the graph licenses **for that object's own kind** —
  its parts and its substances. 170 of 320 scene objects (53.1%) got a
  kind-constrained attribute; the rest fell back because the graph had nothing
  to say about that kind.

Fallback rates over 179 lessons x 4 seeds, per slot: `name` 95/95 (excluded, see
above), `material` 8/8 and `substance` 8/8 (WordNet's substance meronymy is 156
edges and simply too sparse), everything else **0**.

### The failure this coverage pass caught, which a score would not have

The first version drew the kinds as the family's **direct children**. WordNet
states meronymy at the parent and does not restate it at each child, so six
siblings inherit one identical part list — and every object in a scene drew its
"constrained" attribute from the same one-element candidate set. The dependency
edge existed and did nothing.

Nothing about the resulting curriculum looked wrong. It generated, it differed
from the baseline, its control differed from it, and every fingerprint and shape
guard passed. What caught it was an assertion written to say the thing the
design claims —
`test_two_objects_of_different_kinds_draw_from_different_candidate_sets` — which
failed with `[frozenset({'merchandise'}) x 6]`. Reaching three levels down
instead of one fixes it, at the cost of less coherent families.

This is the shape of
[[2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property]] again: a
mechanism that is present and inert looks exactly like a mechanism that is
working, and only an assertion of the *claim itself* separates them.

## What would have refuted this note

* **Coverage near zero.** If fewer than ~5 lessons had a graph-addressable word,
  the whole line dies here and no model needs to be trained. It did not happen;
  54 lessons is enough to measure and too few to expect a large macro effect.
* **Coverage near total.** Would have meant the curriculum is mostly real words
  and the "one object sort" diagnosis was about something else. Also did not
  happen — 5.3% of nodes.
* **A tree shape moving.** Would have meant the manipulation is confounded with
  structure and the arms are not comparable. Three of 2,148, +0.026% of nodes,
  with a named mechanism — see above. The threshold I would have called
  disqualifying is 1% of episodes or 0.5% of nodes; this is an order of
  magnitude under both, and it is reported rather than rounded to zero.
* **The control's census differing from its treatment's.** Would have meant the
  control also changes density and cannot isolate meaning. Identical.

## What this note does *not* say

It does not say the semantics helped, or that anything reorders. Nothing here is
a score. The three arms (`runs/kg179-base`, `runs/kg179-wordnet`,
`runs/kg179-shuffled`) are what will answer that, and this note exists so that
whatever they say is read against a 5.3% denominator rather than a 100% one.
