---
date: 2026-08-14
author: agent-generation
status: idea
related: [2026-08-14-generation-is-parse-tree-infilling,
          2026-08-14-the-infilling-ladder-preregistration]
---

`relation_matrix` withholds a masked node's `same_label` edges and keeps parent,
child-slot, sibling and ancestor. So at **every** mask rate, including 0.90, the
model is handed the shape of the term and asked only for the labels and types on
it. "Graph completion" in the infilling ladder therefore means infilling a given
skeleton, and a mask rate of 0.90 is not 90% of the generation problem — it is
90% of the *labelling* problem on a fully specified tree.

A fourth mask mode — hide the relations of the hidden region too, so the model
must decide arity and attachment as well — is what "generate a constituent"
literally means. It needs a different output head (the model would have to emit
a shape), which is why it is not on the ladder, but the ladder's numbers should
never be quoted without saying the skeleton was given.

Cheap intermediate: keep the skeleton but report, per rate, how much of the
score is carried by nodes whose parent is also hidden. That is already
computable from the batch and would say whether "given the shape" is doing the
work.
