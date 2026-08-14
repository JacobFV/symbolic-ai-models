---
date: 2026-08-13
author: agent-ae944e68
status: open
related: [a-parser-is-a-parameter-and-the-oracle-is-prefix-restricted]
---

Every held-out slice in the rule-based half is `episodes[cut:]` with
`cut = 0.8 * len(episodes)` — `_fit_context_prior`, `_fit_temperature` and now
`gparse`'s confidence calibration all take the same contiguous tail.

The episode list is **lesson-major**. So the "held-out" 20% is not a fresh sample
of the same distribution, it is *the last ~36 lessons, entirely*, and the
first 143 lessons are absent from it. Every calibrated confidence in the
rule-based family is therefore fitted under cross-lesson transfer while
evaluation is same-lesson, different-seed.

That is not a leak — it is the pessimistic direction — but it is a mismatch, and
"my confidences are calibrated" currently means "calibrated for lessons I have
never seen". Noticed while reading `gparse-oracle`'s calibration table, where the
statistic it reports for `answer in parse` came out at 0.902 on its held-out
slice against 0.845 measured on the eval set — the slice is a different 36
lessons, not a noisy estimate of the same thing.

What would answer it: interleave the split (`episodes[::5]`) instead of slicing
the tail, and see whether any published lift moves. It touches every rule-based
row, so it is a shared-component change and by this repo's own rule the first
hypothesis for anything that then moves a lot is the harness, not the models.
