---
title: A composed query is bounded by its weakest relation, and d belongs to the query
date: 2026-08-19
status: measured
arm: multi-relation-world
---

## The milestone, met

Independently authored prose → a **multi-relation typed world** → a **composed
query whose answer is stated in no sentence**. 168 Wikipedia intros, three
relation families read from the text, Wikidata for ground truth only:

    parent(c, p)  JOIN  country(c, X)   ->   {p}

*which parent groups control companies whose country is X.* No article says it.

## The relations are not equally readable, and that is the binding constraint

| relation | gold known | answered | **correct** | precision |
|---|---:|---:|---:|---:|
| **country** | 0.988 | 0.867 | **0.819** | **0.944** |
| parent | 1.000 | 0.589 | **0.327** | 0.556 |
| headquarters | 0.964 | 0.401 | **0.241** | 0.600 |

**A 3.4× spread.** A lead reliably says *"a French multinational"* — nationality is
almost always stated and almost never wrong (precision 0.944). Ownership is
optional and hedged; a head office is usually implicit in the city name and my
reader only catches the explicit *"headquartered in"* phrasing.

## Composition is worse than the product

| country | \|gold\| | \|read\| | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|
| united states | 52 | 26 | 0.423 | 0.212 | 0.282 |
| germany | 16 | 8 | 0.500 | 0.250 | 0.333 |
| united kingdom | 15 | 8 | 0.500 | 0.267 | 0.348 |
| **macro (29 countries)** | | | **0.207** | **0.119** | **0.138** |

Per company the join needs both sides: 0.327 × 0.819 ≈ **0.268**. The query scores
**0.138**, half that. **A set-valued answer accumulates rather than averages** — a
missed parent removes a group from the answer, a wrong one adds a spurious group,
and across 52 companies both happen many times. I predicted 0.25–0.35 by taking
the product; the product is an upper bound on a per-item join and not on a
set-valued one.

> **A composed query is bounded by its weakest relation, and set-valued
> composition degrades faster than the product of its parts.**

## And `d` is a property of the query, not of the domain

The influence law says critical mass ≈ `d · |Ŵ △ W|`, and weighting separates only
when `d < 1`. Measured on this query — the share of read claims whose removal
changes the answer **set**:

| relation | claims | **d** |
|---|---:|---:|
| `parent` | 67 | **0.866** |
| `country` | 101 | **0.574** |

Against flood's **0.236**. So:

| query shape | d | what weighting buys |
|---|---:|---|
| selection over a redundant graph (flood) | 0.236 | AUC 0.506 → **0.946** |
| union / enumeration (this query) | **0.57–0.87** | little |
| sum against a threshold (solvency revenue) | ≈ 1 | nothing |

**A selection query hides most single-claim errors; an enumeration query shows
nearly all of them.** That extends the law with its controlling variable, and it
has a blunt practical corollary: **for enumeration queries, plain extraction
accuracy *is* the right objective.** Task-weighted reconstruction is not
universally the better target — it is better exactly where the query is
insensitive, which is what `d` measures.

## What would refute this

- One join, one direction. A query with a selective filter (*groups controlling
  companies founded after 2010 in X*) should push `d` back down, and that is the
  cheap test of the claim that `d` tracks the query rather than the corpus.
- The headquarters reader is weak enough (0.401 answered) that it contributes
  little; the composed query uses only two of the three relations.
- Ground truth is Wikidata's, which is incomplete for `P749` in ways the gold set
  inherits — several `|gold|` counts are certainly under-counts.
