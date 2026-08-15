---
date: 2026-08-14
author: agent-generation
status: provisional
related: [2026-08-14-generation-is-parse-tree-infilling,
          2026-08-13-readout-is-a-knob,
          2026-08-14-record-the-curve-not-the-argmax,
          2026-08-13-slices-have-inverted-results-eight-times]
---

# Pre-registration: the mask-rate curve, the subtree, and the answer subtree

Written before any number landed. What is fixed here is the model set, the
metrics, the floors, the coverage rules, and — the part that matters — the
readings each outcome licenses. `2026-08-14-generation-is-parse-tree-infilling`
is the brief; this file is the protocol.

## What is being built, and what is not moving

Three registered tasks, beside `node`, never in place of it:

| task | what it hides |
|---|---|
| `node` (unchanged) | each node independently with probability `mask_rate` |
| `nodesub` | **whole subtrees**, drawn until the hidden fraction reaches `mask_rate` |
| `nodeans` | every node whose label **is the episode's answer**, and its subtree |

`mask_rate` is already a config knob and already flows into
`MaskedNode.floor`, so the floor is refitted at every rate by construction
rather than by anyone remembering to. The 0.15 arm is re-run as its own row and
compared digit-for-digit against `runs/full179`; if it does not reproduce, that
is reported as a harness drift and *my* 0.15 row — not the published one — is
the baseline for the curve, because the four arms have to come from one build.

## What the graph task can and cannot ask, stated before it flatters anything

**The tree skeleton is never hidden.** `relation_matrix` withholds a masked
node's `same_label` edges and keeps parent, child-slot, sibling and ancestor.
So at *any* mask rate the model is given the shape of the term and asked for the
labels and types on it. "Graph completion" in this ladder means **infilling a
known skeleton**, not generating a tree. Every number below should be read as an
upper bound on generation for that reason, and rung 4 would need the skeleton
hidden too before "generate a constituent" is literally true.

**The answer is a node label in 78.9% of evaluation episodes** (565 of 716, all
179 lessons, seeds from 1,000,000, exact string match against a non-structural
node label; mean 2.03 copies where present). It is *always* one in 136 lessons
and *never* one in 34 — and the 34 are systematically the lessons where the
answer is computed rather than stated: `entailment`, `negation`,
`quantification`, `unification`, `variable_binding`, `predicate_logic`,
`palindrome`, `parse_depth`, `scope_ambiguity`, `pronoun_coreference`. So
`nodeans` is scorable exactly where the answer is an entity the question already
mentions, and unscorable exactly where it is a conclusion. That is a bias in
favour of the graph reading and it is reported as coverage next to every
accuracy, never folded into one number.

**Three asymmetries all favour `nodeans` over `answer_acc`, and all three point
the same way.** Named now so the comparison is not later described as fair:

1. `nodeans` is told **where** the answer sits; `answer_acc` is not.
2. `nodeans` is scored on the 78.9% subset; `answer_acc` on everything.
3. `nodeans` names one symbol from a fitted vocabulary; `answer_acc` spells a
   string token by token.

So `nodeans >> 0` does **not** by itself establish that generation was
mis-measured — it establishes it only in the sense that a capability reachable
with a different readout is a capability the model has. `nodeans ~ 0` **does**
refute the reframe, because none of the three asymmetries can hurt it. The
refutation is therefore clean and the confirmation is not, which is why the
refutation is checked first.

## Model set, fixed before any run

Twelve rows, six with a pointer (`source_votes` overridden) and six without,
because the pre-registered expectation is about pointers. Chosen for coverage of
the families in `RESEARCH_LOG.md`'s renaming table, not for score.

