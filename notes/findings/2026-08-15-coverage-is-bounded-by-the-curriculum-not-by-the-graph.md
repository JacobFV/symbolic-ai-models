---
date: 2026-08-15
author: agent-kg-semantics
status: provisional
related: [2026-08-14-what-share-of-the-curriculum-a-knowledge-graph-can-reach,
          2026-08-14-semantic-constraint-from-a-knowledge-graph,
          2026-08-15-the-kg-arms-are-a-null-and-the-quarter-that-mattered-did-not-move,
          2026-08-13-vendor-verbatim-rather-than-rename]
---

# Two real knowledge graphs cover the curriculum's whole vocabulary, and the reach number does not move

Rule 3 of the decision note says measure coverage before building on a graph.
[[2026-08-14-what-share-of-the-curriculum-a-knowledge-graph-can-reach]] did that
for the vendored WordNet projection and got **55 of 179 lessons, 5.2% of node
labels**. A 14 GB knowledge graph then arrived — 3,054,055 nodes and 5,203,843
edges of semantic graph, plus CSKG's 3,975,177 commonsense assertions — and the
obvious question is whether the small graph was the limiting factor.

**It was not, and this is the finding.** Coverage of the curriculum's own
closed word lists is essentially total on all three graphs, and it was already
essentially total on the 13,810-node one. The 5.2% is a property of the
**curriculum's slot inventory** — how many of its symbols are drawn from a word
list a graph could bind at all — and no graph changes it.

## The measurement

The curriculum's module-level word lists, hand-classified in
`scripts/kg_coverage.py` into 69 `STRICT` concrete nouns and adjectives, 180
`WIDE` (adding verbs, sizes, directions, technical-but-English labels) and 14
`PROPER` names. Each word looked up as a node label, then asked whether it has
the neighbourhoods a binder needs.

| | `STRICT` (69) | `WIDE` (180) | `PROPER` (14) |
|---|---:|---:|---:|
| **semantic graph**, 3.05M nodes: present | 69 (100%) | 170 (94%) | 10 (71%) |
| … with an `is-a`/`instance-of` neighbourhood | 69 (100%) | 152 (84%) | 8 |
| … with `has-property`/`part-of`/`located-in` | 64 (93%) | 130 (72%) | 9 |
| **CSKG**, 3.98M rows: present as an English concept | 69 (100%) | 174 (97%) | 12 (86%) |
| … with an `/r/IsA` edge either way | 64 (93%) | 129 (72%) | 8 |
| … with an outgoing selectional edge | 42 (61%) | 92 (51%) | 7 |
| … with a property edge | 32 (46%) | 52 (29%) | 2 |

The six `WIDE` words neither graph has are `boundary_condition`,
`hidden_variable`, `hums`, `memory_lookup`, `mul`, `symbolic_io` — this repo's
own jargon, which is the correct answer.

`bird` in the semantic graph carries 626 incoming `is-a`, 125 outgoing
`has-property` and 111 `used-for`; `apple` in CSKG carries 36 `CapableOf`, 23
`UsedFor`, 17 `IsA` and 153 `MayHaveProperty`. The vocabulary is not the
problem and never was.

## Where the 5.2% actually comes from

Three deflations, none of which a bigger graph touches:

1. **Most of the curriculum's symbols are not drawn from a bindable word list.**
   They are structural (`o0`, `q`, field names), numeric, or nonce **by design** —
   `ontology.TYPE_NAMES`, `B_CONCEPT_NAMES`, `social.WORDS` exist because
   `lexical_novelty` is a declared difficulty axis and those lessons are about
   learning a word you have never seen. Binding them would delete what they
   teach.
2. **`ident` is 42% of nodes** and only the content-word ones are addressable.
3. **`name` cannot be bound on any of these graphs for a reason that is not
   about coverage.** The language packs key on the six specific names —
   `pronoun_coreference` reads `gender()[n]` for every `n in NAMES` — so a name
   here is not a free variable but a key into a hand-written lexicon. CSKG has
   `alice` and `frank` as concepts; the failure is downstream of the graph.

Raising the reach number is therefore a **curriculum** change — more rows in
`SLOT_SOURCES` and a language-pack change for names — not a graph change. That
is worth saying plainly because the natural reading of "the small graph reached
5%" is "get a bigger graph", and that reading is wrong.

## What a bigger graph buys, measured — and it is less than it looks

Not reach. The thing that could improve is **constraint density**: how much the
graph has to say about a kind once a slot is bound to it, which is the part of
the seam that was thinnest.

