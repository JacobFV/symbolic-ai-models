---
date: 2026-08-14
author: agent-readout
status: open
related: [site-readout-on-179-lessons]
---

# `label_bits` drifted on master while every accuracy stayed bit-identical

Found while gating the readout refactor on "every published number must
reproduce". It is **not** the refactor — that was checked — and it is on master.

## What was measured

`runs/full179-site/` re-runs `configs/full179.toml`'s exact knobs. Against the
published `runs/full179/`:

| model | `label_acc` | `label_bits` published -> now |
|---|---|---|
| `corefer-001` | identical to 9 d.p. | 6.951829 -> 6.954734 (**+0.0029**) |
| `ngram-001` | identical to 9 d.p. | 6.411704 -> 6.412144 (**+0.0004**) |

`type_acc`, `type_bits`, `copy_acc`, `label_floor` and `copy_floor` are all
bit-identical for both.

## Why it is not the readout work

The readouts were added to `MaskedNode.compute` beside the existing counts, and
the `lm` task was added to the run. A control ruled both out: `corefer` re-run
with **`--tasks node` only**, on the current code, gives
`label_bits = 6.954734341965252` — the *same* drifted number, to the last digit.
The presence of the `lm` task and of the readouts changes nothing.

## What it probably is, and why that is a guess

Every accuracy holding while bits move is the signature of a **post-hoc
monotone rescaling**: dividing log-probabilities by a positive constant cannot
reorder them, so `_fit_temperature` moves every stated probability and no
prediction. `corefer` now fits `T = 1.1`; the commit that introduced temperature
scaling is titled *"Temperature scaling picks T=1"*.

So something between `8847da3` (where the published summary was committed) and
`e34b2bd` moved the back-off enough to move the fitted temperature by one grid
step. The two candidates, neither checked:

* `f0e403d` — every `RuleBasedModel` gained a `text_parser` and a
  `self.text_parser.fit(...)` call inside `fit()`, before `_fit_backoff`.
* `886ddf2` — `collate_graph` gained `languages` in `meta` and `GraphView`
  gained `language`.

The published run's `model.pt` was deleted by *"Keep the evidence, drop the
weights"*, so the old temperature cannot be read off disk; it has to be
re-derived by checking out the commit.

## Why it is worth chasing rather than shrugging at

It is 0.04% and it does not change a single ranking. What it *does* change is
the claim that a versioned name pins a number — the whole reason
`symbolic_ai_core/registry.py` exists. `corefer-001` published one `label_bits`
and now produces another, with no commit anywhere saying so, which is the exact
failure the registry docstring says has already happened twice.

## What would answer it

`git worktree add` at `8847da3`, run `corefer` node-only under
`configs/full179.toml`, and bisect forward over the ~10 commits that touch
`models/symbolic.py` or `data/batch.py`. One run is ~200s, so the whole bisect
is under an hour. Then either re-run the affected rows of `runs/full179` or say
in `RESEARCH_LOG.md` which commit redefined them.
