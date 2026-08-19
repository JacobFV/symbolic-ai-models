---
title: The reader's target is [W]_K, and the audit already measures how much of W that leaves out
date: 2026-08-19
status: measured
arm: influence-weighted-reconstruction
supersedes: >
  Folds in "claim recall is the wrong reader column" as a special case, and
  connects the certificate, the uncorroborated marker and the explanation/answer
  divergence as instances of one quantity rather than three threads.
---

## The question this answers

*What information must be recovered, with what fidelity, for cheap structured
computation to remain useful?* Formally, with `X --R--> Ŵ --K--> Y` and
`W₁ ~_K W₂ ⟺ K(W₁) = K(W₂)`: the reader does not owe `Ŵ = W`, it owes
`Ŵ ~_K W`. So the useful measure of a reconstruction is not how much of `W` it
recovered but **whether its errors leave the equivalence class**.

Define influence by **intervention on the true world**: a missing claim is
influential if deleting it from `W` changes `K(W)`; a spurious one if adding it
does. **Critical error mass** is the count of influential claims in the symmetric
difference `Ŵ △ W`.

## The standard extraction metrics are at chance

130 non-empty flood cases on the honest surface, 87 correct and 43 wrong. AUC is
the probability the metric ranks a correct case ahead of a wrong one:

| quantity | mean \| correct | mean \| wrong | **AUC** |
|---|---:|---:|---:|
| claim recall | 0.996 | 0.995 | **0.506** |
| claim precision | 0.931 | 0.930 | **0.473** |
| symmetric difference | 2.230 | 2.279 | **0.506** |
| **critical error mass** | **0.184** | **1.233** | **0.946** |

**Recall, precision and raw error count carry no information about whether the
answer is right.** Not "less than we hoped" — *at chance*, all three. The reader
makes 2.2 errors on the cases it gets right and 2.3 on the ones it gets wrong.

## One direction is exact

| | n | |
|---|---:|---|
| critical mass **= 0** | 82 | **correct on 1.000** |
| critical mass **> 0** | 48 | wrong on 0.896 |

**Zero critical mass ⟹ `Ŵ ~_K W`, with no exceptions in 82 cases** (rule of
three bounds the failure rate at ~3.7%). That is a characterisation, not a
prediction: it says exactly which reconstructions are good enough.

The converse fails on **10.4%** — influential errors whose effects **cancel**.
Single-claim intervention cannot see joint influence, and flood is already known
to have jointly-critical pairs in 5 of 14 non-empty cases, so a residual of
exactly this kind was predicted before the run.

## And the audit measures the weighting offline, before any reader exists

Per-kind influence, measured through the reader's *actual* errors:

| kind | errors | influential |
|---|---:|---:|
| `link` | 260 | **0.169** |
| `depot` | 16 | **1.000** |
| `flooded` | 16 | 0.562 |
| **all** | 292 | **0.236** |

`audit.deletion_dependency` computes the same quantity **offline, on true worlds,
with no reader involved**, and reported flood's link dependency as **0.138**
against the **0.169** observed here. `depot` at 1.000 matches the earlier finding
that a misassigned role is never inert while a spurious link usually is.

So the instrument that predicts reader difficulty also predicts **how much
influence-weighting buys**, and it does so before a reader is written.

## The law, and its limiting cases

> **Critical mass ≈ d · |Ŵ △ W|**, where `d` is the deletion dependency of the
> error mix. Influence weighting separates exactly when **d < 1**.

- **d → 1** — every claim is pivotal, so critical mass *is* the symmetric
  difference and the ordinary metrics are already correct. Solvency's `revenue`
  channel is measured at d = 0.000 decided, i.e. every filing moves the sum: there
  is nothing for weighting to buy.
- **d → 0** — every claim is inert, the answer is corruption-proof, and no
  reconstruction metric matters.
- **flood** sits at d = 0.236 across its error mix, which is why the gap between
  0.506 and 0.946 is as large as it is.

The reader's target is therefore **not fidelity to `W` but coverage of the
influential set**, and the size of that set is a property of the *domain*,
measurable offline, not of the reader.

## What this unifies

Three results that were separate threads are instances of this quantity:

- **the certificate** is a proof that critical mass is zero *without knowing `W`*
  — which is why it buys soundness and an honest explanation from one check;
- **the uncorroborated marker** works because `render_complete` cites the
  load-bearing set, i.e. exactly the influential claims, so fabrications
  concentrate there;
- **the explanation/answer divergence** is the same quantity at a different
  aggregation depth: an explanation is wrong if *any* claim it cites is wrong, the
  answer only if a *critical* one is.

## What would refute this

- One domain, one reader, one error distribution. The exact direction rests on 82
  cases and the residual on 5.
- Influence is measured by **single-claim** intervention. The 10.4% residual is
  the visible cost of that; a joint measure is `O(n²)` and was rejected earlier on
  those grounds.
- The audit-vs-observed agreement is 0.138 against 0.169 on one kind. That is
  close, and it is one point.
