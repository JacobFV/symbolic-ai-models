---
title: The fusion registry could not group an identity conflict at all, and last-writer-wins rewrote 4,992 measured facts on load order
date: 2026-08-18
status: provisional
tags: [fusion, provenance, real-data, gleif, architecture]
---

## Why this, and not another guard

Five wake-ups went into substrate soundness, and the last audit found nothing
new — two sites, neither a fabrication. That is the signal a vein is worked out.
The layer with **zero real-data evidence** is the fusion registry: every test of
it is synthetic, and the alignment work produced real `Alignment` claims from two
sources and never fused anything.

The real fusion case was already on disk. GLEIF publishes
`IS_DIRECTLY_CONSOLIDATED_BY` and `IS_ULTIMATELY_CONSOLIDATED_BY` separately, so
the closure of the first (an **inference**) and the second (a **filing**) are two
claims about the same property, disagreeing on 4,998 entities.

## Two holes, and the second is structural

**1. A claim could not say how it came to be known.** `derivation_classes` —
`measured`, `derived`, `simulated`, `synthetic`, `reconstructed`, `unresolved` —
exists in `ontology/vocab.yaml`, is enforced by `source/validate.py` on stream
metadata, and travels on artifact manifests. **`Provenance` had no `derivation`
field.** So a claim inferred by a kernel and a claim ingested from a filing were
indistinguishable once in the world, and *derived can never become measured* was
unenforceable at exactly the layer where fusion happens.

**2. The registry could not group an identity conflict.** `_subject` keys a
group on **every** `EntityRef` role. That is right whenever the value is a
number — two mass readings of one robot differ in the number and agree on the
entity, so they group and compete. It is wrong whenever **the value is itself an
entity**: "who ultimately owns this company" puts the rival answer *inside the
key*, so two sources naming two different parents land in two groups and never
meet.

That is not a missing fuser. It is a class of disagreement the registry was
structurally unable to see, and every fuser it shipped with — sum, log-opinion
pool, independent odds, inverse variance, interval intersection — operates on
numbers, so nothing had ever exercised the case.

## What was built

- `Provenance.derivation`, carrying the existing vocabulary to the claim layer.
- `SUBJECT_ROLES` / `register_subject_roles`, so a predicate can declare which
  roles identify its subject. The default is unchanged, so no existing
  predicate regroups.
- `prefer_measured`, the first non-numeric fuser: rank by derivation, keep the
  loser recorded, **preserve the winner's derivation onto the fused claim** —
  otherwise the invariant fails at the last step having been enforced all the
  way upstream — and **refuse a tie**. Two *measured* claims that disagree are a
  real conflict between sources, and resolving it by arrival order is precisely
  the failure the registry exists to prevent.

## Measured on 234,252 real claims over 117,129 entities

**Prediction: 4,998 conflicts; last-writer-wins differs by 4,998 on load order.**

| | agrees with the filing |
|---|---|
| derivation-aware fusion | 117,129 / 117,129, **order-independent** |
| last-writer-wins, filed loaded last | 117,129 |
| last-writer-wins, **closure loaded last** | **112,137** |

**4,992 conflicts, not 4,998** — and the six-entity gap is explained: those are
the ownership cycles, where the closure returns `None` and emits no derived
claim at all. The prediction was off by exactly the cases that produce no claim
to conflict with.

**The 117,129/117,129 is not an accuracy result and must not be quoted as one.**
The filed edge *is* the task's ground truth, so preferring it is circular by
construction. The finding is the other row: **which source happened to load
second silently rewrote 4,992 measured facts — 4.26% of the world — with
inferences.** Order-independence is the property; the accuracy is arithmetic.

## What would refute it

- One predicate, one source, one kind of conflict. `prefer_measured` is
  registered for nothing by default and `ultimate_parent` is the only predicate
  with declared subject roles, so the machinery is exercised on exactly the case
  it was built for.
- The tie refusal raises. That is right for a batch job and wrong for a pipeline
  that must produce *something*, and no caller yet catches it to retain both
  alternatives as the ADR says it should — the claim "alternatives retained not
  collapsed" now has a mechanism that refuses to collapse and still no mechanism
  that retains.
- `derivation` is unset on every claim the eight kernels produce. The field
  exists and nothing populates it, which is the fourth instance this week of a
  contract shipping ahead of its use — named here rather than discovered later.
