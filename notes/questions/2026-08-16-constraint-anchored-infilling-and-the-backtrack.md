---
date: 2026-08-16
author: lead
status: idea
related: [2026-08-14-the-lean-gate-closes-the-kernel-loses-to-an-arity-check,
          2026-08-14-generation-is-parse-tree-infilling,
          2026-08-13-the-harness-moves-more-than-the-models]
---

# CART: emit checkable assertions while infilling, propagate, backtrack

[arXiv:2607.16727](https://arxiv.org/abs/2607.16727), Cheng, Dai and Sun,
2026-07-18. Natural-language reasoning runs normally but periodically emits
machine-checkable assertions (`count(red objects) = 3`); a Boolean constraint
propagator checks them, and a contradiction backtracks to the last consistent
checkpoint. They report the cascade rate — once one step is wrong, all the rest
are — falling from **0.65 to 0.14** at under 18% inference overhead.

The repo already has the two halves and has never joined them. Infilling fills
one node at a time and each fill is independent; `symbolic_ai_lean` has an
**arity check that beat a Lean kernel**, which is exactly a cheap
machine-checkable assertion over a partially-completed term. Nothing propagates
a fill's consequences to the remaining holes, and nothing ever un-fills.

What to build: a decode-order wrapper that fills the most-constrained hole
first, propagates type/arity/coreference consequences to the rest, and
backtracks when the partial graph becomes unsatisfiable. Reasoner held fixed, so
the arms differ in the decoder alone.

**Why it is parked rather than started, and this is the interesting part.** This
is a *harness* change, and
[[2026-08-13-the-harness-moves-more-than-the-models]] says harness changes here
span 0.15 to 2.0 where models span 0.1. So it will almost certainly produce the
largest number in the repo, and that number will be nearly uninterpretable
unless the arms are designed first. Two conditions it needs before it is worth
running:

* a **propagation-free control** with the same fill order — otherwise ordering
  and propagation are confounded, and ordering alone is known to matter;
* a **no-op constraint** control — the same backtracking machinery with an
  assertion that is always satisfiable. If that moves the score, the gain is the
  decode order and not the logic, which is precisely the shape of
  [[2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control]]
  read from the other side.

The cascade-rate metric is worth stealing on its own: this repo has never
measured whether one wrong fill makes the next one wrong, and it is a property
of the *task* that can be measured today with no new model.
