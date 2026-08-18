---
title: A query pays for the conflicts it reads — 4,992 unresolved conflicts, 117,129 answers in 0.3s, and the cheap method is wrong on every pair it touches
date: 2026-08-18
status: provisional
tags: [fusion, ambiguity, real-data, gleif, sec, cost, architecture]
---

## The gap this closes

`fuse` retains a disagreement, the mixture survives serialisation, and
`possible_answers` reads one. But it prices a query at the **world's** product:
251 retained GLEIF conflicts are 2^251 consistent worlds, so it refuses
*everything*, including "who ultimately owns this one company" — whose answer
depends on exactly one of them. Its own refuter said so: *"a query touching 30
interacting conflicts is refused rather than answered."*

Retention was therefore a capability with a bound that made it unusable at the
scale the real data has. Pre-registration, written before any number landed:
`notes/decisions/2026-08-18-a-query-pays-for-the-conflicts-it-reads-not-the-ones-that-exist.md`.

## Three mechanisms, and which case each is for

- **Scoped enumeration** (`possible_answers_scoped`). Hand the computation an
  assignment that *records* what it looks at, collect the read set, enumerate
  only that, repeat until a pass reads nothing new. No annotation, no static
  analysis of the query — a computation declares its dependencies by having
  them. Cost `2^(conflicts read)`, exact.
- **Additive bounds** (`additive_bounds`). For the aggregate that genuinely
  reads everything, the extreme worlds are found term by term, and each bound
  is *attained* by the assignment returned with it. Linear, exact, and refuses
  nothing.
- **Set propagation** — carry a set of possible values per entity and take
  unions. Built here as the **control that must fail**, because it cannot see
  that two entities under one conflict must move together.

## Measured on two real mixtures

| | **A: 251 conflicts** filed-vs-filed, both `measured` | **B: 4,992 conflicts** closure-vs-filed |
|---|---|---|
| what it is | GLEIF contradicting itself; `prefer_measured` refuses to settle | the mixture a world **without** derivation-aware fusion holds |
| worlds | 2^251 | 2^4992 |
| `possible_answers` | refused | refused |
| point queries answered | **117,129 in 0.3s** (2.5 us each) | **117,129 in 0.3s** (2.7 us each) |
| conflicts read per query | p50 **0**, max **1**, sum 253 | p50 **0**, p99 1, max **1**, sum 5,006 |
| answers that are undetermined | 253 (0.216%) | 5,006 (**4.274%**) |
| anchor: scoped == full enumeration | **410/410** entities | **410/410** entities |

The anchor is the check that says scoping is exact and not merely cheap: full
enumeration cannot run on 251 conflicts, so it runs on the first 8 of them as a
mixture in its own right (256 worlds) and the two are required to return the
**same answer set** for every entity — not a subset, not a superset.

### What retention costs, now that it is affordable

| | A | B |
|---|---|---|
| collapse the mixture, answer once | 0.11s | 0.09s |
| answer under the mixture, scoped | 0.30s | 0.30s |
| **retention** | **2.8x** | **3.4x** |
| USD per answered query (0.02/core-hour) | **1.41e-11** vs 5.10e-12 | **1.48e-11** vs 4.30e-12 |

Three times the cost of collapsing, and in exchange every one of the 5,006
undetermined answers is *flagged as undetermined with its alternatives*, rather
than being silently whichever source loaded second. This is the same shape as
the witness result — inspectability is not free and it is not expensive.

### Where scoping stops, and bounds take over

The point query is cheap for a reason that is about the **query**, not the
graph: the ultimate owner of an entity is its first conflicted ancestor's, so
the walk stops there and reads one conflict. A *portfolio* query — how many
entities beneath this hub end up owned by the party its own chain names — reads
every conflict underneath it:

| | A | B |
|---|---|---|
| hubs whose portfolio query reads >= 1 conflict | 301 / 51,456 | 3,044 / 51,456 |
| conflicts read, p99 / max | 0 / **32** | 3 / **197** |
| worlds at the widest hub | 4.29e9 — **refused** | **2.0e59** — refused |
| additive bounds at that hub | [3, 35] over 35 entities | [1, 198] over 198 entities |
| **bounds == enumerated extremes**, where enumeration runs | **295/295** hubs | **2,978/2,978** hubs |

A hub whose subsidiary count is *anywhere between 1 and 198* is not a failure of
the method. It is the honest state of GLEIF's filings for that group, and the
alternative on offer was a single confident number that is right in one world
out of 2.0e59.

### The control failed exactly as required, on a population two orders of magnitude smaller than predicted

| | A | B |
|---|---|---|
| pairs of entities whose answers turn on the **same** conflict | **2** | **17** |
| scoped enumeration: one answer ("they agree in every world") | 2/2 | 17/17 |
| **set propagation disagrees with the truth** | **2/2 (100%)** | **17/17 (100%)** |

