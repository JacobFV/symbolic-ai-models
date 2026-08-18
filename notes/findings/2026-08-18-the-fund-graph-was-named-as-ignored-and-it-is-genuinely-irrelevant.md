---
title: The fund graph was named as an ignored gap, and it turns out to be genuinely irrelevant — the 251 real conflicts and the fund universe are disjoint populations
date: 2026-08-18
status: provisional
tags: [fusion, ambiguity, topology, real-data, gleif]
---

## The gap this closes

Yesterday's exposure correction
(`notes/findings/2026-08-18-ambiguity-does-not-propagate-in-a-forest-and-that-is-why-retention-is-affordable.md`)
found four orders of magnitude of exposure *within* `IS_FUND-MANAGED_BY`
(146,948 edges) and `IS_SUBFUND_OF` (71,833 edges) — a fund manager with 1,258
funds, a fund family with 3,847 subfunds — but named an explicit hole in its own
method: **the 251 real conflicts were only ever walked through the ownership
relation.** Whether an ownership conflict also sits on one of those fund hubs,
and so contaminates further than the ownership-only count says, was unmeasured.

## Prediction, and how it landed

The 251 are entities whose filed *ultimate* consolidation parent contradicts a
mid-chain intermediate on their own filed *direct* consolidation chain — both
facts about corporate ownership. A fund manager or a subfund is a different part
of GLEIF's population (funds and the firms that run them). Predicted: low
overlap, most of the 251 absent from both fund relations, total added exposure
in the tens rather than the thousands.

**It came in more extreme than predicted, not less: zero, not low.**

| | value |
|---|---|
| conflicts checked | 251 |
| conflicts that are a hub in `IS_FUND-MANAGED_BY` or `IS_SUBFUND_OF` | **0** |
| conflicts appearing in **either** fund relation in **any** role, leaf or hub | **4** |
| conflicts touching neither fund relation at all | **247 (98.4%)** |
| exposure via `IS_FUND-MANAGED_BY`, summed over the 251 | 251 (every node exposure = 1) |
| exposure via `IS_SUBFUND_OF`, summed over the 251 | 251 (every node exposure = 1) |
| exposure via ownership, summed over the same 251 (baseline, reproduced) | 304 |

Reproducing the ownership baseline first (sum 304, mean 1.211, median 1, max 18)
matched the prior finding's own numbers exactly, which is the check that the
251 set and the exposure walk are the same construction, not a coincidentally
similar one.

## Why zero rather than merely low

Corporate consolidation ownership and fund administration are filed as separate
GLEIF relationship types precisely because they are different relationships
between different kinds of entities — an operating company's parent versus a
fund's manager. The 4 entities that do appear in a fund relation appear as
**leaves** (a fund or subfund itself), never as a hub with anything reporting to
them, so even those four contribute no downstream exposure. The named gap is
closed with a null: **the fund graph was not wrongly ignored, it is genuinely
irrelevant to this conflict set**, and the reason is structural (disjoint entity
roles) rather than a property of where these 251 particular conflicts happened
to fall.

## What this does and does not license

- It does **not** mean `IS_FUND-MANAGED_BY`/`IS_SUBFUND_OF` exposure is
  irrelevant in general — yesterday's percentile table over the *whole*
  population still stands, hubs with exposure in the thousands are real, and a
  conflict landing directly on a fund manager (none of these 251 do) would still
  cost what the table says.
- It does not generalise past GLEIF's specific relation semantics. A source
  where ownership and fund administration share entities more often — or a
  future GLEIF snapshot with more cross-typed conflicts — could find nonzero
  overlap; this is one measurement of the actual filed data, not a proof about
  the schema.

## Built

`scripts/gleif_fund_exposure.py` — reproduces the 251 exactly (mid-chain
intermediate contradicting the filed ultimate, distinct from the registry
finding's looser 4,992 "closure disagrees with filed ultimate" set, which this
script also computes and reports as a distinct number so the two are not
conflated again), then measures ownership, fund-management and subfund exposure
for that same set, plus role-agnostic relation membership.

## What would refute it

- A future GLEIF snapshot, or a different conflict-defining rule, that produces
  a conflict set with nonzero overlap with the fund hubs — the finding is about
  *this* 251, not a claim that ownership and fund conflicts can never coincide.
- Restricting to `IS_FUND-MANAGED_BY`/`IS_SUBFUND_OF` misses a third
  cross-population relation this script did not check —
  `IS_INTERNATIONAL_BRANCH_OF` (1,920 edges) and `IS_FEEDER_TO` (1,359 edges)
  are smaller and unexamined here.
