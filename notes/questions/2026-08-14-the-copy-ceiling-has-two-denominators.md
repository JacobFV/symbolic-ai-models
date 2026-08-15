---
date: 2026-08-14
author: agent-kg-seam
status: open
related: [2026-08-13-audit-the-floor-before-quoting-a-lift,
          2026-08-14-preregistering-the-curriculum-arms]
---

# `copy_ceiling` is over `label_n` and the copy head is scored over `copy_scored_n`

`symbolic_ai_models/tasks/masked_node.py`:

```python
out["copy_ceiling"] = reachable / scored     # scored == label_n
...
out["copy_scored_n"] = totals["copy_n"]      # what copy_acc is over
```

So the published **0.7216** is the share of *scored label* positions whose
answer sits on a visible node, and it is quoted against a `copy_acc` computed
over a different set. On its own denominator the ceiling is **0.7305**.

0.009 changes no ranking, and every "share of reachable signal" claim in
`RESEARCH_LOG.md` is written against the `label_n` version, so **the existing
key must keep its meaning to the digit** — renaming it would silently redefine
those claims, which is the thing `symbolic_ai_core/registry.py` exists to stop.

The fix is additive: emit `copy_ceiling_scored` beside it, one line, and let a
reader see both denominators without going to a scratch script.

**Written and then deliberately not done, today.** The patch was made, the tests
passed, and it was reverted before commit because the four-arm curriculum sweep
was mid-flight. An additive summary key cannot change a score — but it would
have been present on the arms trained after it landed and absent on the ones
before, and an asymmetry across arms of one experiment is exactly the silent
property this repo keeps getting caught by. It is a two-minute change once
`runs/kg179-*` are finished, and it should be made then, on its own commit, with
`copy_ceiling` asserted unchanged.
