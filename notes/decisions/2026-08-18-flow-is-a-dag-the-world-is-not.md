---
title: Flow is a DAG, the world is not — and nothing exported may be called `Graph`
date: 2026-08-18
status: decided
tags: [architecture, ir, naming, streaming, federation]
---

## The fork

The repo is a model zoo over one 179-lesson language benchmark. The user's
architecture brief asks it to become a **typed world-program runtime**: arbitrary
inputs → typed world IR → cost-aware multi-kernel computation → arbitrary useful
outputs, with language, logic, physics, geography and economics as *overlapping
views over one world* rather than as separate apps or as one homogeneous graph.

This note records the invariants that decision commits to, before the code. It
is a decision note and not a finding: nothing here is measured, and the thing it
is trying to prevent is a naming and topology mistake that would be very
expensive to undo once fifty models are defined over it.

## The one non-negotiable distinction

**The executable graph is a DAG. The represented world is not.**

A road network is cyclic. A social network is cyclic. An economy is cyclic.
Recursive rules are cyclic. A scene can carry mutual constraints. A knowledge
source can state arbitrary n-ary and nested propositions.

So:

- `flow_graph` — operations and typed artifact bindings. **Acyclic**, at the
  outer execution level, enforced at compile time. Loops, fixed points, search,
  retries, agents and recurrence live *inside* explicit `container` / `fold` /
  `fixed_point` / `event_loop` nodes, so the outer graph stays compilable and
  cacheable.
- `world_ir` — entities, facets, events, claims, relations, constraints.
  **Arbitrary topology**, including cycles, hyperedges, scopes and time.

A test asserts each half directly: `test_flow_graph_rejects_cycles` and
`test_world_ir_accepts_cycles`.

## Stop saying "graph" without a qualifier

This repo already uses `Graph` for a flattened term tree. The commandagi project
this will share a wire schema with uses "graph" for executable operation graphs,
stage graphs, editor documents and several domain representations. That collision
becomes lethal the moment the two touch.

The naming law:

| name | exact meaning | topology |
|---|---|---|
| `flow_graph` | executable operations and typed bindings | outer DAG |
| `stage_graph` | runtime scheduling of kernels, resolution, coupling | outer DAG |
| `world_ir` | represented state, knowledge and uncertainty | arbitrary |
| `term_graph` | syntax, expressions, logical terms, shared subterms | tree or DAG |
| `scene_view` / `geo_view` | projections of world state | arbitrary |
| `knowledge_federation` | external sources, assertions, alignments | arbitrary |
| `relation_network` | roads, social links, causality, dependencies | arbitrary |
| `constraint_system` | solver-local factors, equations, constraints | arbitrary |
| `proof_trace` | derivation and justification structure | DAG |
| `lineage_trace` | how artifacts and claims were produced | usually DAG |
| `dataset_recipe` | source/generator/transform/task composition | DAG |
| `neural_compute_graph` | transient autograd internals | implementation detail |
| `canvas_view` | editable visual projection of a flow graph | UI only |

And: **no exported public type named merely `Graph`.**

`symbolic_ai_core.data.graph.Graph` is specifically a flattened *term tree* with
labels, types, parents, slots and depths. It becomes `TermGraph` in
`symbolic_ai_core/data/term_graph.py`. `Graph` survives as a deprecated alias so
that fifty registered models and every published number keep loading —
`test_no_public_unqualified_graph_type` allows exactly that one alias, in exactly
that one module, and fails on any other.

`KnowledgeGraph` in `symbolic_ai_kg` is *qualified* and stays. It is a
`relation_network` in the table above; renaming it is a later, cheaper move.

## What else this decision fixes in advance

**Artifacts are immutable and content-addressed.** Every edge in the flow DAG
carries an artifact or a stream handle. Small values inline; meshes, rasters,
tensors, corpora and solver-native states stay as blob references. The flow graph
never contains every triangle.

**Kernels propose, they do not mutate.** A kernel returns claims, a world delta,
artifacts, a trace and a *cost*. It never receives a mutable global world and
races other kernels to overwrite it. Fusion is explicit and property-specific:
forces sum, probabilities fuse, poses need covariance, proof validity is a veto.
`test_kernel_cannot_mutate_input` is the guard.

**Two times, everywhere.** `valid_time` is when a claim applies in the
represented world; `transaction_time` is when the system learned it. Economic and
political data are revised after publication — this is why ALFRED exists beside
FRED — and one-time-only is how a backtest silently reads the future.

**Sources federate; identity is a claim, not a merge.** `wn:dog.n.01`,
`wd:Q144` and `cn:/c/en/dog` are not collapsed into one `dog`. An `alignment`
claim relates them with a relation (`exact_match`, `close_match`, `possibly_same`,
`contradicts`, …), a confidence and a method, and is itself improvable evidence.
Contradictory claims stay present; a reconciled `belief_view` is *derived* for a
task, context, authority policy and time.

**The current CSKG loader is a projection and will be named as one.** It collapses
concepts by lemma, reads selected relations and maps them into a small local
relation set. That is a useful view; calling it "CSKG" is the same class of error
as calling a slice a result. It becomes `cskg_selectional_v1`.

## What was rejected

- **One universal triple store as the internal representation.** A triple-only
  encoding cannot say *casey believes that lara performed exam_17* without
  inventing reification nodes that no consumer agrees on. Claims are n-ary with
  nested content.
- **One 50,000-type ontology built before the first integrated task.** Instead a
  small `core` plus independently versioned, semi-overlapping **profiles**
  (`language`, `logic`, `scene`, `geo`, `economy`, …). One entity carries several
  facets; kernels require *capabilities*, not the whole schema.
- **A full mechanical rename of `Graph` at all 53 call sites in one commit.**
  The alias costs one line and this repo has twice destroyed a model with a
  prefix-matching sweep. New code uses `TermGraph`; the alias is allowed to
  outlive this branch.
- **Dataset-as-`Sequence`.** The generator is already lazy and an episode is
  already a pure function of its address; the trainer then calls `list()` on it
  and the sampler builds an index array over the whole corpus. A dataset becomes
  an **address space plus a replayable generator**, which is what makes a
  practically unbounded training stream cost the same memory as a small one.

## What would show this was the wrong call

The honest failure mode is that the universal layer stops being small. If, six
months in, `core` has grown to hundreds of types because every kernel needed one
more thing in the middle, then the factoring was wrong and the complexity should
have stayed inside the kernels and the source adapters. The countable version:
`symbolic_ai_core` grows faster than `symbolic_ai_kernels` and
`symbolic_ai_sources` combined.
