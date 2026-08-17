---
date: 2026-08-16
author: agent-softreason
status: provisional
prereg: notes/decisions/2026-08-16-softreason-preregistration.md
---

# The distribution output buys 0.80 bits over the best pointer; the fixpoint iteration then gives 0.17 of them back

Scouting arm. One sweep, `configs/full179.toml`, `--tasks node`, the same floors
as every other row in `runs/full179`. Not refuted by anything independent yet.

## The numbers

| model | `label_acc` | `label_bits` | `type_acc` | renaming |
|---|---|---|---|---|
| **softreason-001** (fixpoint, ≤4 rounds) | **0.3071** | **6.3165** | 0.8482 | 0.307 -> 0.300, **-0.007** |
| **softreason-onehop** (`T_P` applied once) | **0.3193** | **6.1479** | 0.8482 | 0.318 -> 0.314, **-0.004** |
| floor | 0.1432 | 9.3695 | 0.8601 | — |
| best prior bits: `grammar-001` | 0.187 | 6.089 | 0.798 | — |
| best prior acc: `corefer-001` | 0.357 | 6.952 | 0.946 | — |

`label_n` 5,233; `label_coverage` 0.825; copy ceiling 0.722. Both rows carry the
identical type head (`corefer`'s `_type_keys` lookup, imported), so the type
column is deliberately uninformative about the difference between them.

## Did the pre-registered prediction hold? Yes, on both halves.

1. **"at or near the best `label_bits`", called at ≤ 6.4.** `softreason-001` is
   6.3165 — 5th of 25 rows overall, 0.23 behind `grammar-001`. `softreason-onehop`
   is 6.1479, **2nd of 25**, 0.06 behind `grammar-001` and ahead of every other
   model including the neural `rgt-001`. Met.
2. **"NOT near the top on `label_acc`", predicted in the 0.25–0.34 band and below
   `corefer-001`'s 0.357.** 0.3071 and 0.3193 — 10th and 8th of 25. Met, and the
   predicted band was right rather than merely wide.

Neither refutation condition fired: bits are nowhere near 8.0, neither row wins
both metrics outright, and both clear the accuracy floor by ~0.17.

## What is actually new here, stated carefully

The repo's standing observation is that `label_acc` and `label_bits` rank these
models close to inversely
(`notes/lessons/2026-08-13-a-ranking-is-a-property-of-a-metric.md`). Until now
the bits table was owned by models that cannot answer — `grammar-001` 0.187,
`ngram-001` 0.170, `evidence-001` 0.219 — and the accuracy table by models with
poor bits — `corefer-001` 6.95, `workspace-001` 7.81, `omegaclaw_rank-001` 8.09.

`softreason-onehop` is the first row that is **top-2 on bits and top-9 on
accuracy at once**, and it is Pareto-optimal: no model in `runs/full179` beats it
on both. The Pareto frontier is exactly four models — `grammar-001`
(6.089, 0.187), `softreason-onehop` (6.148, 0.319), `corefer-001` (6.952,
0.357), `frontier-001` (7.433, 0.404) — and the second did not exist this
morning.

*(Corrected at merge: this arm ran in a worktree branched before `frontier-001`
landed, so it was written against a table without that row. `frontier-001` is
0.4042 accuracy at 7.433 bits, which takes the best accuracy from 0.357 to
0.404 and puts a fourth point on the frontier at the accuracy end. The Pareto
claim survives — `frontier-001` is far behind on bits — and the accuracy rank
moves by one place. Nothing measured here changes.)*

Against the nearest comparable mechanism, `corefer-001` — same relational
features, same task, same floors — it trades **0.038 of accuracy for 0.804 of a
bit**. That is the interface argument in `RESEARCH_LOG.md` cashed out: the loss
was not in the reasoning, it was in collapsing the reasoning to an argmax and
then inventing a scalar for it.

## The result I did not predict, and it is the more interesting one

**Iterating to a fixpoint is worse than applying the operator once, on both
metrics.** `softreason-001` loses 0.012 accuracy and 0.169 bits to
`softreason-onehop`. The two differ in `max_rounds` and in nothing else — same
rules, same reliabilities, same gate procedure, same type head, same candidate
truncation — so the comparison is clean and the sign is unambiguous.

The reading I believe, offered as a hypothesis and not as a measured claim: the
second round lets a hidden node's *derived* mass enter another hidden node's
body, and derived mass on this curriculum is mostly wrong. Noisy-OR is monotone
increasing, so round 2 can only *add* support — it never retracts — and what it
adds is a hidden neighbour's error, laundered into the conclusion set at a
truth value the reliabilities were fitted against *visible* bodies to justify.
Closure over a soft program with no negation and no retraction is an error
amplifier when the ground facts are sparse.

That the control was built in ahead of the run is the only reason this is
readable at all; without the `onehop` row the headline would have been
"a fixpoint reasoner is 2nd on bits" and it would have been the iteration
getting credit for what the output format did.

Two things in `runs/full179/softreason-001/rules.txt` support that reading and
one of them qualifies the model's own name:

- **`T_P rounds to fixpoint: 1x60, 2x382, 3x362, 4x2776`.** 77% of episodes hit
  the round cap of 4 with atoms still moving by more than `tol = 1e-3`. So
  `softreason-001` is *not* a fixpoint model on most episodes — it is a
  four-round model, and the truth values were still climbing when it stopped.
  Since noisy-OR is monotone and there is no negation to retract anything, "still
  climbing" and "still accumulating support for wrong conclusions" are the same
  sentence. The name overclaims and the note should be read with that in mind.
- **The calibrator noticed by itself.** Fitted independently for each row on the
  same held-out episodes, the gate saturates at **0.73** for the fixpoint and at
  **0.82** for one-hop, and starts lower across every bin (0.56 vs 0.47 is the
  one exception, at the least-peaked bin). `MassCalibrator` is maximising held-out
  likelihood with no knowledge of which row it is fitting, and it independently
  decided the iterated conclusions deserve less of the mixture's mass. That is a
  second, procedurally separate witness to the same finding.

Both rows induced the identical 1,407 weighted rules from 1,268,412 pairs at a
global same-symbol rate of 0.088, which is the check that the two differ only in
the operator: `sibling` at distance-bucket 4 reaching backwards tops the table at
`r = 0.859` in both.

## What was measured against what

- **Floor:** the sweep's own `label_floor_bits` 9.3695 / `label_floor` 0.1432,
  identical for every row in `runs/full179`.
- **Control for the closure:** `softreason-onehop`, registered beside, one axis.
- **Control for the output format:** `corefer-001` and `ptrgen-001`'s published
  rows — same features, argmax-plus-scalar and pointer-plus-gate respectively.
- **Renaming:** the sweep's own line. **-0.007 and -0.004** — essentially
  invariant, which is what a model reading only structural patterns should be.
  Compare `ensemble-001`'s 1.14-bit headline dying at -0.43 under this same
  permutation. Nothing here is memorising symbol identity.

## What would refute it

- An independent tracer finding the gate's score (`max(mass)/sum(mass)`) is
  correlated with the answer through some path I have not seen. The gate is
  fitted on the held-out 20% of training episodes, and `_pattern` reads no
  label of either node, but I have traced this myself and that is an input, not
  a verdict (`notes/lessons` on self-computed curves).
- The bits win surviving only because the type head was imported: if
  `softreason` with its own type head loses the bits, the label claim is
  entangled with a head it did not build. Cheap to check, not checked.
- A `MassCalibrator` ablation — `ptrgen` records the calibrator as worth ~0.58
  bits on its own, so a `softreason-argmax` row would say how much of the 0.80
  is the distribution and how much is the fitting procedure. **This is the
  single most important missing control** and the honest caveat on everything
  above: the 0.80 bits against `corefer` changes two things at once.

## Correction to the brief that commissioned this

The task named `frontier-001` at `label_acc` 0.404 as the repo's best accuracy.
There is no `frontier_001` package and no such row; the actual best in
`runs/full179` is `corefer-001` at 0.3572. The bits figure (6.089) and floor
(9.369) in the brief were correct. Pre-registration was written against the
numbers that exist.
