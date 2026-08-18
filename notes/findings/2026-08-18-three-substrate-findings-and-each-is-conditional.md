---
title: Three flood findings met a second task today and none of them is universal — each turns out to hold in a regime, and the regimes are measurable
date: 2026-08-18
author: lead
status: provisional
tags: [synthesis, generalisation, second-task]
---

## What this collects

Until this morning every substrate finding came from one generated task. The
solvency task exists to test which of them are properties of the substrate and
which are properties of flood logistics. Three were checkable. **None survived as
stated**, and all three survive with a stated regime.

## 1. "Recall errors hurt more than precision errors"

Measured on flood at **1.76×** and generalised to enumerate-then-filter pipelines.
Solvency reproduces **1.74×** — at one covenant margin, and nowhere else:

| decision margin | drop / misread ratio |
|---|---|
| 0.00 | 1.40 |
| 0.25 | **1.74** ← flood's regime |
| 1.00 | **0.11** ← inverted |

The variable is the **ratio of the decision margin to a typical error**, not the
kind of fact. Missing a term is bounded and additive (~1/n of the total);
misreading one is unbounded and multiplicative. Full write-up:
`2026-08-18-recall-beats-precision-only-in-the-middle.md`.

## 2. "Routing pays in proportion to what is downstream of the gate"

Not testable on solvency, and the reason is a number rather than an opinion:

| | flood | solvency |
|---|---|---|
| pipeline cost / episode | 1.2 × 10⁻⁸ | **6.7 × 10⁻¹¹** |
| ratio | — | **179× cheaper** |
| the kernel's share | ASP+SMT 68% | economy 62% |

Flood's **router node alone**, before it was optimised, cost 1.4 × 10⁻⁹ — **21×
solvency's entire pipeline**. There is nothing to route around. So the routing
result is a property of *pipelines containing expensive solvers*, not of the
substrate, and a task whose whole cost is a dictionary walk cannot exhibit it in
either direction.

That is worth stating rather than filing as "untested": a reader who takes
"routing saves 13%" as a substrate property will look for the saving in a
pipeline that has none.

## 3. "$/solved-above-floor has a perverse regime"

This one **is** universal in its stated form, because it was derived rather than
measured: a lossy arm wins iff

    Δcost / cost  >  Δacc / (acc − floor)

and the right-hand denominator is large whenever accuracy sits far above the
floor. The flood numbers were an instance; the algebra is not task-specific. It
is the only one of the three that did not need a second task, and noticing *that*
is the useful part — a claim with a derivation behind it travels, and a claim
with only a measurement behind it does not.

## The pattern

> **A measured claim about a pipeline is a claim about a regime until something
> tells you which regime.** Two of the three needed a second task to find the
> boundary; the third had an argument and needed none.

Concretely, for the substrate's own record: findings from a single task should
carry the regime they were measured in — decision margin, cost concentration,
accuracy distance from the floor — because those are the axes that turned out to
matter, and none of them was recorded in the original notes.

## What would have refuted the synthesis

- **The second task being a near-copy of the first.** It is the structural
  opposite: aggregate-and-compare rather than enumerate-and-filter, one boolean
  rather than a subset, temporal rather than spatial, and 179× cheaper.
- **The regimes being unmeasurable.** Both boundaries were swept, not argued —
  the ratio inversion across five margins at N = 1,200, and the cost gap directly
  from the two traces.
- **The third finding quietly failing too.** It cannot: it is algebra, and the
  test that pins it uses the measured flood numbers rather than synthetic ones,
  so it fails if the arithmetic ever stops describing them.
