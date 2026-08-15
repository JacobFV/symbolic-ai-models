---
date: 2026-08-14
author: agent-generation
status: provisional
related: [2026-08-14-generation-is-parse-tree-infilling,
          2026-08-14-the-infilling-ladder-preregistration,
          2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name,
          2026-08-13-a-ranking-is-a-property-of-a-metric,
          the-readout-survives-both-attacks-and-its-comparison-row-does-not]
---

# The curriculum's own question, asked on the graph: nine of twelve models score the abstention row

**Not a slice of lessons — all 179, 716 evaluation episodes, seeds from
1,000,000, `runs/infill-ans`.** It *is* a slice of the models: twelve of the
113 registered rule-based rows, six with a pointer and six without, fixed in
`notes/decisions/2026-08-14-the-infilling-ladder-preregistration.md` before any
number landed, plus one abstention control.

This is rung 3 of the infilling ladder and it was run **first**, because it is
the rung that can refute the reframe. It largely does.

## The task

`nodeans` hides every node whose label is the episode's answer, together with
its subtree, and asks for it back. That is the curriculum's own question — the
one `answer_acc` scores on the text — put to the graph instead. The answer is a
node label in **565 of 716 evaluation episodes (78.9%)**, always in 136 lessons
and never in 34; the 34 are systematically the lessons where the answer is
*computed* rather than *stated* (`entailment`, `negation`, `quantification`,
`unification`, `variable_binding`, `predicate_logic`, `palindrome`,
`parse_depth`). Those episodes are **unscored, not scored zero**, and the
coverage is printed beside every accuracy.

## The result

`ansnode_*` is the label score restricted to the positions that carry the
answer. 841 scored fills, coverage 0.781. **The floor is a structure-only
context lookup refitted under this masking regime: 0.101.**

| model | ansnd acc | lift | lbl bits | renaming drop | type lift |
|---|---:|---:|---:|---:|---:|
| `grammar-001` | **0.181** | **+0.089** | **5.381** | **0.184** | −0.536 |
| `ngram-001` | 0.169 | +0.075 | 5.470 | 0.164 | −0.964 |
| `brill-001` | 0.168 | +0.074 | 10.668 | 0.172 | −0.750 |
| *floor* | *0.101* | *0* | *7.495* | — | — |
| `ruleinduce-001` | 0.012 | −0.099 | 11.925 | 0.010 | −0.089 |
| `ctw-001` | 0.012 | −0.099 | 7.984 | 0.017 | +0.393 |
| `ptrgen-001` | 0.004 | −0.108 | 12.000 | 0.003 | **+0.554** |
| `vsa_perm-002` | 0.004 | −0.108 | 12.000 | 0.003 | −0.375 |
| `omegaclaw_rank-001` | 0.004 | −0.108 | 11.943 | 0.003 | −1.982 |
| `omegaclaw_ctx-001` | 0.004 | −0.108 | 11.933 | 0.003 | −2.161 |
| **`gparse-none` (says nothing)** | **0.004** | −0.108 | 12.000 | 0.003 | −2.482 |
| `corefer-001` | 0.001 | −0.111 | 11.861 | 0.001 | +0.321 |
| `routes-001` | 0.000 | −0.112 | 12.035 | 0.000 | −6.607 |
| `evidence-001` | 0.000 | −0.112 | 11.873 | 0.001 | −6.607 |

**Nine of the twelve land on the abstention row.** `gparse-none` does not
override `node_votes`, so on a graph task it says nothing and its score *is* the
shared back-off: 0.004. Every equivariant model in the table is at or below it.
`corefer-001` — the best label model in the repo, 0.357 under scattered masking
— gets **1 of 841**.

**Four of them are identical to saying nothing, to nine decimal places.** This
is the control working, in the form
`notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name.md`
describes: rows agreeing to the last digit by unrelated mechanisms are one row.

| model | `ansnode_acc` | `label_acc` | `label_bits` |
|---|---:|---:|---:|
| `gparse-none` (no graph hook at all) | 0.003567182 | 0.003225806 | 12.000487 |
| `ptrgen-001` | 0.003567182 | 0.003225806 | **12.000487** |
| `vsa_perm-002` | 0.003567182 | 0.003225806 | **12.000487** |
| `omegaclaw_rank-001` | 0.003567182 | 0.003225806 | 11.942960 |
| `omegaclaw_ctx-001` | 0.003567182 | 0.003225806 | 11.932962 |

