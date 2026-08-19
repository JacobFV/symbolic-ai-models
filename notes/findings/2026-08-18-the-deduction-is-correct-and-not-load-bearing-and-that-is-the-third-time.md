---
title: The ownership closure is 95.7% correct and changes 0.8% of answers — three arms in one session where the symbolic machinery was right and the data did not reach
date: 2026-08-18
author: lead
status: provisional
tags: [datalog, closure, gleif, coverage, negative-result, programme-level]
---

## Why this was run

Everything this session measured is **cost and uncertainty**. Nothing
demonstrated *reasoning* a model could not do, and the `Witness` contract shipped
four cycles ago still has no consumer. One query closes both gaps: a portfolio's
country exposure resolved to **ultimate parent** rather than to the issuer's own
domicile. That needs a transitive closure over GLEIF consolidation — multi-step
deduction, not a lookup — and each answer carries a derivation chain a reader
checks by following named edges.

It also has something this repo almost never gets: **a filed ground truth for a
derived answer.** GLEIF files *both* `IS_DIRECTLY_CONSOLIDATED_BY` (124,460
edges) and `IS_ULTIMATELY_CONSOLIDATED_BY` (130,355), so a closure computed over
the direct edges can be checked against the stated ultimate.

## The deduction is correct

| | |
|---|---:|
| closure agrees with the **filed** ultimate | **112,135 / 117,129 = 95.7%** |
| chain depth | p50 **1**, p90 2, max 9 |

The 117,129 matches the `ultimate_parent` task's own count exactly, and the depth
profile matches the wide shallow forest already in `HANDOVER.md` §3. **A
derivation witness here is one or two edges** — checkable by following named
relationships, and consistent with the witness work's finding that an existential
claim's certificate grows linearly in the answer.

## And it is not load-bearing

Of **7,503** bridged held issuers:

| | | |
|---|---:|---:|
| have an ownership parent at all | **395** | **5.3%** |
| ...of those, ultimate in a **different** country | 61 | **15.4%** |
| **effect on the population** | **61 / 7,503** | **0.8%** |

The mechanism is exactly right — the top shifts are `US→DE` (15), `US→JP` (7),
`US→GB` (6), `BM→CH` (4), `US→IE` (3): the subsidiary-of-a-foreign-parent case
the question exists to catch. **It just almost never applies**, because 94.7% of
held issuers have no ownership parent in GLEIF.

I predicted 15–30%. Within the subset that *has* a parent it is 15.4%, inside
the band. Across the population it is **0.8%** — and **I nearly reported the
15.4%.** That is the fourth form of the slice-versus-population error in one
session; the guard fired because I computed the denominator before writing the
number down.

## The pattern, which is worth more than this result

> **Three arms, three times the symbolic machinery was correct and the data did
> not reach.**
>
> | arm | the machinery | the reach |
> |---|---|---|
> | extraction | works | **62%** of a 0.99 ceiling |
> | the identifier bridge | exact, **0** ambiguity | **22.3%** per security |
> | the ownership closure | **95.7%** agreement with filed truth | **5.3%** of held issuers |

**The programme's bottleneck is not reasoning, and has not been reasoning at any
point this session.** Every arm ended at coverage. That is a more useful thing to
know than any of the individual numbers, and it says where the next year should
go: not to better kernels, and not to cheaper inference, but to **reach**.

## What would refute it

- **One question.** Ownership closure is irrelevant *to country exposure* on this
  corpus. A question about control, sanctions or beneficial ownership would put
  the same closure on the critical path, and 5.3% coverage of *held* issuers is
  not 5.3% coverage of *all* entities — GLEIF's relationship graph covers 296,491
  entities.
- **The 95.7% control is against a filed ultimate**, which is another filing and
  not truth; the repo has already measured 251 filed-vs-filed conflicts in this
  relation.
- **Depth p50 = 1** means this barely exercises transitivity. A deeper graph would
  test the closure properly and this one cannot.

## Reproduce

A ~40-line closure over `relationships_p0.parquet` joined to the bridged
holdings; numbers and method in `notes/autonomy/predictions.jsonl` under
`is-transitive-ownership-load-bearing`.
