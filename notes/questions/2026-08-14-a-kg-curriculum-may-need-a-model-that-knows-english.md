---
date: 2026-08-14
author: agent-kg-seam
status: idea
related: [2026-08-14-semantic-constraint-from-a-knowledge-graph,
          2026-08-14-preregistering-the-curriculum-arms,
          2026-08-13-a-real-pretrained-seed]
---

# The strongest argument against the KG curriculum is that these models start from zero

Written before the arms landed, as the thing most likely to explain a null.

Every model in this repo trains on this corpus alone. It has no idea that
`penguin` is a bird, that `oak` is made of wood, or that `sleep` takes an
animate subject — except insofar as the training episodes told it, and the
training episodes are the only thing that ever will.

A **degree-preserving edge permutation** preserves every within-episode
statistic such a model could learn. Same node count, same per-node degree, same
density, same acyclicity. If the only channel by which meaning could reach a
model is the episodes themselves, then the real graph and the scrambled graph
present the same learning problem and the control is guaranteed to match — which
is the decision note's cheapest death, arrived at for a reason that has nothing
to do with whether the idea is right.

What is left that the scramble does break, and it is thin:

* **lemma strings correlate with taxonomy position in the real graph.**
  `stringed_instrument` and `wind_instrument` share a suffix and a parent;
  after the scramble they share the suffix and not the parent. A model reading
  subwords or characters can use that; one treating symbols as atoms cannot.
* **the same family recurs across episodes.** Two episodes anchored on `bird`
  share a lexicon in the real graph in a way that tracks a real similarity;
  under the scramble they share a lexicon that tracks nothing.

If those are worth less than the pre-registered 0.010 of label accuracy, the
honest conclusion is **not** "semantics does not help". It is that a
semantically constrained curriculum is an instrument for measuring models that
already know something, and this repo has none. That would make
[[2026-08-13-a-real-pretrained-seed]] a prerequisite rather than a side quest,
and it would reframe the KG work as *building the measurement* rather than
*taking it*.

The experiment that would settle it, and which nothing here has run: seed one
model's symbol representations from an outside source (co-occurrence counts from
a real corpus, or an off-the-shelf embedding table restricted to the vendored
graph's lemmas), and run the same three arms. If the seeded model separates the
real graph from its scramble and the unseeded one does not, the null above is a
statement about the models. If neither separates them, it is a statement about
the curriculum.
