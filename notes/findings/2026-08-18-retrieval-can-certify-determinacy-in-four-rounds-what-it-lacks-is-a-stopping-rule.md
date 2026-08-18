---
title: Retrieval can certify determinacy in four rounds — I predicted it could not. What it lacks is a stopping rule, and it over-fetches 46x
date: 2026-08-18
status: provisional
tags: [cost, retrieval, advantage-curve, ambiguity, real-data, gleif, correction]
---

## The claim under test, which was mine and was too strong

`notes/findings/2026-08-18-the-advantage-curve-was-mostly-the-framing-and-what-is-left-is-a-constant.md`
priced an opponent handed **exactly** the filings a query depends on and got a
flat ~5e7. I then argued the strategic consequence: that opponent does not
exist, because knowing which lines matter *is* the read set, so the substrate's
real product is certifying what an answer depends on — something a retriever
*"can only guess"*.

That was a claim about a mechanism, so it was testable without an API, and it is
**partly wrong**.

Simulated opponent: an **ideal** lexical retriever — perfect recall on any
identifier it already holds, no embedding noise, no top-k cutoff. Every filed
line mentioning a known identifier comes back. The only thing it cannot do is
know an identifier it has not yet seen.

## What it found

| | |
|---|---|
| **the lookup** — "who does X file as its ultimate parent" | answered verbatim in **round 1, 117,129/117,129**. Retrieval wins this outright, and it should: it is a database question. |
| chain length | p50 **2**, p90 3, max 10 |
| rounds until a conflict is *visible* | p50 **1**, max **4** |

| conflicts still invisible after k rounds | of 4,992 | share of the world answered "determined" when it is not |
|---|---:|---:|
| k = 1 | 1,321 | **1.128%** |
| k = 2 | 350 | 0.299% |
| k = 3 | 22 | 0.019% |
| k = 4 | **0** | **0.000%** |

**Four rounds and a perfect reader can certify determinacy on this corpus.**
There is no structural barrier. My "can only guess" was wrong, and the reason is
plain in hindsight: the line naming the conflicting ultimate parent *mentions the
queried entity*, so round 1 already hands it over for most entities.

## What survives, and it is narrower and better

**Retrieval has no stopping rule.** At k=1 it has an answer — a filed ultimate
parent, retrieved verbatim, looking complete — and it is silently wrong about
determinacy on **1.128% of the world**. Nothing in the retrieved context says
"there is a second hop you have not fetched". The read set is exactly that
missing thing: a **termination certificate**, the statement that what you hold
is everything the answer depends on. That is a much smaller claim than the one I
made, and unlike it, it is supported.

**And it over-fetches by 46x.** Fetching everything that mentions an identifier
pulls in every child of every hub on the path:

| | tokens |
|---|---:|
| what the answer depends on (measured read set) | **41** |
| what an ideal retriever actually pulls | **1,901** mean, 272 p50, 31,863 max |

So the realistic price, at 2.08 rounds x (1,901 retrieved + 400 overhead) =
2,731 tokens per query, input only, $15/Mtok:

| opponent | $ per query | advantage |
|---|---:|---:|
| handed the whole corpus (the published framing) | $61.18 | 5.01e12 |
| **realistic agentic retrieval, ideal recall** | **$4.10e-02** | **3.36e9** marginal, **1.30e9** amortised |
| oracle retrieval (knows the dependency already) | $6.15e-04 | 5.03e7 |
| — and the substrate on a workload of *one* query | $2.26e-06 | 271x |

The realistic opponent is **67x more expensive than the oracle one**, not
cheaper, because over-fetching is paid on every round.

## Predictions against outcomes

Registered in
`notes/decisions/2026-08-18-price-the-realistic-opponent-agentic-retrieval-not-an-oracle.md`.

| predicted | measured |
|---|---|
| lookup answered at round 1 for >=95% | **100%** |
| silent error at k=1 of **4.0-4.5%** (approximately the conflict rate) | **1.128%** — wrong by 4x, against my own argument |
| rounds p50 2, p90 3, max 64 | p50 2, p90 2, **max 4** |
| realistic advantage **1e5-1e6** | **3.36e9** — wrong by three orders, in my favour |

Two misses in opposite directions, which is the useful kind. I over-estimated
how hidden a conflict is (retrieval sees most of them immediately) and
under-estimated how much junk retrieval drags in (46x the necessary context).
The cost claim came out *stronger* than predicted and the capability claim came
out *weaker*, and the strategy that follows is the one supported by both.

## A control that failed first, and had to be fixed

The first version of the visibility test seeded the retriever's held set with
the chain prefix only, so it never learned the identifier its own round-1 result
named. It reported **4,992 of 4,992** conflicts invisible at k=1 — exactly my
prediction, which is what made me look at it. Corrected, the number is 1,321.

A control that confirms the author's prediction to three significant figures is
the thing this repo has a lesson about, and it took one reading of the code to
catch. It is recorded here rather than quietly fixed.

## What would refute this

- **Ideal recall by exact identifier is generous in one direction and harsh in
  another.** Real retrieval over 20-character LEIs would do worse on recall;
  real retrieval over *names* would do better on the first hop and much worse on
  precision. This is one point, not a curve over retrievers.
- **A perfect reader is assumed.** Every number here charges the model nothing
  for failing to notice a contradiction that is sitting in its context. That
  keeps these rows as lower bounds on its cost and upper bounds on its ability.
- **Four rounds closes it on a graph with p50 chain length 2.** On a deeper or
  denser graph the rounds grow and so does the over-fetch; nothing here predicts
  where it lands.
- The 1.128% silent-error figure is the rate at *the natural stopping point*.
  An agent instructed to always take four rounds pays 4x and is not wrong at
  all — so the finding is about the default, not about a ceiling.

## Built

`scripts/retrieval_rounds.py`.
