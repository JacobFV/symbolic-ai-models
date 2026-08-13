---
date: 2026-08-13
author: lead
status: open
---
`corefer-001` beats `ptrgen-001` on copy (+0.096 vs +0.078) and has a
second-stage reranker that `ptrgen` does not; stage-one features are shared
exactly. Until a reranker is added, "naive Bayes points better than marginal
likelihood" is confounded with "two stages beat one" and neither claim can be
made.
