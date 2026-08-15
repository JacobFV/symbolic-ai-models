---
date: 2026-08-15
author: agent-kg-semantics
status: idea
related: [2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control,
          2026-08-15-the-kg-arms-are-a-null-and-the-quarter-that-mattered-did-not-move,
          2026-08-14-semantic-constraint-from-a-knowledge-graph,
          2026-08-14-the-label-score-is-a-copy-score]
---

# The binder constrains the vocabulary and never puts the constraint on the page

The decision note's fourth promise was "inference gets something to infer — a
dependency DAG means some answers are *derivable* rather than *copyable*". As
built, the seam does not deliver that, and the null is easier to read once you
see why.

The binder uses the graph to **choose which symbols appear**. The graph's
assertions themselves never enter the episode: nothing in the rendered prompt or
the term says `penguin isa bird` or `bird has wing`. So an answer is derivable
only by a model that already holds the graph — which no model here does, and
which the leak guard (`tests/test_kg.py::test_no_model_can_read_the_knowledge_graph`)
deliberately forbids.

The alternative manipulation, which is a different experiment and not a bigger
graph:

* **put a walk of the DAG into the episode as premises**, and mask a node whose
  label follows from them and appears nowhere else. The answer is then neither
  copyable (no visible node carries it) nor memorisable (the premises change per
  episode).
* the control is no longer a scrambled graph — it is the **same premises with
  one link cut**, so the answer stops following while every surface statistic
  stays put. That control *can* lose, which is the property
  [[2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control]]
  says the current one lacks.
* the copy ceiling is recomputed by construction and the non-copyable share
  rises, which is the first mechanism on the table for moving `label_acc` past
  0.72 rather than approaching it.

Costs, honestly: this changes tree shapes, so the arms are no longer
symbol-only and the whole comparability argument of the current design has to be
rebuilt (probably as a new lesson family rather than a rebinding of the existing
179). That is a bigger change than the seam was, and it is the one the seam's
result points at.
