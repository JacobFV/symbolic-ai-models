---
date: 2026-08-13
author: agent-action-readout
status: idea
related: [2026-08-13-action-readout, 2026-08-13-abstention-on-repair-is-below-chance]
---

An agent's `repair` column mixes *how often it had something to say* with *how
good what it said was*, and only the product is reported. `graphread`'s coverage
ranges from 47% (`ilp-001`) to 100% (`ensemble-001`, `corefer-001`, `ptrgen-001`,
`vsa-002`) on the same 116 fills, and the thing it abstains onto scores 0.0431.
So two rows an eighth of a point apart may be one agent that speaks twice as
often and is much worse when it does.

`ActionReadout.summarize` already computes exactly the split — `action_acc`
(right, given that it spoke), `action_yield` (right, out of everything asked),
`action_speak` — but nothing calls it: the counts need a gold action, which is
`Environment.oracle`, which is fitting-time only. Wiring an **offline audit** of
the readout into `train.run` (score `action_*` on the training episodes, report
it beside the evaluation row) would settle it without touching the leak
contract.

Worth doing before anyone reads a `graphread` ranking as a ranking of reasoners.
The naive arithmetic — invert `acc = r·a + (1-r)·0.0431` — is not the answer,
because the decisions an agent abstains on are not a random sample of the
decisions it faces.
