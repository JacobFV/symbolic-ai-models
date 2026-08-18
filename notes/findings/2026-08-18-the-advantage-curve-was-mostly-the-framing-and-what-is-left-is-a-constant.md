---
title: 99,738x of the published advantage was the framing — priced by what the query actually depends on, four query classes collapse from five orders of magnitude apart to 1.2x
date: 2026-08-18
status: provisional
tags: [cost, advantage-curve, ambiguity, real-data, gleif, correction, north-star]
---

## What this corrects, and what it does not

`notes/findings/2026-08-18-ownership-closure-and-the-advantage-curve-spans-seven-orders-of-magnitude.md`
put three points on a curve — 6,750x on country-from-coordinate, 1.5e6 on
shortest path, **1.85e11 on ultimate parent** — and named the variable that
orders them: *how much of the answer lives in structure the model must be handed
rather than in knowledge it already has.* The largest of those is computed by
handing a language model **the whole ownership graph** for a question about one
company.

**The arithmetic in that finding is right. The framing is doing almost all of
the work,** and until this week there was no way to say so, because "how much of
the corpus does this query actually depend on" was not a measurable quantity.
The read set makes it one.

## Measured on the same corpus, the same substrate

Necessary context = exactly the filings a correct answerer must see: the
entity's direct-ownership chain up to the first conflicted ancestor, plus the
filed ultimate of every entity on it — which is what makes a conflict visible
and "this answer is determined" checkable rather than asserted.

| | naive context | **necessary context** |
|---|---:|---:|
| point query: who ultimately owns X | 4,078,514 tok | **41 tok** (p50 **32**, p99 128, max 288) |
| determinacy + the alternatives | 4,078,514 | 41 |
| portfolio bracket for one hub | 4,078,514 | 311 (max 75,104) |
| census: which of 117,129 answers are open | 4,078,514 | 4,078,514 |

| query class | advantage, naive framing | advantage, oracle retrieval |
|---|---:|---:|
| point: who ultimately owns X | **5.01e12** | **5.03e7** |
| determined? + the alternatives | 4.95e12 | 4.97e7 |
| portfolio bracket for one hub | 6.69e11 | 5.10e7 |
| census: which answers are open | 4.10e7 | 4.10e7 |

**Two things fall out, and the second is the finding.**

1. **99,738x of the point query's claimed advantage was the framing.** Give the
   opponent a perfect retriever and 5.01e12 becomes 5.03e7. It does not vanish
   — five orders of magnitude survive — but five orders of magnitude were the
   comparison, not the capability.
2. **Once both sides are charged for the dependency, the curve is flat.** Four
   query classes spanning **five orders of magnitude** of naive advantage land
   within **1.2x of each other** at ~**5e7**. The advantage stops being a
   property of the task. What is left is an architecture constant: the ratio
   between *putting one filing in a prompt* and *processing one filing in a
   kernel*, and every task-level number is that constant times how much
   irrelevant context the opponent was handed.

## And the number is a property of the workload, not only the query

Cost is charged to the **system** here, so the parquet ingest and the mixture
build are in the ledger:

| how it is charged | $ per point query | advantage |
|---|---:|---:|
| naive framing, marginal | 1.22e-11 | 5.01e12 |
| oracle retrieval, marginal | 1.22e-11 | **5.03e7** |
| oracle retrieval, **amortised** over 117,129 queries | 3.15e-11 | **1.95e7** |
| oracle retrieval, **a workload of one query** | 2.26e-06 | **271x** |

Setup is 0.41 s of ingest for 476,875 filed rows. Amortised across the corpus it
is 2.6x the marginal query cost; paid by a single query it is everything, and
the advantage falls from 5e7 to **271x**. Still a factor of hundreds, still an
exact answer that carries its own alternatives — but three orders of magnitude
of the headline is "we were going to read the whole file anyway".

## Predictions against outcomes

Registered in
`notes/decisions/2026-08-18-drop-the-dense-graph-arm-and-measure-the-dependency-instead.md`
before the run.

| predicted | measured |
|---|---|
| necessary context under 500 tokens | **41 mean, 32 median** — held, and smaller than expected |
| advantage falls 3–4 orders of magnitude | **5 orders** (99,738x) — under-called |
| aggregate queries cannot shrink under retrieval | **wrong for hub brackets** — they shrank 13,126x; only the *global* census is irreducible |
| spread within one corpus stays >= 4 orders, driven by dependency size | **wrong, and it is the finding** — the spread collapses to **1.2x**, because both sides scale with the dependency and it divides out |

The third and fourth misses share one cause: I conflated *aggregate* with
*global*. A hub's portfolio depends on its own subtree, which is a few hundred
tokens; only a question about the whole world depends on the whole world.

## What would refute it

- **The opponent is charged nothing for the retrieval that makes it cheap.**
  Knowing which 32 tokens matter is the read set — the output of the system
  under test. This row is therefore the *hardest honest* comparison available
  and an unfair one in the substrate's favour in exactly one respect: an
  independent retriever would cost something, and if it is itself a graph walk
  then the honest statement is that the substrate is the retriever and the
  comparison is not adversarial at all.
- **A ratio of two token counts under one convention** (chars/4). The convention
  cancels in every advantage-shift number here; it does not cancel in the
  absolute dollar figures, which is why the convention is stated. My corpus
  count is 4.08M against the published 1.99M for the same bytes — a 2x
  disagreement in *counting*, not in bytes, and a reason to distrust absolute
  token figures across findings unless the rule is quoted.
- **Frontier-tier pricing at $15/Mtok, input only, zero output, perfect
  accuracy.** That is a lower bound on the opponent's cost and therefore a lower
  bound on the ratio, which is why these rows carry no equal-accuracy assumption
  and are not stamped NOT QUOTABLE — unlike every advantage row before them.
- One corpus, one substrate, four query classes. The ~5e7 constant is a
  measurement, not a law, and the first thing that would test it is a corpus
  where a single fact costs more tokens to state than an LEI pair does.

## What it changes about the programme

The roadmap's open item was *"the advantage is a variable, so map it"*. It is a
variable — but not of the task. Priced properly it factors into three things,
and only the first is about the substrate:

1. a constant ~5e7, the cost of a fact in a kernel against a fact in a prompt;
2. **how much irrelevant context the alternative is handed** — up to 1e5 here,
   and entirely a property of how the comparison is set up;
3. **how many queries the ingest is amortised over** — up to 2e5 here, between a
   workload of one and a workload of the corpus.

A headline advantage figure that does not say which of the three it is
reporting is not a measurement of anything.

## Built

`scripts/ambiguity_advantage.py`.