`symbolic_ai_kg/data/cskg-commonsense.json.gz` is now vendored beside the
WordNet projection: 30,315 nodes, 626 KB gzipped, built by
`scripts/build_cskg_kg.py` from a parquet whose sha256 is pinned, with the
selection rule stated in the module and the CC BY-SA 4.0 notice and statement of
changes in `symbolic_ai_kg/data/LICENSE.cskg`. It registers in
`symbolic_ai_kg.registry` as `cskg` and `cskg-shuffled`. **No curriculum arm is
registered for it** — see
[[2026-08-15-the-commonsense-arms-are-built-and-not-run]]. The WordNet arms are
untouched and their three golden fingerprints did not move, because `property`
and `can` are relations WordNet's projection does not have and every query over
them returns empty there.

| | WordNet projection | CSKG projection |
|---|---:|---:|
| nodes | 13,810 | 30,315 |
| `isa` | 10,442 | 32,647 |
| `part` | 1,408 | 7,294 |
| `substance` | 156 | 363 |
| `property` (thing → adjective) | **0** | **30,513** |
| `can` (thing → verb) | 0 | 8,752 |
| `attr` (adjective → dimension noun) | 623 | **0** |
| families the binder can anchor | 157 | 1,397 |
| person / place / artifact pools | 102 / 20 / 157 | 264 / 193 / 254 |

Read the `property` row and then the next table, because the second is the
answer and the first is only the promise.

| over 179 lessons × 4 seeds | WordNet | CSKG |
|---|---:|---:|
| scene objects whose attribute was re-bound from their own kind | 170/320 (**53%**) | 56/320 (**17%**) |
| `color` slot fell back | 0/137 | 1/137 |
| `material` slot fell back | 8/8 (100%) | 7/8 (88%) |
| `substance` slot fell back | 7/8 (88%) | 8/8 (100%) |
| `property` and `size` slots fell back | 0/45 (0%) | 45/45 (**100%**) |
| `name` slot fell back | 95/95 | 95/95 |

**30,513 property assertions do not become 30,513 constrained draws.** They are
concentrated: only **2,490 of 30,315** nodes carry a direct property edge at
all, at a median out-degree of 3. So the relation is rich in aggregate and
sparse exactly where a scene object needs it, and the per-object constraint
fires on 17% of objects against WordNet's 53%.

**Lost as well: dimensions.** A dimension is a noun naming an attribute —
`weight`, with `heavy` and `light` as its values — which is what makes two
adjectives mutually exclusive. WordNet's `=` pointer states it; ConceptNet says
`lemon HasProperty sour` and never says which dimension `sour` is a value of. So
the `property` and `size` slots fall back on every episode. This is recorded in
`tests/test_kg.py` as an assertion that a pool is empty **only** where the graph
lacks the relation that fills it, rather than as a relaxed check.

### The 17% is the honest number, and the first version of it was 89%

Worth recording because the wrong number was flattering and looked fine.
`properties_of` initially inherited down the taxonomy, copying `parts_of`. On
WordNet that is required — `penguin` has no part edges and `bird` has `beak` and
`wing`. On CSKG it destroys the constraint: every chain reaches a general
ancestor carrying most of the adjective vocabulary, so `penguin`, `dog`,
`brick`, `car`, `chair` and `apple` each licensed ~1,130 of 1,365 adjectives.
Six kinds, one candidate set. The binder reported **89% of objects "bound"**,
which was true and meaningless — every object was "constrained" to the same
list.

Whether a relation is inherited is now declared by the graph
(`KnowledgeGraph.inherit`) rather than assumed by the query, and both directions
are asserted in `tests/test_kg.py`.

## What would have refuted this note

* **Coverage materially higher on a bigger graph.** It is not: `STRICT` is 100%
  present on both new graphs and was already reachable on WordNet. If the reach
  number had risen with graph size, "get a bigger graph" would have been the
  right prescription and it is not.
* **The new graph filling the slot WordNet could not.** It was supposed to:
  30,513 property assertions against zero. It does not — 17% of objects against
  WordNet's 53% — and that refutes the reason the graph was vendored for. It is
  reported as a refutation rather than dropped, because "we got a bigger graph"
  is the kind of claim that survives on its headline number if nobody prints the
  binding rate underneath it.
* **The vendored artefact moving a published WordNet number.** It cannot: the
  two new relations are empty on that graph, the `inherit` field defaults to
  that artefact's own behaviour, and the three WordNet golden fingerprints are
  byte-unchanged with the `property` query wired into the binder.

## What this note does not say

It does not say the CSKG arms score worse — they were not run, and
[[2026-08-15-the-commonsense-arms-are-built-and-not-run]] gives the reason:
their families are incoherent enough that the treatment would not have been a
semantic treatment, and a null from a broken treatment enters the record as
evidence about semantics.
