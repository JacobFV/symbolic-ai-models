---
title: Reach has three tiers, not two — closure settles 81.3% of the ambiguity GLEIF recorded structure for, reaches 22.4% of it, and the other 90% of entities have no relationship anyone ever filed
date: 2026-08-18
author: lead
status: provisional
tags: [federation, reach, closure, cost, control-passed, prediction-refuted]
---

## The question

`notes/findings/2026-08-18-purchasable-reach-saturates-...md` closed the
purchasable half of the reach problem with a negative — crosswalk value
**saturates**, so buying more mappings will not close the 68× cliff — and named
what was left as **structural** reach. This measures it.

The mechanism on offer, from the 93.0% cross-validation in that note: the name
join's failure mode is **over-generation**, and entities share a canonical name
because they are *Morgan Stanley & Co*, *Morgan Stanley Bank*, *Morgan Stanley
Capital* — members of one group. GLEIF's relationship file encodes exactly that
and is already on disk. So take the transitive closure and ask whether an
ambiguous filer's candidates land on **one root**.

## The result, and it is a product of two numbers

`scripts/manufactured_reach.py`, over the 598 ambiguous filers of 4,078 matched.

| | | |
|---|---:|---|
| determined at group level, **unconditional** | **18.2%** | 109/598 |
| permutation control | **0.0%** | 0/598 |
| candidates all present in the relationship graph | **22.4%** | 134/598 |
| determined, **conditional on that** | **81.3%** | 109/134 |
| permutation control, same conditional population | **0.0%** | 0/134 |
| GLEIF entities mentioned in any relationship | **10.4%** | 348,836 / 3,348,427 |

> **The mechanism is strong and its reach is narrow.** Where GLEIF recorded the
> relationships, closure settles **four ambiguous filers in five**. It records
> them for **a tenth of its entities**.

I pre-registered 45–70% for the unconditional number with a refutation criterion
at 30%, and by that criterion the mechanism is refuted. It is not — the
prediction named a **product** and could not tell "name-sharing crosses corporate
groups" from "the graph is sparse". See
`notes/lessons/2026-08-18-predict-the-factors-not-the-product.md`.

## What it is worth, and it composes

`f` for a **group-level** question, priced on the same sheet as everything else
(41-token dependency, $15/Mtok, $1.56e-11 ours):

| policy | `f` | advantage | |
|---|---:|---:|---|
| names alone | 14.66% | 6.8× | |
| + wikidata bridge | 9.81% | 10.2× | 1.49× — **acquired** |
| + closure, no acquisition at all | 11.99% | 8.3× | 1.22× — **derived** |
| **+ both** | **8.17%** | **12.2×** | **1.80×** |

1.49 × 1.22 = 1.82 against a measured 1.80: **the two are very nearly
orthogonal.** Buying a crosswalk and reasoning over recorded structure settle
almost disjoint sets of filers, which is the first evidence in this repo that
acquisition and inference are complements rather than substitutes.

And closure cost **nothing**: the relationship file is the same source the
candidates came from, and building both closures takes 0.4s.

## The three tiers

The reach split this repo has been carrying — *purchasable* versus *structural* —
is wrong, and the correction is the finding:

1. **Purchasable.** Crosswalks. **Saturates**: 2,383 rows reach 68.8% of $51.4T,
   2,281,221 rows reach 75.0%, and normalised at each crosswalk's own size the
   two are 1.06× apart. More money buys the tail.
2. **Derivable from recorded structure.** Closure over relationships already
   filed. **Works — 81.3% where it applies** — and is capped by how much
   structure was recorded, not by the reasoning.
3. **Absent.** Nobody ever recorded the relationship. GLEIF Level 2 is only
   reportable when a consolidating parent exists *and* is itself LEI-registered,
   so **90% of entities** have no relationship on file anywhere. This is not a
   procurement problem and no amount of closure reaches it.

> The residual `f` after both levers is **8.17%**, and it lives almost entirely
> in tier 3. That is the honest frontier of the federated advantage: not a
> reasoning limit, not a budget limit, but **the limit of what the world has
> written down.**

## Scope — half the finding

This settles **group-level** questions. *"Whose group is this filer part of?"*
becomes determinate; *"which country is this filer's legal entity in?"* does not,
when the group spans countries. The alignment itself stays ambiguous throughout
— what changes is that the *question* stops depending on the part that is
ambiguous.

That is the **match the question to the data's shape** thesis stated as a
measurement rather than as advice, and it is the first time this repo has priced
it: matching the question to the shape is worth **1.22×**, free, and composes
with everything else.

## Two bugs, both caught by the answer being too clean

- Roots were keyed on the full `kg:lei:*` form and looked up by the bare LEI.
  Result: **0/598, with a 0/598 control.** A clean zero on both arms is a bug
  signature, not a null.
- Graph membership was tested against the `root` map, which only holds entities
  with an **outgoing** edge — so a top-level parent read as absent from a graph
  it is the root of. That version reported **81.8% from n = 11**, and n = 11 is
  a slice, which has inverted results in this repo ten times. Testing membership
  of sources ∪ targets gives n = 134, and all 109 determined filers fall inside
  it, which reconciles exactly.

## What would refute it

- **81.3% is conditional on a population selected by graph presence**, and
  entities GLEIF records relationships for are larger and more structured. The
  mechanism may be weaker among entities that would be added if coverage grew —
  so the *conditional* rate is an upper bound on what better coverage would buy.
- **`IS_FUND-MANAGED_BY` is not ownership.** Including it moved 104 → 109, so
  the loose notion of "one group" contributes 5 filers; the result is essentially
  all consolidation and does not depend on the looser reading.
- **One source's relationship file.** Whether the 10.4% recording rate is a GLEIF
  property or a general one is unmeasured. Corporate-registry data in single
  jurisdictions is far more complete, and a national test would move the tier-3
  estimate a lot.
- **Group-level questions may be a small share of real demand.** The 1.22× is
  earned only by queries that can be asked about the group. Nothing here measures
  what fraction of a real workload those are, and that is the number that would
  turn this into a product claim.

## Reproduce

```bash
uv run python -u scripts/manufactured_reach.py
```

`runs/manufactured_reach.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `manufactured-reach-by-closure`.

## AMENDMENT, one cycle later: the tiers are not independent

This note treats the three tiers as independent levers and says tier 3 is "not a
procurement problem". `notes/findings/2026-08-18-structural-federation-is-gated-by-identity-federation-and-that-saturates.md`
tested the obvious consequence — that a second source's structure would reach
what GLEIF never recorded — and it is a **null**: wikidata holds **4.3×** more
ownership structure (1,279,720 edges to GLEIF's 296,491) and settles **3** more
filers of 598, against a control that settles ~1.

The reason is that only **3,996** of those edges are expressible about LEIs,
because only **52,860 of 3,348,427** GLEIF entities (**1.58%**) carry a wikidata
twin.

> **Relief in tiers 2 and 3 is gated by tier-1 identity coverage, and tier 1
> saturates.** The residual `f` of 8.17% is therefore *more* robust than this
> note implied: it does not yield to more sources, only to more identity.