| pointer | no pointer |
|---|---|
| `corefer-001` (best label acc, equivariant) | `grammar-001` (best bits, vocabulary-bound) |
| `ptrgen-001` (best symbolic bits) | `ngram-001` (counting) |
| `routes-001` (structural, −0.000 renaming) | `ctw-001` (819,990 counts) |
| `evidence-001` (retrieval + abstention) | `brill-001` (−0.130 renaming) |
| `vsa_perm-002` (algebraic) | `omegaclaw_rank-001` (best claw takes all) |
| `ruleinduce-001` (rules predict pointers) | `omegaclaw_ctx-001` (weighted mixture) |

All 179 lessons, `configs/full179.toml` unchanged except `--mask-rate`, eval
seeds from 1,000,000. Not a slice of lessons; it **is** a slice of the 113
registered rule-based models, and that is stated in the first sentence of the
finding.

## The pre-registered expectations, and what refutes each

**R1 — pointer models degrade fastest with `mask_rate`.** A pointer's candidates
are the visible nodes and masking removes them. Refuted if the pointer arm's
mean `label_lift` falls *less* between 0.15 and 0.60 than the no-pointer arm's;
that outcome means the models are reconstructing rather than copying and is the
most interesting result on offer.

There is a mechanical version of R1 that is *not* a fact about the models and
must be separated from it: `copy_ceiling` — the share of scored answers that
still sit on a visible node — is forced down by masking, because
`target_source` only accepts a **visible** same-label node. **`copy_ceiling` is
therefore reported at every rate as part of the curve**, and a pointer's fall is
only a fact about the pointer to the extent that it falls faster than its own
ceiling. Any claim of the form "pointers collapse" that does not quote
`copy_acc / copy_ceiling` is quoting the harness. (`the-harness-moves-more-
than-the-models`.)

**R2 — the curve falls off a cliff between 0.15 and 0.35.** The brief's second
refutation condition. Registered threshold: a cliff means the mean pointer
`label_lift` at 0.35 is below **half** its 0.15 value while the 0.35→0.60 and
0.60→0.90 steps are each smaller than the 0.15→0.35 step. A smooth monotone
decline is not a cliff and must not be written up as one. A *rise* is possible
and is not excluded here — more masked nodes is also more supervision per
episode and a lower floor — and if it happens the reading is that the floor
moved, not that the models improved, until `label_acc` and `label_floor` are
quoted separately. (`a-guard-applied-only-to-the-arm-that-lost`: the check is
run on whichever arm wins.)

**R3 — a contiguous subtree is harder than scattered nodes at the same
budget.** `nodesub` at `mask_rate=m` against `node` at `mask_rate=m`, same
models, same floors refitted per regime. Refuted if `nodesub` scores at or above
`node` at matched budget, which would mean scattered masking's visible siblings
were not what the models were using.

**R4 — `nodeans` clears its floor.** Every rule-based model scores `answer_acc`
0.000. Refuted — and the whole reframe with it — if `nodeans` `label_lift` is
not positive for any model in the set. Threshold for "positive": above 0.005,
the repo's noise band for bits, applied here to accuracy as the same order of
caution.

## What gets quoted

Accuracy, bits and renaming are not interchangeable
(`a-ranking-is-a-property-of-a-metric`). Every table carries, per rate:
`label_acc`, `label_floor`, `label_lift`, `label_bits` (three decimals),
`label_n`, `type_lift`, `copy_acc`, `copy_floor`, `copy_ceiling`, and for
`nodeans` the episode coverage. Nothing is averaged across mask rates.

## Rejected

- **Raising `mask_rate` on the `node` task itself as the published row.** It
  would redefine every number named `node`. Separate `--out` per rate; `node`
  at 0.15 stays what it was.
- **Falling back to a random node when the answer is absent from the graph.**
  That makes "there is nothing to ask here" indistinguishable from "here is a
  question", which is `no-information-is-not-negative-evidence` exactly. Those
  episodes are **unscored**, and the coverage is printed.
- **Scoring `nodeans` against `node`'s floor.** A floor fitted under one masking
  regime is not the floor under another.
