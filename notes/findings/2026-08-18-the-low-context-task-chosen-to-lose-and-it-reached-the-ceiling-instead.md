---
title: I picked a task to show the symbolic side losing at the low-context end, and it reached the ceiling — the 0.05 gap was my effort, not a boundary
date: 2026-08-18
status: provisional
tags: [real-data, cost, effort, sec-edgar, negative-result]
---

## Why I built this one

Three real-data tasks all sat where the substrate is strong: the answer lives in
structure a model must be *given*, and the advantage ran 6,750x → 1.5e6 →
1.85e11 with the size of that context. Every one confirmed the curve, and every
cost row rested on an **assumption I had never tested** — that the symbolic
method and a language model reach equal accuracy.

So I went looking for the task that breaks it: **~10 tokens of context, and a
great deal of knowledge about how company names work.** Normalising
`Chocoladefabriken Lindt & Spruengli AG/ADR` to
`chocoladefabriken-lindt-spruengli-ag-adr` is the shape a model is good at and a
rule is bad at. Ground truth: 8,021 `same_as` bridges filed in SEC EDGAR.

**Prediction: floor ~0.30, a careful hand-written rule 0.85–0.90, and a residual
of genuine judgement that a rule cannot reach.**

## What happened, in four steps

| | accuracy | |
|---|---|---|
| floor — slugify, strip nothing | **0.1046** | predicted 0.30, **wrong** |
| hand-written rule v1, trailing suffixes | **0.8870** | predicted 0.85–0.90, right |
| hand-written rule v2, medial suffixes | **0.9479** | predicted ~0.95, right |
| **fitted rule, held out** | **0.9998** | predicted ≥0.98, right but under-called |

At v1 I looked at the residual and it looked like judgement. It was not: 68.9%
of it was one pattern — `WATERS CORP /DE/` puts the legal form in the *middle*,
before a state code, and my rule only stripped trailing tokens. Fixing that gave
v2.

At v2 the residual looked like judgement again — `SUBURBAN PROPANE PARTNERS LP`
keeps `partners` while `Silvercrest Asset Management Group Inc.` drops `group`.
I formed the hypothesis that the labels were **inconsistent**, which would put a
ceiling below 1.0 on any name-only method *including a language model*, and set
out to measure it.

**The hypothesis was wrong and the measurement was emphatic.** Every token is
treated with perfect consistency:

| always kept | always dropped |
|---|---|
| `trust` (254/254), `partners` (57/57), `limited` (46/46), `sa` (33/33) | `inc` (4125), `corp` (1580), `ltd` (945), `holdings` (607), `group` (509), `co` (400), `plc` (150) |

Zero tokens treated both ways. **The ceiling is 1.0000.** My two hand-written
lists were simply wrong about four tokens.

Fitting the strip set from a training half — a token is dropped if it is dropped
in a majority of at least 3 occurrences — and evaluating on the **held-out**
half gives **0.9998**, one error in 4,011, with train and test identical so
nothing is overfitted. The fit rejected 13 tokens from my hand list, including
`limited`, `partners`, `sa`, `trust` and `nv`, and found one I had missed:
`the`.

## What this actually says

**The 0.052 gap between my second hand-written rule and the ceiling was effort,
not a capability boundary.** I twice looked at a residual, saw something that
looked like it needed world knowledge, and was twice wrong — the first time it
needed a better traversal rule, the second time it needed one pass of fitting.

That is the same thing this repo has already found once, in a different costume:
*effort, not architecture, predicts who is on the Pareto front*. What is new is
the failure mode attached to it. **"This residual needs judgement" is what a
residual looks like before you have understood it**, and it is a conclusion that
sounds sophisticated while being an unexamined claim about one's own last
attempt.

## What it does to the curve

The fourth point, and the low end is now **measured** rather than assumed:

| task | context an LLM must be given | symbolic accuracy | ceiling |
|---|---|---|---|
| **company key from a name** | **~10 tokens** | **0.9998 held out** | 1.0000 |
| country from a coordinate | ~40 tokens | 0.9078 | unmeasured |
| shortest path | 233k tokens | exact | exact |
| ultimate parent | 1.99M tokens | 0.9785 | — |

At the low-context end the cost advantage is small — a ~10-token query is nearly
free for a model too — and the honest reading is **not** "use the model there".
It is that the symbolic method reaches the task's ceiling, so the choice at the
low end is decided by something other than accuracy, and at the high end there
is no choice to make because the context does not fit.

The one task where I set out to show the substrate losing is the one where its
accuracy is now best established.

## What would refute it

- The ceiling of 1.0 is measured over tokens **in my suffix list**. A token
  outside it that is treated both ways would lower the ceiling and I have not
  swept every token in the corpus.
- 8,021 rows from one snapshot of one regulator. Company-name conventions are
  jurisdictional and this is almost entirely US filings.
- The fitted rule is fitted on *these* labels. A different registry's
  normalisation would need a refit, which is exactly the cost a language model
  does not pay — and that portability difference, not accuracy, is the real
  argument for the model at this end of the curve.
