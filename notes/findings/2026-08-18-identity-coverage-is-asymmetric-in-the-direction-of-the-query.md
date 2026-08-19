---
title: What a portfolio holds is 66.3% addressable and who holds it is 23.2% — the same bridge, the same technology, and a 2.9x gap that depends only on which way the question points
date: 2026-08-18
author: lead
status: provisional
tags: [federation, reach, denominators, prediction-refuted, decisive]
---

## The question this settles

`notes/findings/2026-08-18-structural-federation-is-gated-by-identity-federation-and-that-saturates.md`
killed the structural-federation arm on one number: **1.58%** of GLEIF entities
carry a wikidata twin. That is an **unweighted per-entity count**, and this repo
has been caught by that denominator three times — the same CUSIP→LEI join is
22.3% per distinct security, 58.8% per position held and **75.0% per dollar
held**, a 3.4× span.

So the null needed one check before it could stand: **is the missing 98.4% the
tail?** If identity coverage is prominence-weighted, the residual `f` of 8.17% is
economically minor. If it is not, identity coverage is the binding constraint on
the whole reach programme. Nothing measured so far distinguished them, and they
imply opposite next moves.

## The 2×2

`scripts/identity_coverage_denominators.py`, over $51.4T of 13F positions.

| population | by count | **by value** | ratio | vs the flat 1.58% |
|---|---:|---:|---:|---:|
| **held securities** (issuers), weighted by $ held | 12.0% | **66.3%** | 5.5× | **42×** |
| **13F filers**, weighted by AUM | 1.6% | **23.2%** | 14.3× | 15× |
| all GLEIF entities, unweighted | 1.6% | 1.6% | 1.0× | — |

> **The weighting effect is real, large, and it does not rescue the filer side.**
> Identity coverage rises 42× when the question is about what a portfolio holds
> and 15× when it is about who holds it — and the second still lands at 23.2%.

## Prominence tracks entity type, not size

I predicted 12–25% of filers by count and 55–80% by AUM. Both are wrong, the
first badly: **1.6%** and **23.2%**. The error was assuming prominence tracks
*size*. It tracks **kind of entity**. wikidata is an encyclopaedia of operating
companies; there are 8,755 13F filers and most are small registered advisers with
no encyclopaedic existence at any AUM. The 14.3× count-to-value ratio shows the
size effect is present and strong — it simply starts from a base too low to
matter.

## What it decides

**The residual `f` of 8.17% is not a tail phenomenon.** The alignment workload
where `f` lives is over **filers**, and by the denominator that matters filers are
**23.2%** addressable. Correcting the denominator was necessary and it does not
change the null: `scripts/federated_structure.py` ran on the population wikidata
covers worst, and it would have been a null on the honest denominator too.

**And the same measurement is good news for the other half of the programme.** The
vertical slice — country exposure of a 13F portfolio — operates on the **issuer**
side, where **66.3% of held value** is addressable. Those answers rest on much
firmer ground than the filer alignment does, and nothing had established that.

## The general claim

> **Coverage is asymmetric in the *direction* of the query over the same edge.**
> The 13F holdings relation is one edge set. Traversed toward the security it is
> 66.3% addressable by value; traversed toward the holder it is 23.2%. Same
> bridge, same technology, **2.9× apart**, and the only thing that differs is
> which end the question is asked from.

That is the *match the question to the data's shape* thesis in its sharpest form
so far. Previous statements of it were about the **shape** of a question
(group-level versus entity-level, worth 1.22×). This one is about its
**direction**, and it is worth more.

## What would refute it

- **One knowledge base.** wikidata's bias toward operating companies is a
  property of wikidata. A financial-industry registry — Form ADV, which covers
  exactly the registered advisers wikidata misses — would inverate the filer
  column, and it is public. This is the strongest available refuter and it is
  cheap; it is not on disk.
- **AUM as the filer weight is crude.** A filer's importance to a question is not
  its portfolio size — a small activist holder may matter more than a large index
  fund. The 23.2% is the aggregate-exposure reading, not a universal one.
- **The 66.3% is by dollar held, not by dollar at risk.** Concentrated positions
  in uncovered small caps would matter more than their share of the total.
- **CUSIP→LEI→QID is two hops**, so issuer coverage is the product of two
  coverages and understates what a direct security↔wikidata mapping would give.
  The wikidata→ISIN edges (9,936) are such a mapping and were measured separately
  at 68.8% of value — close enough to suggest the two-hop loss is small.

## Reproduce

```bash
uv run python -u scripts/identity_coverage_denominators.py
```

`runs/identity_coverage_denominators.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `identity-coverage-by-denominator`.
