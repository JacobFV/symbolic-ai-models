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
nearly all of them.**

### The controlled version, because the cross-corpus comparison proves nothing

Flood at 0.236 against this corpus at 0.57–0.87 could be two worlds rather than
two query shapes. So: **three queries over one world, one reader, one set of
claims** — only the aggregation changes.

| shape | `parent` d | `country` d |
|---|---:|---:|
| **union** — every group in X | **0.866** | **0.574** |
| **argmax** — the largest group in X | 0.493 | 0.327 |
| **existence** — does group G appear in X | **0.015** | **0.010** |

**`d` spans 0.010 to 0.866 — a factor of sixty — on identical claims.** Nothing
about the corpus, the reader or the world moved. `d` is the query's.

(Predicted union 0.87 → argmax 0.15–0.35 → existence < 0.10. The monotonicity and
the endpoints hold; argmax came in higher than predicted at 0.49.)

> **The value of task-weighted reading is ≈ 1/d, and `d` is set by the query's
> aggregation shape — knowable before a word is read.** At `d ≈ 0.01` an existence
> query makes 99% of reading effort irrelevant to its answer; at `d ≈ 0.7` a union
> query makes plain extraction accuracy nearly the right objective already.

That is the blunt practical corollary: **for enumeration queries, plain extraction
accuracy *is* the right objective.** Task-weighted reconstruction is not
universally the better target — it is better exactly where the query is
insensitive, which is what `d` measures.

## Amendment: enumeration was the wrong variable, redundancy is the right one

Trying to turn `d` into a **value-of-information** rule — `VOI(r) ≈ d_r·(1−acc_r)`,
the rational decision rule the frame asks for before any learned router — the
discriminating design **failed**, and the failure is informative.

Two queries were meant to swap the relations' roles: *groups in country X* (parent
enumerated) against *countries of group G* (country enumerated). **`d` did not
swap.** Parent's `d` exceeds country's in both, so VOI and the naive *improve the
weakest relation* agree and nothing is discriminated.

The reason is that **`d` is governed by value redundancy in the answer set**, not
by whether a relation is enumerated or filtering. Country values *repeat* — many
companies share *united states* — so dropping one country claim rarely changes the
set. Parent values are near-unique, so dropping one usually does. That also
explains flood's low `d` without appeal to aggregation at all: its network has
alternative routes, so most links are redundant.

So the controlling variable is **redundancy of the relation's values within the
answer**, and aggregation shape is one way to get it rather than the thing itself.
The union/argmax/existence spread above is still a factor of sixty on identical
claims — but it is the *selectivity* changing the redundancy, not the enumeration
per se.

One more number worth keeping: fixing half of each relation's errors gave a gain
ratio of **16.0** against a VOI ratio of **5.45**. First-order `d·(1−acc)` is
directionally right and **quantitatively weak** — it under-predicts how
concentrated the value is.

*(The `d` figures in this amendment are computed over all rows per probe rather
than only matching ones, so 0.099 is not comparable with the 0.866 above — same
quantity, diluted denominator.)*

## The formula, and it is a reliability quantity

"Redundancy" was still a story. Making it precise: for a union query the answer is
a set of **values**, each supported by some number of claims, so dropping a claim
changes the answer only if it was that value's **sole support** — a min-cut of
size one.

| relation | answer values | **P(support = 1)** | mean support | **measured d** |
|---|---:|---:|---:|---:|
| `parent` | 64 | **0.922** | 1.09 | **0.866** |
| `country` | 6 | **0.000** | 17.33 | **0.574** |

**It works for `parent` and fails completely for `country`** — and the failure is
the derivation. In this query the answer values *are* parent groups; a country
claim never appears in the answer, it **gates** which companies reach it. So a
country claim matters when the company it admits was the sole support of its
group, *and* that company's parent was read at all:

    d(country) ≈ P(sole support) × P(partner relation present)
               = 0.922 × 0.589  =  0.543      (measured 0.574)

Two terms, both measured elsewhere, agreeing to three points. And for `parent`,
whose claim is itself the answer value, the second term is 1 by construction:
0.922 against 0.866.

> **`d(r) = P(a claim of r is a bridge to some answer element) × Π P(the rest of
> its derivation path survives).`** It is a **reliability** quantity — the
> probability a claim lies in a min-cut of size one, times the survival of the
> path it sits on — not a property of aggregation shape.

That is the network-reliability abstraction reached from data rather than borrowed.

### Run on flood, it is refuted in exactly the predicted direction

The formula predicted flood's link `d` from a purely structural predicate:
`load_bearing_cheap` computes, in one DFS per edge with no solve and no reader,
whether removing a link disconnects depot from site in some vehicle's admissible
subgraph. Three routes to the same quantity:

| route | population | value |
|---|---|---:|
| **structural bridges**, true worlds, no reader | **all real links** | **0.245** |
| influence of the reader's actual errors | the links the reader got wrong | **0.169** |
| `audit.deletion_dependency`, offline | true-world link deletions | **0.138** |

Predicted band 0.13–0.20; measured **0.245**, outside it and **higher** — which is
the direction the refutation condition named. **A phantom link is more likely to
be redundant than a real one**, because the distractor connects two real regions
in a network that already has routes, so the reader's errors are *biased toward
inert claims* relative to the world's claims.

> **`d` is not a property of the world alone. Bridgehood is structural; *which*
> claims are wrong is not.** The right object is
> `d = E_{c ~ error distribution}[c is a bridge]` — the structural predicate
> averaged over **where the reader errs**, not over the world.

So the structural share is computable offline and is an **upper bound**, exact
only when the reader's errors are unbiased with respect to redundancy. Here it
over-states the influence of real errors by **1.4×**.

That is the third narrowing of this claim, each forced by a measurement:
aggregation shape → value redundancy → bridges → **bridges over the error
distribution**.

## What would refute this

- The three shapes share a corpus and a reader, which is what makes them a
  control — but they also share a *relation pair*. A join over relations with
  different redundancy might move `d` for reasons that are not the aggregation.
- `existence` is measured against one probe group per country, the largest in the
  gold set. A rare group would raise its `d`, since fewer claims support it.
- The headquarters reader is weak enough (0.401 answered) that it contributes
  little; the composed query uses only two of the three relations.
- Ground truth is Wikidata's, which is incomplete for `P749` in ways the gold set
  inherits — several `|gold|` counts are certainly under-counts.
