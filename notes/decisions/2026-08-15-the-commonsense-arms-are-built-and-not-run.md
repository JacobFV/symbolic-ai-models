---
date: 2026-08-15
author: agent-kg-semantics
status: provisional
related: [2026-08-14-semantic-constraint-from-a-knowledge-graph,
          2026-08-14-preregistering-the-curriculum-arms,
          2026-08-15-coverage-is-bounded-by-the-curriculum-not-by-the-graph,
          2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control,
          2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property]
---

# The commonsense graph is vendored and its arms are not registered, because the treatment would have been incoherent

A real 14 GB knowledge graph arrived. The obvious next move was a `kg:cskg` arm
beside `kg:wordnet`, and the seam was built for exactly that: "a larger graph
swaps in as data, not design". The graph is vendored, it loads, it registers,
`load("cskg")` works, its control scrambles, its tests pass — and **the
curriculum arms are deliberately not registered**. This note is why, written
before anyone spends two hours of sweep on them.

## What was built

`symbolic_ai_kg/data/cskg-commonsense.json.gz`, 626 KB, 30,315 nodes, built by
`scripts/build_cskg_kg.py` from a parquet with a pinned sha256, CC BY-SA 4.0
notice and statement of changes committed beside it. Registered as `cskg` and
`cskg-shuffled`. Adding it needed two rows in `symbolic_ai_kg/registry.py`, two
new relation names, and nothing above the package — which is the seam's design
claim cashed, and it is worth having even though the arm did not run.

| | WordNet | CSKG |
|---|---:|---:|
| nodes | 13,810 | 30,315 |
| `isa` | 10,442 | 32,647 |
| `part` / `substance` | 1,408 / 156 | 7,294 / 363 |
| `property` (thing → adjective) | **0** | **30,513** |
| `can` (thing → verb) | 0 | 8,752 |
| `attr` (adjective → dimension noun) | 623 | 0 |

## Why the arm is not registered

**The per-object constraint needs a coherent family, and CSKG's taxonomy does
not give one.** The binder anchors a family, draws the scene's kinds from its
descendants, and draws each object's attribute from what the graph licenses for
that object's own kind. On WordNet a family is `bird` and the kinds are birds.
On CSKG, at the same settings, the families are:

| lesson | family | the six "kinds" |
|---|---|---|
| `symbol_grounding` | `skill` | interior, crocheting, snout, crusade, conk, salesmanship |
| `set_operations` | `revolve` | pinwheel, setscrew, easel, rig, pinion, hematocrit |
| `negation` | `indicant` | argue, profiling, cosign, con, testament, confutative |
| `counting_quantifier` | `affection` | scarf, unite, yoke, coupling, pawn, assemble |

And the per-object constraint that is the point of the DAG produces **1 or 2
distinct candidate subsets across the six kinds**, against WordNet's spread.

An arm like that is not a semantic treatment. It is `kg:wordnet-flat` — six
unrelated words of roughly the right shape — wearing the treatment's name. Its
comparison against `cskg-shuffled` would come out null, and the null would be
**unreadable**: indistinguishable from "meaning does not help" while actually
saying "there was no meaning in the arm". That is
[[2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property]] with the
guard fired *before* the sweep instead of after it, which is the whole reason to
look at the episodes a new curriculum produces rather than only at its
fingerprints.

It was already made as good as one afternoon allows. Restricting `isa` to
assertions whose **both endpoints carry ConceptNet's own part-of-speech tag** —
its disambiguation, not this repo's judgement — drops 46,089 raw edges to 34,257
and improves the families from *(debacle, coma, interjection, splinter,
concertina, cripple)* to the table above. Better, still not a neighbourhood.

## The other thing this turned up, which is a real bug the seam had

`KnowledgeGraph.properties_of` originally inherited down the taxonomy, copying
`parts_of`. On WordNet inheritance is **required** — `penguin` has no part edges
and `bird` has `beak` and `wing`. On CSKG it is **fatal**: every chain reaches a
general ancestor that has been assigned most of the adjective vocabulary, so
`penguin`, `dog`, `brick`, `car`, `chair` and `apple` each licensed ~1,130 of
1,365 adjectives — six kinds, one candidate set, constraint gone.

Both settings load, generate and pass every fingerprint. So whether a relation
is inherited is now **declared by the graph** (`KnowledgeGraph.inherit`, in the
vendored payload) rather than assumed by the query, defaulting to WordNet's
behaviour so the committed WordNet artefact keeps meaning what it meant.
`tests/test_kg.py::test_whether_a_relation_is_inherited_is_a_property_of_the_source`
asserts both halves.

## What was rejected

* **Registering the arms anyway and reporting the null.** Rejected: a null from
  a broken treatment is worse than no measurement, because it enters the record
  as evidence about semantics.
* **Tuning `FAMILY_DEPTH` / `FAMILY_CAP` / `FAMILY_MIN_DISTINCT` until the
  families look better.** Rejected: that is fitting the data-generation
  parameters against a qualitative impression of the output, with no held-out
  anything, and the repo has a lesson about boundary optima and one about
  recording the curve rather than the argmax. If it is done it needs a stated
  objective, not an eyeball.
* **Waiting for a cleaner commonsense graph.** Rejected as a *reason not to
  vendor*; the artefact is committed and the next agent starts from it.

## What to do instead, and it is cheap

**Join the two graphs: WordNet's taxonomy, CSKG's properties.** WordNet gives
coherent families and 3,436 adjectives with dimensions; CSKG gives 30,513
property assertions that WordNet simply does not have. The join is on the lemma,
both are already vendored, and the result fixes the one substantive complaint
against the WordNet arm — that an object's *attribute* was bound to its kind's
*parts* — while keeping everything that made the arm readable.

That is the recommended next build, and it should be run *after*
[[2026-08-15-permute-the-lemma-strings-with-the-edges]], which attributes the
only signal the existing arms produced and costs one registry row.
