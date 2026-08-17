---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-type-bits-was-never-compared-and-it-inverts-the-type-ranking,
          2026-08-13-a-ranking-is-a-property-of-a-metric,
          2026-08-13-a-control-that-could-fail]
---

# `corefer-001`'s +0.612 type lift is the pointed-at node's type, and everything else it does for types is worth −0.065

`RESEARCH_LOG.md` has recorded since the beginning that node type is very nearly
determined by tree shape — a content-blind backed-off lookup reaches **0.8601** —
and that **only two of nineteen models clear it**, `corefer-001` at +0.612 and
`rgt-001` at +0.395 (a network). That fact has been load-bearing for a long time
and has never been decomposed.

`corefer`'s type key is a backed-off conjunctive ladder over
`(ptype, slot, depth, arity, sibling type, pointed type)`. The floor is a lookup
of *exactly that shape* minus the last term. So the whole advantage might be one
conjunct — the type of the node its coreference pointer selected, which nothing
else in the registry has.

## The ablation

`corefer-nopoint` drops that conjunct and changes nothing else: same pointer,
same ladder, same support threshold, same confidence formula.

| | type acc | type bits | type lift | label acc / bits |
|---|---:|---:|---:|---|
| `corefer-001` | 0.9458 | **0.3479** | **+0.612** | 0.357157 / 6.9547 |
| `corefer-nopoint` | **0.8514** | 0.8300 | **−0.065** | 0.357157 / 6.9547 |
| the type floor | 0.8601 | — | 0.000 | — |

All four predictions held: accuracy falls to ≈0.86 (0.8514), lift to ≈0 (−0.065),
bits rise toward the 0.9 region (0.830), and **every label number is
bit-identical** — the label pointer never reads `pointed`, which is the control
saying this row is the conjunct and nothing else.

**So `corefer`'s type head, minus one term, is slightly *below* the floor.** The
+0.612 that has stood as one of two positive type results in this repo is a
single feature: *what kind of node did my coreference pointer land on*.

## What this says about the type head generally

**The induced type heads need a pointer, not a better rule language.** I spent
the previous rounds giving `frontier`'s type head its own knobs
(`frontier-009`), its own atoms including arity and sibling type
(`frontier-010`), and its own fitted gate (`frontier-typemass`) — reaching 0.8666
accuracy and 0.9342 bits. Every one of those atoms is in `corefer`'s ladder
already. The one it does not have is the pointed type, and this ablation prices
that term at **+0.095 of accuracy and 0.48 of a bit** on a model that otherwise
sits at the floor.

**A second, separable observation.** `corefer-nopoint` is *less accurate* than
`frontier-typemass` (0.8514 against 0.8666) and *better calibrated* (0.830
against 0.934). A backed-off ladder and a rank-ordered induced rule list, at
comparable accuracy, do not produce comparable bits — the ladder falls back to a
more general key with honest support, while the rule list fires its highest-rank
match and lives with that rule's average. That is
[[2026-08-13-a-ranking-is-a-property-of-a-metric]] appearing as a fact about two
*hypothesis languages* rather than two metrics, and it is the second time today
the back-off structure has come out ahead of induction on the estimate while
losing on the decision.

## What would make this less interesting

The pointed type is not free information — it is the output of a fitted
coreference pointer, so "one conjunct" understates the machinery behind the
term. The honest statement is that **the conjunct is where the pointer's value
is cashed for the type head**, not that a single cheap feature is worth 0.612.

And this is one model. `rgt-001`, the other positive row, is a network with no
such conjunct and reaches +0.395 by some other route, which this says nothing
about.
