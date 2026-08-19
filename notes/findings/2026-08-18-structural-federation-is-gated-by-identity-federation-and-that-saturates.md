---
title: A second source holds 4.3x more ownership structure than the first and delivers 1.01x — 1,279,720 edges collapse to 3,996 expressible ones, because only 1.58% of entities carry the identity that would reach them
date: 2026-08-18
author: lead
status: provisional
tags: [federation, reach, null-result, dead-arm, correction, control-passed]
---

## The hypothesis, and why it was worth testing

`notes/findings/2026-08-18-reach-has-three-tiers-...md` placed the residual
`f` of 8.17% in **tier 3** — relationships nobody recorded — and called it
"not a procurement problem". That note quietly assumed something it never
checked: that a relationship *GLEIF* did not record was not recorded
**anywhere**. GLEIF Level 2 is reportable only when a consolidating parent
exists *and* is itself LEI-registered, which is a rule about GLEIF's registry,
not about the world.

wikidata's backbone carries **1,540,285** ownership edges under no such rule
(`owned-by` 1,162,331, `parent-organization` 196,426, `subsidiary` 116,506,
`owner-of` 65,022). So the question was not *how much more* but **what kind of
limit tier 3 is**: if a second source settles filers the first cannot, tier 3 is
a function of how many sources you federate rather than a wall.

## The result is a null, and the mechanism is the finding

`scripts/federated_structure.py`. Nodes are LEIs and wikidata QIDs; the
`idbridges` `same-as` edges contract a bridged pair into one node; ownership is
normalised to `child → parent` in both sources; GLEIF wins on conflict because it
is filed. Same directed closure as the published GLEIF-only number, so the arms
are comparable.

| arm | edges | determined | control |
|---|---:|---:|---:|
| GLEIF only | 296,491 | **109/598 = 18.2%** | 0.0% |
| wikidata only | 1,279,720 | 6/598 = 1.0% | 0.0% |
| **UNION** | 1,573,678 | **112/598 = 18.7%** | 0.2% |

**Settled by wikidata that GLEIF could not: 3.** Against a union control that
settles ~1 by chance, that is **noise-adjacent** — three filers out of 598 is a
slice, and slices have inverted results in this repo ten times. It is a
hypothesis, not a result. **The second source buys 1.01×.**

### Where 1,279,720 edges went

| | |
|---|---:|
| wikidata ownership edges | **1,279,720** |
| GLEIF ownership edges | 296,491 |
| wikidata edges with **both** ends expressible about an LEI | **3,996** |
| GLEIF entities carrying a wikidata twin | **52,860 / 3,348,427 = 1.58%** |
| ambiguous filers whose candidates **all** carry a QID | 11/598 = 1.8% |

> **The second source holds 4.3× more ownership structure than the first and
> 0.3% of it can be said about the entities in question.** Not because the
> structure is wrong or stale — because the identity that would reach it is
> missing for 98.4% of entities.

The mechanism is the exact opposite of the hypothesis. I expected the structure
to be absent and the reach to be the easy part. The structure is abundant and
**unaddressable**.

*(Conditional determinacy among the 11 fully-covered filers is 54.5%. n = 11.
That is a slice and is recorded only so a later session with better bridge
coverage has a prior to beat — it is not a number to quote.)*

## What this corrects, one cycle later

The three-tier finding treated the tiers as independent levers. They are not:

> **Relief in tiers 2 and 3 is gated by tier-1 identity coverage — and tier 1
> saturates.**

You cannot route around unrecorded structure by adding sources, because reaching
another source's structure requires exactly the identity coverage that was
already measured as saturating (2,383 crosswalk rows reach 68.8% of $51.4T;
2,281,221 reach 75.0%). The two findings compose into a tighter claim than
either made alone, and it is less optimistic than the earlier one:

| policy | `f` | advantage |
|---|---:|---:|
| names alone | 14.66% | 6.8× |
| + GLEIF closure | 11.99% | 8.3× |
| + UNION closure (a second structural source) | 11.92% | **8.4×** |
| + UNION closure + wikidata bridge | **8.17%** | **12.2×** |

**The residual 8.17% is more robust than the three-tier note implied.** It does
not yield to more sources. It yields only to more *identity*, and identity
saturates.

## The dead arm, and what it costs to skip next time

Federating a second structural source is **dead** for this workload. The cost of
finding out was one script and one cycle, and the reusable half is a single
screening number:

> Before federating another source's structure, measure **what fraction of the
> target population carries that source's identity**. Here it was 1.58%, and
> that one number predicts the 1.01× yield without building anything.

## What would refute it

- **One bridge.** `idbridges` is wikidata's own crosswalk and may badly
  understate how many GLEIF entities *could* be matched to a QID. A name-based
  LEI↔wikidata match would raise coverage — at the cost of reintroducing exactly
  the ambiguity the closure was meant to settle, which is a circularity worth
  stating rather than a fix.
- **The workload is 13F filers**, who are asset managers and funds. wikidata's
  corporate coverage is best for large listed operating companies, so a workload
  of *issuers* rather than *filers* would likely show higher QID coverage. That
  is the obvious next probe and it is cheap.
- **Ownership only.** `part-of` (292,624 in the 12M core) and
  `headquarters-location` (38,786) encode weaker group signals that were not
  used. They would raise recall and lower precision, and the permutation control
  would need re-running.
- **The 3 filers could be real.** If a later run with wider bridge coverage keeps
  them and adds more, the "noise-adjacent" reading was too conservative.

## Reproduce

```bash
uv run python -u scripts/federated_structure.py
```

`runs/federated_structure.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `second-source-structure`.