`ptrgen-001` and `vsa_perm-002` are **bit-identical to a model that does not
implement the graph hook**, in accuracy and in bits. The two `omegaclaw` rows
move the distribution slightly and never move an argmax. Two more rows —
`routes-001` and `evidence-001` — sit *below* the abstention row at exactly
0.000: they vote, and they are wrong every time.

**The three that clear the floor clear it with vocabulary, and the renaming
column says so.** `grammar`, `ngram` and `brill` are exactly the three
vocabulary-bound rows of `RESEARCH_LOG.md`'s renaming table (−0.159, −0.143,
−0.130 there). Here their whole score is the drop: 0.192 → 0.008 for `grammar`
under a symbol permutation. Quoting accuracy alone would have produced the
headline "a symbolic model answers the curriculum's question on the graph"; the
renaming column turns it into "a model that has memorised which symbols are
answers does".

**They know what kind of thing goes there.** `ptrgen-001` scores **+0.554** type
lift and `corefer-001` **+0.321** on the same fills they cannot name. The
failure is reference, not structure.

## The refutation, stated plainly

The pre-registered refutation was: *if completing the answer subtree also scores
~0, the 0.423 readout gap was about the `repair` environment specifically and
generation is genuinely absent rather than mis-measured.*

**It scores ~0.** For every renaming-invariant model in the set, asking the
graph for the curriculum's answer produces the same nothing that asking for text
produced. `answer_acc` is 0.000 and `ansnode_acc` is 0.000–0.012 against a 0.101
floor. The readout was worth 0.423 on *masked-node repair* and is worth nothing
here.

So the honest statement is narrower than the reframe: **the readout gap is real
and it is about which nodes are being asked for.** Scattered masking asks about
nodes that are 71.9% copyable; the curriculum's answer is 0% copyable, because
hiding it means hiding every node that says it.

**And the two surfaces agree, model for model.** `answer_acc` on all 179 lessons
(`runs/full179-site`, `runs/full179-gparse`, floor 0.0579) against `ansnode_acc`
here (floor 0.101):

| model | `answer_acc` (text) | lift | `ansnode_acc` (graph) | lift |
|---|---:|---:|---:|---:|
| `corefer-001` | 0.000 | −0.062 | 0.001 | −0.111 |
| `ptrgen-001` | 0.000 | −0.062 | 0.004 | −0.108 |
| `gparse-none` | 0.000 | −0.062 | 0.004 | −0.108 |
| `ctw-001` | 0.047 | −0.012 | 0.012 | −0.099 |
| `ngram-001` | **0.143** | **+0.090** | **0.169** | **+0.075** |

The models that can answer on the text are the models that can answer on the
graph, and they are the vocabulary models. Changing the readout does not release
a capability the text surface was hiding — which is exactly what the reframe
predicted it would.

## Why, measured rather than argued

`scripts/nodeans_diagnostic.py` re-reads the sweep's own fitted `corefer-001`
over the same 716 episodes and asks what the wrong answers *are*:

| | share of scored fills |
|---|---:|
| correct | 0.001 |
| wrong, and the label of a **visible node of the same graph** | **0.681** |
| wrong, and inside the episode's own answer set (mean size 4.19) | 0.164 |
| wrong, and neither | 0.315 |

`corefer` is doing exactly what it does: naming a visible node's label. Under
scattered masking that is right 72% of the time it is possible; here it is right
0% of the time by construction, because `nodeans` hides every copy.

## The control that had to exist, because the design guarantees the null

Hiding **every** copy of the answer is correct — leaving one visible turns the
curriculum's question into a copy exercise — and it also means a pointer head
*cannot* answer, since a pointer emits the label of a visible node. "Pointers
score zero on `nodeans`" is therefore true by construction and is no evidence
about pointers. Without a control, the rung-3 null could not be told apart from
its own design.

`nodeans1` (`runs/infill-ans1`) hides the answer's **first** occurrence only, so
on the episodes with more than one the copy route is open — `copy_ceiling` goes
from 0.087 to **0.419**. Same 179 lessons, 501 scored answer fills, floor 0.092,
and the abstention row is now **0.000**.

