---
date: 2026-08-13
author: lead
status: open
related: [2026-08-13-cluster-to-the-measured-effective-rank]
---
Three independent seeding experiments are nulls: synthEX's WordNet supersenses
(~0 against a random partition, negative past 15M chars), `synthex_class-002`
(ground-truth node types LOSE to sha256 at matched cardinality), and
`template-lex` (the full dictionary: +0.011 at 2 episodes/lesson, 0.000 at 16).

The mechanism in the second is **balance**, not semantics: the curated layer puts
68% of symbols in one class so the context cannot discriminate, while the hash
partition is uniform.

**The experiment nobody has run:** hold provenance fixed and vary *balance*.
Rebalance the curated classes (split the giant one, merge the tiny ones) to match
the entropy of the random partition. If rebalanced-curated beats random, the
semantics were real and were masked by skew. If it only matches random,
provenance contributes nothing and the leapfrog's high-level seed should be any
balanced partition, which is free.

Refutes the "seeding is worthless" reading if rebalanced-curated > random.
