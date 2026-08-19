---
title: A wrong fact is amortised too — the claims consulted most are the ones read worst
date: 2026-08-19
status: measured
arm: blast-radius
---

The persistence argument is that ingestion amortises: extract once, answer
forever, per-query cost goes to nothing. Measured and defended — $1.16e-04 once
against $6.32e-03 per iterative-RAG query, cheaper from the first query.

**The same arithmetic applies to the errors, and neither of those notes said so.**
A context-window reader gets a fresh chance at every query; a persistent world
commits. A wrong claim about a hub entity is not one wrong answer, it is every
answer that passes through it. This prices that liability.
`runs/error_blast_radius.json`.

## 1. The mechanism is real: hub articles are read worse

In-degree = how many corpus articles name this entity as their parent. It is
computed from gold, so it is available for all 1,661 articles rather than only
the 191 chains.

| in-degree | articles | **accuracy** | mean intro length |
|---|---|---|---|
| 0 | 1,526 | **0.197** | 816 chars |
| 1 | 96 | 0.115 | 1,074 |
| 2 | 25 | 0.200 | 1,206 |
| 3+ | 14 | 0.071 | 1,504 |
| **any (≥1)** | **135** | **0.126** | — |

**Hubs read 36% worse relatively** — 0.126 against 0.197 — and wrong articles
carry **1.6x the in-degree** of correct ones (0.124 against 0.076).

> **Power check, added after the fact.** That headline rests on **17 successes in
> 135 hub articles**. Wilson intervals are [0.080, 0.192] against [0.178, 0.218],
> which nearly touch, and a two-proportion test gives **p = 0.044** — real, and
> fragile. It would *not* survive a correction for the four-bucket table
> immediately above it, and the 3+ row (1 success in 14) carries nothing at all.
> The mean-in-degree comparison (0.124 against 0.076 over all 1,661 articles) is
> the better-powered form of the same claim and is the one to quote. Treat the
> 36% as a direction with one asterisk, not as a measured size. The mechanism
is visible in the last column: an entity that many companies belong to is a big
company, and a big company's intro is nearly **twice as long** and correspondingly
harder.

The same ordering appears in fan-out measured directly on the served queries:
0.194 at fan-out 1, 0.179 at 2, 0.143 at 3, 0.000 at 4+ — with n falling to 21
and 2, which is why in-degree is the number to quote.

**So the claims a persistent world consults most are the ones it most likely got
wrong.** That is the liability, and it is the opposite of the reassuring
possibility — that hubs, being mentioned everywhere, would be read better.

## 2. And in this corpus it costs almost nothing

| query mix | consultations | unweighted | **consultation-weighted** |
|---|---|---|---|
| as served (1,661 one-hop + 191 two-hop) | 1,928 | 0.1908 | 0.1878 |
| full ancestor chains | 1,862 | 0.1908 | **0.1842** |

**3.5% relative degradation** at the deeper mix, 1.6% at the actual one.
Fan-out is **mean 1.16, median 1, max 5**, and the top 1% of claims carry 2.6% of
consultations.

Predicted a heavy tail with a maximum above ten. **Refuted**, and the reason is
structural rather than reassuring: this corpus is **shallow**. Only 191 of 1,661
articles have a parent that also has an article, so almost every chain has length
one and no fan-out can concentrate. The liability is a property of the **query
mix and the graph depth**, not of persistence.

## 3. What this actually licenses

- **The amortisation argument stands as measured**, and now with its liability
  quantified rather than unmentioned: at this depth, consulting a persistent
  world costs 3.5% relative accuracy against reading each document fresh.
- **It should not be extrapolated to deep hierarchies.** Both ingredients of a
  large effect are present — fan-out concentrates on hubs, and hubs read worst —
  so a corpus with real depth, or an agent that asks composed questions, widens
  this gap. The right form of the claim is conditional: *persistence is cheap and
  nearly free of error liability when the graph is shallow, and its liability
  grows with exactly the structure that makes persistence valuable.*
- **The obvious mitigation is measurable and unbuilt**: spend more reading effort
  on high-in-degree entities, which is a query-volume-weighted version of the
  sensitivity idea that failed at claim level. In-degree is known before any
  reading, from the link structure, so it is available as a *budget* signal in a
  way `sᵢ` never was.

## What would have refuted it

Hubs reading *better* — plausible, since they are named in many articles and a
reader could learn them from repetition. They read worse, by 36% relative, and
the intro-length column says why.
