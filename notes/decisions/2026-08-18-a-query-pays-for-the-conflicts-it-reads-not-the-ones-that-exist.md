---
title: Pre-registration — a query should pay for the conflicts it reads, not for the conflicts that exist
date: 2026-08-18
status: preregistered
tags: [fusion, ambiguity, gleif, preregistration]
---

## The fork

`possible_answers` enumerates the **whole** mixture: `world_count()` is the
product over every retained conflict in the world, so 251 GLEIF conflicts give
2^251 worlds and every query is refused — including "who ultimately owns this
one company", whose answer depends on **one** of them. The module's own
"what would refute it" says so: *"A query touching 30 interacting conflicts is
refused rather than answered, and the useful thing there would be to reason
about the answer set symbolically instead."*

There are three ways out and they are not equivalent:

1. **Set propagation** — carry a set of possible values per node and take
   unions. Linear, and **wrong** the moment a query reads the same conflict
   twice, because the product of two independently-derived sets contains pairs
   no single world produces. This is the cheap answer and it is the one I
   expect to over-approximate; it is built here as a **control that must
   fail**, not as a candidate.
2. **Scoped enumeration** — discover which conflicts the computation actually
   reads, by handing it a recording assignment, and enumerate only those. Exact
   by construction, cost `2^(conflicts read)` rather than `2^(conflicts that
   exist)`.
3. **Additive bounds** — when the read set is genuinely large *and* the answer
   is a sum of independent per-subject contributions, the extreme worlds are
   found term by term. Exact bounds, linear, no enumeration.

2 and 3 divide the space cleanly: 2 handles a local query over a huge mixture,
3 handles a global aggregate that genuinely reads everything. What is left —
large read set, non-additive — stays refused, which is honest and is a solver's
job.

## What is predicted, before anything is measured

**Arm 1 — scoped enumeration over GLEIF's 251 retained mixtures.**

- Full enumeration refuses: 2^251. Certain, it is arithmetic.
- Read-set size per entity query: median **1**, max **2**, and **fewer than 10**
  of the 117,129 entities read two or more conflicts. Basis: the prior finding
  measured 45 entities whose chain passes through a conflict; a chain through
  *two* conflicts is rarer than that.
- Scoped answers are identical to full enumeration restricted to the reachable
  conflicts, on 100% of a checked sample. If this is not 100% the mechanism is
  wrong, not approximate.

**Arm 2 — set propagation as the control.**

- Pairs of distinct entities that share a conflicted ancestor: order 100–400
  (a conflicted node has mean 1.21 descendants and max 18, and C(18,2)=153).
- On the query "do X and Y have the same ultimate owner", where both answers are
  determined by the *same* conflict, every world agrees and the truth is a
  single answer. Set propagation will report two. Predicted wrong on **>=90%**
  of such pairs; scoped enumeration wrong on **0**.

**Arm 3 — additive bounds over the SEC->GLEIF alignment mixture.**

- The alignment leaves ~14.7% of matched filers with more than one GLEIF
  candidate. The query "how many matched filers are US-domiciled" reads every
  one of them, so scoped enumeration **also** refuses — this is the case arm 2
  does not cover, and that is why arm 3 exists.
- Bounds width ≈ the number of ambiguous filers whose candidates disagree on
  country, which the prior finding put at 51.3% of ambiguous ones. Predicted
  width within ±20% of `0.513 × ambiguous`.
- On a 12-conflict subsample the bounds equal the enumerated min and max
  **exactly**. Not approximately: they are the same number or the method is
  broken.

## What would make this a failure worth recording anyway

If the read set turns out to be large for ordinary queries — if GLEIF's chains
routinely pass through many conflicts — scoped enumeration buys nothing and the
honest report is that the bound was not the obstacle. That is a real possible
outcome and it is what arm 1's read-set distribution decides.