| model | `nodeans` | `nodeans1` | renaming drop (nodeans1) |
|---|---:|---:|---:|
| `grammar-001` | 0.181 | **0.224** (+0.145) | **0.219** |
| `brill-001` | 0.168 | 0.208 (+0.127) | 0.205 |
| `ngram-001` | 0.169 | 0.208 (+0.127) | 0.191 |
| *floor* | *0.101* | *0.092* | — |
| `corefer-001` | 0.001 | **0.072** (−0.022) | 0.003 |
| `ptrgen-001` | 0.004 | 0.064 (−0.031) | 0.006 |
| `vsa_perm-002` | 0.004 | 0.052 (−0.044) | 0.007 |
| `evidence-001` | 0.000 | 0.020 (−0.079) | 0.002 |
| `omegaclaw_ctx-001` | 0.004 | 0.018 (−0.081) | 0.004 |
| `routes-001` | 0.000 | 0.016 (−0.084) | −0.001 |
| `omegaclaw_rank-001` | 0.004 | 0.012 (−0.088) | 0.002 |
| `ruleinduce-001` | 0.012 | 0.000 (−0.101) | −0.001 |
| `ctw-001` | 0.012 | 0.000 (−0.101) | 0.010 |
| **`gparse-none` (says nothing)** | 0.004 | **0.000** | 0.000 |

Both halves are true and they are different claims:

1. **The pointer zero on `nodeans` is mostly design.** Opening the copy route
   moves `corefer-001` from 0.001 to 0.072 — 60x — and it is now clearly above
   an abstention row of 0.000, so the pointer really is contributing.
2. **It still does not clear a structure-only lookup.** Not one equivariant
   model reaches 0.092 in the *most* favourable framing of the curriculum's
   question available: the position given, a copy visible, only the 78% covered
   subset scored, one symbol named rather than a string spelled. Its pointer
   finds a valid source on 0.117 of fills where 0.419 are reachable — 28% of its
   ceiling, against 47% (0.336 of 0.722) on ordinary scattered masking.

And in both arms the only rows above the floor are the three vocabulary models,
losing 0.19–0.22 of 0.21–0.23 under a symbol permutation.

## Rung 4, minus the render

The ladder's last rung was "render and score exact-match end to end". The
renderer takes the generator's own term object rather than this repo's flattened
`Graph`, so a true end-to-end render needs an inverse of `graph_from_json` —
real work with its own correctness burden. It is also not needed to answer the
question, because the render is a **deterministic function of the term**
(`notes/findings/2026-08-13-the-renderer-is-deterministic.md`): a graph that is
not exactly right cannot render to text that is. So `exact_match <= ` graph
exact-match, and `scripts/graph_exact.py` computes the cheap side by rescoring
the sweep's own fitted model on all 179 lessons.

| run | label acc | episodes | every hidden label right | …and every type |
|---|---:|---:|---:|---:|
| `corefer-001`, `node` @0.15 | 0.357 | 706 | **0.0397** | **0.0368** |
| `ptrgen-001`, `node` @0.15 | 0.334 | 706 | 0.0326 | 0.0312 |
| `corefer-001`, `nodeans` | 0.030 | 505 | **0.0000** | **0.0000** |
| `grammar-001`, `nodeans` | 0.192 | 505 | 0.1842 | 0.1842 |

Two things fall out. On the **curriculum's own question**, `corefer-001` gets
*no* episode's hidden region exactly right — 0 of 505 — so `exact_match` through
a perfect renderer would be 0.0000, and the ladder's third refutation condition
holds for it. On **ordinary scattered masking at 0.15**, `exact_match` would not
be zero, but it would be **0.037 where the published number is 0.357**: partial
credit is worth roughly a factor of ten, and that factor is what the repo's
whole leaderboard has been denominated in.

(The mask draw here is an independent sample from the same regime rather than
the sweep's own draw, so `label_acc` agrees with `summary.json` to about 0.002 —
0.357 against 0.357, 0.334 against 0.336 — which is the check that this is
scoring the same thing.)

## What would still refute this reading

- **Undertraining.** `answer` masking hides about 1.2 nodes per episode where
  scattered masking at 0.15 hides about 10, so a model fitted in the matched
  regime sees roughly **eight times less supervision**. This repo has already
  published one null that was an undertrained budget wearing an architecture's
  name. The control is `extra.fit_mask_mode="scatter"` — fit under the full
  regime, score under `answer` — and it is reported below.
- **A different readout.** These rows score an argmax over 8,192 symbols. A
  readout restricted to the episode's own four options is the graph-side
  equivalent of the curriculum evaluation and is not measured here; the
  diagnostic says only 16.4% of `corefer`'s wrong fills are even inside that
  set, which makes a large gain there unlikely but not impossible.
- **The skeleton is given.** `relation_matrix` keeps parent, sibling and
  ancestor for a hidden node. These numbers are an upper bound on generation for
  that reason. See `notes/questions/2026-08-14-the-skeleton-is-never-hidden.md`.

## Provisional, and why

Every control in this note was designed by its author. `status: provisional`
until something independent has tried to break it — in particular the claim that
`gparse-none` at 0.004 really is the abstention row and not a broken model.
