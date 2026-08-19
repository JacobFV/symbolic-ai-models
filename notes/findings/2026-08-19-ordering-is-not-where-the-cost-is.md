---
title: Ordering is not where the cost is — proving agreement is
date: 2026-08-19
status: measured
arm: order-candidates
---

## Correcting the next step I named

The previous finding named *"order candidates by measured `deletion_dependency`"*
as the next optimisation. **That is wrong as stated.** `deletion_dependency` is
measured per **kind**, and every candidate in the link policy is the same kind.
Within a kind, which claim is load-bearing varies case by case, so a kind-level
number cannot order anything.

What is needed is a per-**claim** proxy computable without solving. For links
there is a natural one: does removing this edge disconnect the depot from the
delivery site? An O(V+E) reachability check against a full datalog + ASP + SMT
flow solve.

Ordering is safe by construction: early exit is exact whatever the order, so
ordering changes only *how soon* a disagreement is found, never which cases are
decided. A heuristic here cannot cost soundness, which is what makes it worth
trying at all.

## The proxy never fires

| ordering | mean solves | decided | right |
|---|---:|---:|---:|
| document order | 13.7 | 20/34 | 20 |
| disconnecting first | **13.7** | 20/34 | 20 |

**0% saving** — and not because the ranking is bad. Over 270 candidate deletions:

| | |
|---|---:|
| deletions that disconnect depot→site | **0** (0.0%) |
| deletions that change the answer | 10 (**3.7%**) |
| both | 0 |

The read graph is redundant — it carries extra links from bridge crossings, the
phantom, and the distractor — so **no single link deletion cuts the network**.
The deletions that do matter act through **load limits**: removing a route with
better bridge ratings forces a heavier-limited one. Reachability is the wrong
signal entirely.

The needle is also rarer than the true-world number suggested: 3.7% here against
a measured deletion dependency of 0.243 on the true world, because the read world
has many more links and each matters less.

## The direction is capped anyway, and I should have computed that first

An oracle ordering runs **every** candidate on a decided case — agreement has to
be *proven* — and exactly two on an undecided one. Directly from the per-case
data:

| | mean solves | price of soundness |
|---|---:|---:|
| document order | 13.7 | 13.4× |
| **oracle ceiling** | **10.2** | **10.0×** |

**Any ordering saves at most 25%.** Early exit only helps undecided cases, and
they are the minority — 14 of 34. So ordering is not where the cost is.

**The cost is that proving agreement requires exhausting the candidates.**

## Where the cost actually is

Going below that ceiling needs a different shape: a **certificate that no single
deletion can change the answer**, rather than an enumeration that checks each one.
`symbolic_ai_core/runtime/certificate.py` already carries `Sensitivity` and slack
machinery built for exactly that question — a decision with margin `m` survives a
perturbation bounded by `m`.

That is the promising direction and it is untried: if the flow can report *how
much* slack its answer has against link removal, a decided case could be settled
in one solve instead of sixteen, taking the price of soundness from 13.4× toward
something near 1×.

## What this cost, and what it bought

One wrong proxy and one un-computed bound. The bound was cheap and would have
capped the direction at 25% before any proxy was written — that is the lesson
worth keeping: **compute the ceiling of an optimisation before optimising.**

What it bought is the knowledge that enumeration is the wrong shape, which is
worth more than a 25% saving would have been.