Set propagation says the two entities *might* differ, because the product of two
independently-derived value sets contains combinations no single world produces.
It is wrong every time it is asked. It is also asked 19 times in total across
both mixtures — this graph barely has correlated queries, for the same reason
its amplification is 1.0x: conflicted entities have almost no descendants.

## The cross-source case, which is the one the federation layer is for

`notes/findings/2026-08-18-retention-was-real-in-memory-and-lost-at-the-artifact-boundary.md`
named the limit: the 251 are one source contradicting itself, and *"two
different sources disagreeing about one property is the case the federation
layer is really for, and the corpus still offers none."* It does offer one, and
it is not a property conflict — it is an **identity** one. `kg:sec:cik:*` and
`kg:lei:*` share no identifier, so aligning SEC filers to GLEIF entities runs
through canonical names and leaves 598 of 4,078 matched filers (14.66%) with
more than one candidate, up to 35.

**Both are the same computational object** — a subject with competing values —
and neither mechanism needed a line of code to tell them apart.

| "how many aligned filers are US-domiciled?" | |
|---|---|
| unambiguous alignments | 3,480 (2,586 US) |
| ambiguous alignments | **598**, i.e. 2^598 worlds and more |
| `possible_answers` | refused, naming nothing |
| `possible_answers_scoped` | refused, **naming all 598** — the query really does read them |
| `additive_bounds` | **[2824, 3062]**, width 238, in **2.4 ms** |
| ambiguous alignments that move the answer at all | 238 of 598 |
| anchor at 8 / 12 conflicts (768 / 41,472 worlds) | enumerated [2,6] / [3,10] == bounds, **exact** |
| per-filer country query, scoped | 307 undetermined of 4,078 (7.5%) |

This is the case that shows scoping is not a universal cure and was never
claimed to be: the aggregate's dependency **is** all 598 conflicts, the refusal
is correct, and the bound is what makes it answerable anyway.

## Predictions against outcomes

| predicted | measured |
|---|---|
| read set p50 1, max 2, <10 entities reading >=2 | p50 **0**, max **1**, **zero** reading two |
| pairs sharing a conflict: 100–400 | **2** (A), **17** (B) |
| set propagation wrong on >=90% of them | **100%** |
| scoped == full enumeration on 100% | **410/410**, both mixtures |
| alignment bound width within +-20% of 0.513 x 598 = 307 | **238** — 22.5% low, outside the band |

Two misses worth keeping. The read-set prediction was wrong because I assumed a
query reads every conflict on its chain; it reads the *first*, and that is a
fact about the query's semantics that I only saw while writing it. And the width
prediction confused "candidates disagree on country" (307) with "candidates
disagree on **US**" (238) — a filer with candidates in GB and DE crosses
jurisdictions and cannot move a US count.

## What would refute this

- **Neither mechanism covers a query whose answer depends on two conflicts
  jointly and non-additively** — a ratio, a distinct-count, "is A's owner also
  B's". Scoped enumeration answers it exactly when the joint read set is small
  (it did, on 19 pairs) and refuses when it is not, and `additive_bounds`
  cannot express it at all. That case is not in this data and it is where a
  solver, not a bound, is the answer.
- **The read set is discovered by running the computation.** A computation that
  reaches around its assignment — a cached value, a global, a second copy of
  the graph — reports a read set that is a lie, and nothing enforces purity.
  The docstring says so; the type system does not.
- **The bounds are exact because each term reads one conflict.** The interface
  enforces it (a contribution sees one subject and one value) but a caller can
  close over anything, and a term that secretly reads two subjects makes the
  term-by-term extreme unattainable while still returning a confident interval.
- **19 correlated pairs is a thin refutation of set propagation.** The method is
  wrong on all of them, and the population where it would be wrong *often* is a
  dense graph — the route network, amplification 44x — which was not tested.
- Both GLEIF mixtures are ownership chains, where the answer is one entity. A
  numeric property with three sources would exercise the same machinery
  differently and there is still no such case in the corpus.

## Built

- `possible_answers_scoped`, `_Recording`, `additive_bounds`, `Bounds`, and
  `AmbiguityExplosion.read` — a refusal that **names the conflicts the query
  depends on** rather than making a caller parse the message for them.
- `scripts/gleif_scoped_ambiguity.py` — both mixtures, three arms each. It
  imports the 251's definition from `gleif_fund_exposure` rather than re-typing
  it, because this repo has already confused two conflict sets once.
- `scripts/alignment_bounds.py` — the cross-source aggregate.
- 17 new tests in `tests/test_ambiguity.py` (38 there, 76 with `test_fusion.py`).

One bug found and fixed on the way, and it is a repeat of a known shape:
`UltimateParentTask.ids` is a property that sorts 117k entities on every access,
and reading it inside a comprehension's condition made a loop 100,000x slower —
the same "a cheap-looking attribute is a computation" trap as
`notes/lessons/2026-08-17-a-default-computed-in-init-captures-the-base-classs-values.md`.
