---
title: Pre-registration — the honest opponent is agentic multi-hop retrieval, and the question is whether it can find the dependency at all
date: 2026-08-18
status: preregistered
tags: [cost, advantage-curve, retrieval, ambiguity, gleif, preregistration]
---

## Why this and not the next capability

`notes/findings/2026-08-18-the-advantage-curve-was-mostly-the-framing-and-what-is-left-is-a-constant.md`
priced a language model given **exactly** the filings a query depends on and
found a flat ~5e7 advantage. That opponent does not exist: knowing which 32
tokens matter *is* the read set, which is this substrate's output. The finding
said so in its own refuter and then stopped.

The opponent that does exist is **agentic retrieval**: fetch what mentions the
question, read it, discover a new identifier, fetch again. Its cost is rounds x
(prompt + retrieved lines), and its failure mode is stopping early — returning a
confident answer built from a subset of the dependency.

This is the pivot the whole strategic reading rests on, so it is worth
attacking before anything is built on top of it. **If one round of retrieval
covers the dependency for almost every entity, then "we compute the dependency
exactly" is worth very little and the honest summary of the cost work is that
the substrate is a cache.**

## The three measurements

1. **Rounds to close the dependency.** A round is: retrieve every filed line
   containing an identifier you already hold; read it; repeat if it introduced a
   new identifier the answer needs. Reported as a distribution over all 117,129
   scored entities, for the point query and for the determinacy query.
2. **Silent error at k rounds.** The fraction of entities for which a k-round
   retriever has a *complete-looking* context — it fetched everything mentioning
   what it knows — and yet the answer it would give is wrong, or is reported as
   determined when it is not.
3. **The realistic price.** rounds x (fixed prompt + retrieved tokens) at
   $15/Mtok input, against the substrate's measured cost, for both a single
   query and an amortised workload.

## Predicted, before running

1. **The lookup is trivially retrievable and that is not the interesting query.**
   130,355 entities file an ultimate parent, so one round returns the answer
   verbatim. Predicted round-1 answer coverage: **>=95%** of entities that file
   one. Retrieval wins the lookup, and it should — this is a database.
2. **Determinacy is not.** A conflict is a disagreement between the filed
   ultimate and the *chain*, and the chain's second hop names an identifier the
   question never mentions. Predicted: a one-round retriever reports
   "determined" for **essentially every** conflicted entity — silent error rate
   at k=1 of **4.0-4.5%**, i.e. approximately the 4.274% conflict rate.
3. **Rounds to close:** p50 **2**, p90 **3**, max = the longest chain (64 by the
   walk's own cap).
4. **The realistic advantage lands between the two extremes I have already
   published:** roughly **1e5-1e6** marginal per query, versus 5e7 for the
   oracle opponent and 271x for a single-query workload with ingest. If it lands
   above 1e7 the oracle framing was fine; if it lands below 1e4 the cost
   argument is much weaker than this week's headline.

## What would make this a failure worth recording

If silent error at k=1 is near zero — if conflicts are visible from the first
round's context after all — then retrieval certifies determinacy as well as we
do, and the strategic reading in the report above is wrong. That is a real
possible outcome and it is the reason to run this before building anything on
the claim.
