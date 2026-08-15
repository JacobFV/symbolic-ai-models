---
date: 2026-08-15
author: agent-r090
status: idea
related: [2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model,
          2026-08-14-the-label-score-is-a-copy-score]
---

Binary copyability predicts `label_acc` to 0.005 at two rates and misses by 0.030
at 0.90; evidence concentration `v/V` overshoots by 0.031. Neither is the right
supply variable, and the truth is between them.

The question: **is there a single statistic of the masking draw — computable
without any model — that predicts `label_acc` across all four rates to within
noise?** Candidates, cheapest first: the expected `v/V` over scored fills; the
distribution of `v` rather than its indicator; `E[1/V]`, which is what a uniform
pointer over visible labelled nodes would score. If one of them works, the
mask-rate curve stops needing a per-rate refit to be understood, and the residual
after subtracting it is the first *ability* number this axis has produced.

Worth doing because the two existing supply models bracket the observation from
both sides, which is the situation in which a third one is most likely to land.
