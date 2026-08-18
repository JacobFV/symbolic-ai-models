---
title: One statistic, two ends — the maximum is closed-form and free, the minimum is NP-hard and needed a solver on 15 of 3,044 hubs
date: 2026-08-18
status: provisional
tags: [fusion, ambiguity, real-data, gleif, asp, kernels, routing, cost]
---

## The assertion this tests

`notes/findings/2026-08-18-a-query-pays-for-the-conflicts-it-reads-and-4992-of-them-cost-one.md`
closed with a hole it named itself: scoped enumeration is exact when a query
reads few conflicts, `additive_bounds` is exact when the answer is a sum of
independent terms, and a query that is **neither** — wide read set, non-additive
answer — *"is where a solver, not a bound, is the answer"*. Asserted, never run.

The test is one statistic over GLEIF's 4,992 unresolved ownership conflicts:

> **concentration(world)** — the largest number of a hub's entities that any
> single party ultimately owns.

It was chosen because its two ends are different problems:

- the **maximum** is closed-form. Conflicts are independent, so for any owner
  the world where every conflict that *can* name it does name it is consistent.
  Linear, and exact rather than a bound.
- the **minimum** is makespan minimisation with restricted assignment — each
  conflict places its weight on one of two owners, minimise the maximum load —
  the classical NP-hard shape.

Predictions were registered before the run in
`notes/decisions/2026-08-18-a-query-pays-for-the-conflicts-it-reads-not-the-ones-that-exist.md`.

## Measured over 3,044 hubs whose concentration depends on the mixture

| the anchor, on the 2,978 hubs enumeration can still reach | |
|---|---|
| closed-form max == enumerated max | **2,978 / 2,978** |
| solver min == enumerated min | **2,978 / 2,978** |
| cheap lower bound == enumerated min | 2,968 / 2,978 |

| over all 3,044 hubs | |
|---|---|
| concentration is **undetermined** (min != max) | 3,025 (**99.4%**) |
| cheap lower bound already exact | **3,029 (99.5%)** |
| hubs where the solver changed the answer | **15**, gap 1..4 (mean 1.47) |
| collapsing lands outside [min, max] | **0**, as it must |
| solver | 1.6s total, **0.52 ms per hub**, 1.29 clingo calls per hub |
| enumeration | 0.04 ms per hub — and **impossible on 66 of them** |
| largest mixture solved exactly | **197 conflicts = 2^197 worlds**, 198 entities |

The widest case is worth stating in full, because it is a real filed group:
`kg:lei:549300RJIC678ZPVWG08` has 198 entities beneath it and 197 unresolved
conflicts among them. **The most concentrated ownership consistent with GLEIF's
filings is 198 of 198; the least is 99 of 198.** Collapsing the mixture reports
198 — the extreme — with no indication that half of it was a choice.

## What this actually says

**The solver rung is real and it is thin.** On 99.5% of hubs the lower bound
anyone would write — heaviest single conflict, heaviest fixed owner, even spread
— is already the exact minimum. On 15 hubs it is not, by up to 4, and there is
no way to know which 15 without asking. That gives the escalation rule directly,
and it is cheap: **verify the cheap bound with one solver call**; it is confirmed
1.29 calls per hub on average, which is why 3,044 exact optima cost 1.6 seconds.

**The asymmetry inside one statistic is the more useful half.** The same question
that is NP-hard downward is closed-form upward. A system that reached for the
solver on both ends would pay twice for one answer, and one that reached for a
bound on both ends would be wrong on the 15. Which rung a query needs is not a
property of the query's *subject* — it is a property of which extreme is being
asked for.

## The encoding cost more than the search

The first version stated the problem the obvious way — `#minimize` over
`#max{ load }` — and **did not finish 3,044 hubs in thirteen minutes**. clingo
was grounding, not searching: a sum per owner and then a max over those sums
instantiates every reachable load value.

Rewritten as the decision problem — "is there a world with concentration <= B",
one integrity constraint per owner — plus a binary search over B in Python, the
same 3,044 exact optima take **1.6 seconds**. Same solver, same answers,
>500x. The optimisation was never the hard part; the encoding was.

Two consequences worth carrying:

- **The ASP kernel cannot express this.** `asp@1` enumerates admissible
  completions and caps at 64 models; it has no notion of an optimum over
  completions, which is exactly what a mixture wants. This ran clingo directly
  and says so. Adding `#minimize` support to the kernel is now a change with a
  measured driver rather than a guess — and the encoding lesson above says the
  API should accept a *decision* predicate, not only an objective.
- A cost row for the solver rung that used the naive encoding would have priced
  the rung at "does not terminate" and killed it. The price of a kernel is a
  price of its encoding.

## Predictions against outcomes

| predicted | measured |
|---|---|
| closed-form max == enumerated max, 100% | **2,978/2,978** |
| solver min == enumerated min, 100% | **2,978/2,978** |
| cheap bound exact on >=70% of hubs | **99.5%** — far tighter than expected |
| undetermined on >=80% of hubs | **99.4%** |
| collapsed always inside [min,max] | **0 outside** |
| solver median <10 ms, total <60 s | **0.52 ms**, **1.6 s** |

Every prediction held, and the one that held *loosely* is the informative one:
predicting "70%" and measuring 99.5% means I expected the solver to earn its
keep an order of magnitude more often than it does on this data.

## What would refute it

- **One graph, one statistic.** Concentration on a wide shallow ownership forest
  is a friendly instance of makespan: most hubs have one or two conflicts. A
  dense graph, or a statistic where the conflicts interact through the objective
  rather than through a shared owner, could invert the 99.5%.
- **The cheap bound's tightness is not a theorem.** It is 99.5% on this data and
  nothing here predicts it elsewhere; the honest rule is "verify it, do not
  trust it", which is what the 1.29 calls per hub buys.
- **The anchor covers 2,978 of 3,044 hubs.** The 66 that enumeration cannot
  reach are checked against nothing but the closed form and the solver agreeing
  with each other — and they are exactly the interesting ones.
- The min/max bracket says nothing about *which* world is true. It is the range
  the filings support, and a user who needs a number still has to choose one or
  go and get evidence — which is the point: the choice is now visible.

## Built

`scripts/gleif_ambiguity_ladder.py` — the four rungs (collapse, scoped
enumeration, closed form, solver) over the same 3,044 hubs, with the anchor
against enumeration wherever enumeration can still run.
