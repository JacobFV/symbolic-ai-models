---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-frontiers-paths-cap-at-0412-and-corefer-is-already-past-it,
          2026-08-17-the-non-copyable-gain-is-entirely-vocabulary-measured-at-last,
          2026-08-17-corefers-entire-type-advantage-is-one-conjunct,
          2026-08-17-a-rule-is-verified-on-the-population-its-guard-admits]
---

# Adding a chosen path lifts the ceiling from 0.412 to 0.520 — past `corefer` — and the constraint moves from representation to selection

The previous finding measured that frontier's ten **fixed** paths reach the
answer on **0.4124** of copyable fills under renaming, while `corefer-001`
scores **0.4920** — above the ceiling — and that frontier was already at 74% of
its own limit. It licensed exactly one change: a path that ranges over every
visible node.

`frontier-point` adds the pointer as an eleventh **path** rather than a new
resolver form, so guards, the cross-fit, the ranking, the MDL tie-break and the
per-key gate all apply to it unchanged and `copy:point` is "copy whatever the
pointer chose". The pointer is `corefer`'s stage one and nothing more — naive
Bayes over relation, distance and direction, with **neither** its prose feature
nor its reranking stage.

## Four predictions, all held

| # | predicted | measured |
|---|---|---:|
| 1 | the reachable ceiling rises above 0.4124 | **0.5200** |
| 2 | renamed `acc \| copyable` rises above 0.306 | **0.340** |
| 3 | `label_acc` rises above 0.4414 | **0.446** |
| 4 | it does **not** reach `corefer`'s 0.4920 | 0.340 |

| model | label acc | bits | type acc | type lift | renamed | ren `acc\|cp` |
|---|---:|---:|---:|---:|---:|---:|
| `frontier-typepoint` | 0.4414 | 7.141 | 0.8689 | +0.062 | 0.2207 | 0.306 |
| **`frontier-point`** | **0.4460** | **7.092** | **0.8760** | **+0.112** | **0.2480** | **0.340** |
| `corefer-001` | 0.3572 | 6.955 | 0.9458 | +0.612 | 0.3499 | 0.492 |

## The diagnosis has inverted, and that is the result

The ceiling is now **0.5200**, and `corefer` scores **0.4920**. For the first
time frontier's hypothesis language can express what `corefer` achieves. The
remaining 0.152 gap is therefore **selection, not representation** — the opposite
of what every previous round on this model concluded.

The efficiency number says the same thing from the other side: frontier used
**74%** of its old ceiling (0.306 of 0.4124) and uses **65%** of the new one
(0.340 of 0.5200). Widening the language left the search with more headroom that
it is not taking, which is the honest cost of the change and the next thing to
work on.

## An independent replication that fell out of it

The pointer's own top-1 pick is right on **0.4449** of copyable fills.
`corefer-001`'s docstring, written long before this model existed, records that
"the correct node is in stage one's top ten about 78% of the time it exists,
against **44%** at top one". Two separately written naive-Bayes pointers over the
same three feature families agree to within a fifth of a percent — which is
either a strong replication or a sign that this curriculum's coreference is
almost entirely determined by relation, distance and direction, and both readings
are worth having.

## The type head got better for free, and that was not predicted

`type_lift` went **+0.062 → +0.112** and `type_acc` 0.8689 → 0.8760. The pointer
extends the *type* paths too, so `copy:point` is available to the type head — and
[[2026-08-17-corefers-entire-type-advantage-is-one-conjunct]] measured that the
pointed-at type is the whole of `corefer`'s +0.612. This is the same term
arriving by a different route, and it is the first thing all day to move that head
by more than a rounding error without being aimed at it.

It is still a sixth of `corefer`'s, and
[[2026-08-17-the-conjunct-does-not-transfer-the-pointer-was-the-thing]] already
said why: the conjunct is worth what the pointer behind it is worth, and this
pointer is stage one without a reranker.

## What is now the open question

**Selection.** Frontier reaches 65% of a ceiling that is finally high enough. The
things that decide which rule fires — the Wilson ranking, first-match-wins,
`_useful`, the guard lattice — have never been examined with a language this wide
underneath them, and every one of them was tuned when the ceiling was 0.41.
