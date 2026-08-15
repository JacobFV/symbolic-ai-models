---
date: 2026-08-14
author: agent-generation
status: provisional
related: [2026-08-14-the-curriculums-own-question-asked-on-the-graph,
          2026-08-14-the-infilling-ladder-preregistration,
          2026-08-13-a-ranking-is-a-property-of-a-metric,
          the-readout-survives-both-attacks-and-its-comparison-row-does-not]
---

# `corefer-001` scores 0.492 where the answer is visible elsewhere and 0.003 where it is not

**All 179 lessons, 716 evaluation episodes, 5,347 scored fills, `runs/infill-node-r015`,
`mask_rate=0.15` — the published masked-node setting.** Computed by
`scripts/copyable_split.py`, which reloads the sweep's own fitted model and
splits the fills it already scores by one bit that was already in the batch:
whether `target_source` found a **visible** node carrying the same label.

`label_acc` has been this repo's central number since the beginning. It is a
mixture of two questions, in a 72:28 ratio, and nothing has ever reported them
apart.

| model | copyable share | acc \| copyable | acc \| **not** copyable | acc (published) | gap |
|---|---:|---:|---:|---:|---:|
| `corefer-001` | 0.723 | 0.492 | **0.003** | 0.357 | **0.489** |
| `ptrgen-001` | 0.723 | 0.456 | **0.014** | 0.334 | 0.442 |
| `grammar-001` | 0.723 | 0.163 | 0.188 | 0.170 | **−0.025** |

**`corefer-001`'s masked-node competence is coreference and nothing else.** Where
the answer is in plain sight somewhere in the same graph it gets half of them;
where it is not it gets three in a thousand — the same nothing it scores on the
curriculum's own answer (0.001, `runs/infill-ans`), which is 0% copyable by
construction. The two measurements are the same fact seen twice.

**`grammar-001` is flat, and that is the control.** A vocabulary model names, and
naming works equally well whether or not a copy happens to be visible: 0.163
against 0.188, a gap of −0.025, i.e. slightly *better* where copying is
impossible. So the split is not an artefact of "copyable fills are easier" — for
one of the three models they are marginally harder. What separates the columns is
the mechanism, not the difficulty.

## What this explains

- **The 0.423 readout gap.** `repair` masks scattered nodes, so 72% of its
  decisions are copyable, and reading `corefer-001` as a move scores 0.508.
  Reading it as text asks it to *spell*, which it cannot do at all. Both numbers
  are what "this model copies" predicts.
- **Rung 3.** The curriculum's answer is the non-copyable case in its purest
  form, and every equivariant model lands on the abstention row there.
- **The 0.722 copy ceiling.** Already published as "more than half the reachable
  signal is untouched". The sharper reading is that essentially *all* of the
  signal these models reach is inside the ceiling, and the region outside it is
  untouched in the strong sense of 0.003.

## What would refute it

- **A model with a large gap on a task where copying is unavailable.** If some
  registered row scores well on `nodeans` while being renaming-invariant, the
  account is incomplete. Twelve were tried; none did.
- **The split being an artefact of node type.** Copyable fills might be
  systematically `ident` leaves and non-copyable ones something harder.
  `grammar-001`'s flat columns argue against it but do not settle it: the right
  test is the split *within* a node type, and it has not been run.
- **A pre-registered prediction for the mask-rate curve, written before those
  numbers existed** (the 0.35 / 0.60 / 0.90 arms were still running when this
  paragraph was committed): raising the mask rate lowers the copyable share
  mechanically, because `target_source` only accepts a **visible** same-label
  node. If this account is right, a pointer's `label_acc` should track
  `copyable_share(rate) × acc|copyable` with `acc|copyable` roughly flat. If
  instead `acc|copyable` *itself* collapses with the rate, the models are losing
  the ability to copy and not merely the opportunity, and that is a second
  effect this note does not predict.

## Provisional

Author-designed controls only. The flat `grammar-001` column is the one that
could have failed and did not, but an independent refuter should try the
within-type split before this is promoted.
