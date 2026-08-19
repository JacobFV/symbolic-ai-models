---
title: Structure is load-bearing exactly where the signature does not fix the predicate
date: 2026-08-19
status: measured
arm: structure-dependence-law
domains: flood, scheduling
---

## The question

Flood's reader collapses to 0.000 when sentences are interleaved, and its
residual is [[2026-08-19-the-empty-cell-is-closed-and-distinguishable-is-not-identifiable|closed to content-free reading]].
Is that a property of the pipeline, or of flood?

**Proposed law.** A domain is structure-dependent exactly to the extent that its
entity names do not carry their roles. Flood names every place `region_N`, and
`region_0` may be the depot, a flooded district or the delivery site, so
*structure* has to assign the role. Scheduling names them `job_3` and
`machine_1`: the prefix **is** the type.

## The numbers, which do not settle it

At V=4, 40 cases per domain:

| domain | role-typed entities | grouped | interleaved | drop |
|---|---:|---:|---:|---:|
| flood | 0.571 | 1.000 | 0.000 | **1.000** |
| scheduling | 0.917 | 1.000 | 1.000 | **0.000** |

That looks like a clean confirmation and the script said so. **It is not**, and
the confound is one I wrote into the prediction before running it: scheduling may
be immune because it has *no cross-sentence binding to destroy*.

| | claims whose own span names every entity it is about |
|---|---:|
| flood | 0.755 |
| scheduling | **1.000** |

Scheduling is fully self-contained. That alone would make it immune whatever its
names were, so the pair does not test the law.

## What settles it: which claims flood loses

| kind | pronoun-realised | grouped | interleaved | drop |
|---|---:|---:|---:|---:|
| **depot** | 0 | 1.000 | 0.000 | **1.000** |
| **flooded** | 0 | 1.000 | 0.000 | **1.000** |
| **needs** | 0 | 1.000 | 0.275 | **0.725** |
| demand | 40 | 1.000 | 0.275 | 0.725 |
| link | 0 | 1.000 | 1.000 | 0.000 |
| bridge_on | 0 | 1.000 | 1.000 | 0.000 |
| mass | 0 | 1.000 | 1.000 | 0.000 |
| **capacity** | **40** | 1.000 | 1.000 | **0.000** |
| **load_limit** | **40** | 1.000 | 1.000 | **0.000** |

**Every claim flood loses is self-contained.** Depot, flooded and needs each name
their own region and are realised by no pronoun at all. Meanwhile the two kinds
realised *entirely* by a pronoun — capacity and load_limit — lose **nothing**.
Demand drops only because `needs` drops, and it is bound to it.

Worst drop among fully pronoun-bound kinds: **0.000**. Among self-contained
kinds: **1.000**.

So cross-sentence binding is not the mechanism, and scheduling's
self-containment is not what protects it — flood's failing claims are
self-contained too.

## The law, restated precisely

**Structure is load-bearing exactly where a sentence's signature does not
determine its predicate.**

In flood, `(one region, no number, no vehicle)` may be a depot, a flood report or
a delivery site — a three-way ambiguity the type signature cannot touch — so the
role must come from arrangement, and destroying arrangement destroys the reading.
In scheduling the `job_`/`machine_` prefix fixes the predicate outright, so there
is nothing for arrangement to carry.

Role-typed naming is one way to get signature-determinacy, which is why the
measured `role_typed` fraction (0.571 vs 0.917) tracks it — but the mechanism is
the determinacy, not the naming.

**This predicts where text→world is hard before any reader is built:** ask
whether the sentence signatures fix their predicates. Where they do, a
content-free reader will do; where they do not, arrangement is doing the work,
and if arrangement is not reliable in the real documents then content is
required.

It also explains the earlier closure result rather than merely coexisting with
it. The residual that no content-free observable can settle is exactly the group
the signature leaves open.

## What would refute this

The clean test is a domain with **signature-ambiguous predicates but no reliance
on arrangement**, or the reverse. Neither exists in the three domains here:
flood is ambiguous-and-structural, scheduling is determinate-and-self-contained,
and solvency has no committed reader module to measure (its 1.000 came from a
script). Constructing the missing cell — flood renamed so the prefixes carry the
roles, leaving everything else identical — would turn this from a two-point law
with a mechanism into a manipulation. That is the next test, and it is cheap.

Until then this is **a mechanism confirmed by decomposition, on two domains**,
not a law confirmed by manipulation. The decomposition is what does the work: the
aggregate numbers are confounded and the per-kind table is not.
