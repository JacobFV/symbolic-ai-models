---
date: 2026-08-14
author: agent-generation
status: idea
related: [2026-08-14-the-infilling-ladder-preregistration]
---

Until the infilling ladder, every rule-based model fitted its context statistics
on views masked at a **hard-coded 0.15**, whatever the run's `mask_rate` said —
`RuleBasedModel.training_views` took `mask_rate: float = 0.15` and no caller in
the repo ever passed it. The docstring said "the mask rate is the one it will
actually face", which was true only because no run had ever asked for another.

The ladder makes fitting follow the task (`fit_mask_rate`, `fit_mask_mode`,
recorded in `summary.json` under `masking`), so the curve measures infilling *at*
each rate rather than transfer from 0.15 to it.

**The other experiment is the interesting one and was deliberately not run:**
fit at 0.15, score at 0.35 / 0.60 / 0.90, against the matched-regime curve. The
gap between the two curves is what the models lose by having learned their
statistics under a mostly-visible graph — a train/test mismatch measured rather
than assumed. One extra sweep, no new code: the pair
`(fit_mask_rate, mask_rate)` is already a knob.
