---
date: 2026-08-16
author: agent-softreason
status: preregistration
---

# softreason-001: a soft immediate-consequence operator, pre-registered

## What is being built

`softreason-001` — a CPU-only, non-differentiable adaptation of SoftReason
(arXiv:2607.20402). Facts carry soft truth values in `[0, 1]`; logical closure is
an iterated immediate-consequence operator `T_P` run to a fixpoint; the model's
**native output is a distribution over conclusions**, not an argmax with a
scalar confidence bolted on afterwards.

Concretely, per episode:

- **Herbrand base.** Atoms `label(i) = v` for each node `i` and each symbol `v`
  that occurs somewhere in this episode. Nothing outside the episode's own
  vocabulary is derivable — generation is the shared back-off's job, not the
  reasoner's.
- **Ground facts.** `label(j) = v` at truth 1.0 for every visible node `j`.
- **Weighted implications.** One rule schema, `label(i)=v <-_{r} label(j)=v`,
  instantiated for every ordered pair whose structural relationship falls in
  pattern `π`; `r_π ∈ [0,1]` is a reliability fitted by counting how often that
  pattern actually joined two nodes carrying the same symbol, shrunk down a
  back-off ladder toward the global rate.
- **The operator.** Product t-norm on the body, noisy-OR (probabilistic sum)
  over derivations:
  `t_{n+1}(i,v) = 1 - Π_j (1 - r_{π(i,j)} · t_n(j,v))`.
  Monotone and bounded, so it converges; iterated to a fixpoint (tolerance
  `1e-3`, cap 4 rounds). Round 1 is one-hop copying, which is what every pointer
  in this repo already does. Rounds 2+ are the actual claim: a hidden node's
  *derived* mass feeds another hidden node's derivation. That is closure, and
  nothing else in the registry does it.
- **Readout.** The whole fixpoint mass over symbols is emitted as the label
  votes. No argmax anywhere. The gate `c` is fitted by
  `MassCalibrator` on held-out training episodes — likelihood, not accuracy.

Type head is `corefer`'s `_type_keys` backed-off lookup, imported rather than
re-derived, so any label difference is attributable to the label machinery.

## Corrections to the brief's stated baselines

**This section was right about the worktree and wrong about the repo, and it is
left standing with the correction beside it rather than edited away.** The
worktree this arm ran in was branched from a commit *before* `frontier-001` was
merged, so `frontier-001` really was absent from everything this agent could
see, and the pre-registration below is honestly registered against the numbers
it had. On `master` the model exists and scores `label_acc` **0.4042**,
`label_bits` 7.433 — so the brief's figure was correct and the best accuracy in
the table is 0.404, not 0.3572.

What this does and does not change. The prediction was "not near the top on
accuracy", and softreason lands at 0.307/0.319 against a true best of 0.404
rather than 0.357 — so the prediction holds *more* comfortably, not less. The
bits claim is untouched: `frontier-001` is 7.433, well behind, so
`softreason-onehop` at 6.1479 is still second on bits behind `grammar-001`.
Nothing measured here moves; one comparison sentence does.

Read off `runs/full179/*/summary.json` as the worktree had it:

| quantity | holder | value |
|---|---|---|
| best `label_acc` | `corefer-001` | 0.3572 |
| best `label_bits` (lower better) | `grammar-001` | 6.089 |
| `label_floor_bits` | — | 9.369 |
| `label_floor` (acc) | — | 0.1432 |
| copy ceiling | — | 0.7216 |

The bits figure and the floor in the brief are correct; the accuracy figure is
not. The prediction below is registered against the numbers that exist.

## Prediction, registered before the sweep

1. **`label_bits` at or near the best in the repo** — I will call the
   prediction met at `≤ 6.4` (i.e. within ~0.3 bits of `grammar-001`'s 6.089),
   and clearly met at `≤ 6.089`. Reason: the mixture asks for a distribution and
   a fixpoint natively produces one; `MassCalibrator` is then fitting the weight
   of a two-component mixture rather than an argmax accuracy.
2. **`label_acc` NOT near the top** — I expect it *below* `corefer-001`'s 0.3572,
   plausibly in the 0.25–0.34 band, because a fixpoint spreads mass over
   everything derivable rather than committing. It should still clear the floor
   of 0.1432 comfortably; a model that cannot do that has not reasoned at all.

## What would refute it, stated now

- **`label_bits > 8.0`.** The interface argument — that these models score badly
  on bits because they emit an answer where the harness wants a distribution —
  would be wrong, or at least not the binding constraint. That argument is
  currently load-bearing in `RESEARCH_LOG.md`, so this is the outcome worth
  having.
- **Wins both `label_acc` and `label_bits` by a clear margin.** Per
  `notes/lessons/2026-08-13-the-harness-moves-more-than-the-models.md`, the first
  hypothesis is then that the contract changed, not that the reasoning improved.
  Suspect the harness: check the gate is not being handed a score correlated with
  the answer, and check the fixpoint is not reading `labels[i]`.
- **Below the floor on either metric.** Then the operator is doing damage and the
  rule reliabilities are noise.
- **Round-1 and round-4 outputs identical.** Then the closure is decorative and
  this is `corefer` in different clothing. Recorded as a diagnostic in the model's
  `render()`, not as a separate sweep.

## What is deliberately not being done

This is a scouting arm. No renaming refuter beyond the line the sweep prints
itself, no ablation of the iteration count as a registered row, no polished
write-up. One comparable number, honestly obtained.

## Rejected alternatives

- **Lukasiewicz t-norm** (`max(0, a+b-1)`) instead of product. Rejected: with
  reliabilities well under 1 the body truth is almost always 0, so the operator
  derives nothing and the model becomes an abstention. Product degrades
  gracefully; Lukasiewicz needs strong rules this data does not supply.
- **Max-aggregation over derivations** instead of noisy-OR. Rejected because it
  throws away exactly the thing being tested: three mediocre routes to one
  conclusion should outrank one mediocre route, and under `max` they are equal.
- **Adding unary context→symbol rules** (`label(i)=v <- context(i)`). Rejected as
  double-counting: `RuleBasedModel._fit_context_prior` already puts precisely
  that lookup into the back-off every model falls to, so a model that also voted
  it would be scoring the back-off under its own name — the failure mode named in
  `notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name.md`.
