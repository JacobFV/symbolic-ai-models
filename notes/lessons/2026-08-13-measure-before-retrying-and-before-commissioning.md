---
date: 2026-08-13
author: lead
status: measured
---

# Two failures of mine that cost the most: retrying, and commissioning without checking

## Retrying a failing shape instead of measuring it

Four attempts to fit one model across 46 languages died at **exit 137** before
printing a line. I retried the same shape three times, adjusting size.

Measuring took one step and settled it: episodes are ~1 GB, the fit scales at
**~0.4 GB per language**, ~4 minutes projected for all 46. Memory was never the
story — 137 was the process group being killed with the terminal.

The fix was **granularity, not scale**: one language per step, 6 s each, written
to its own JSON immediately (`scripts/wals_perlang.py`). All 46 completed. An
interruption now costs one language.

**Rule:** when the same action fails twice, the third attempt should be a
*measurement*, not a retry. And on an unreliable box, structure work so that each
step is minutes and its result is durable — resumability beats reliability.

## Commissioning an experiment the README had already answered

I designed and dispatched a cross-language experiment on the **node** task.
`README.md` line 724, which I had read that morning:

> the graph is byte-identical across all of them — which makes a cross-language
> **node** experiment vacuous rather than probing

`Lesson.structured(seed)` takes no language; the claws read only the graph.
Conditioning on language partitioned the evidence into seven estimates of **one
distribution**. The experiment was **guaranteed null by arithmetic about the
corpus**, and I spent an agent on it.

It was salvaged only because the agent checked the premise before fitting and
added surface claws so language had somewhere to live.

**Rule:** before commissioning work, check whether the *task* can express the
variable being manipulated. Ask "what in this data could possibly differ along
this axis?" and answer it with a measurement, not an intuition.

## A smaller one, same family

Probing `languages.db` with `sqlite3.connect()` **created** an empty database —
a read-only-looking call that mutated the repo and broke two tests until the
zero-byte file was removed. Inspection is not always inspection.
