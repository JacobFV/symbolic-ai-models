---
title: Dropping the dense-graph arm — I already expect its answer — and pricing the query's *dependency* instead
date: 2026-08-18
status: decided
tags: [decision, ambiguity, cost, advantage-curve, gleif]
---

## Dropped, deliberately

The parked arm "run scoped enumeration, additive bounds and set propagation on
the route network" is **not being pursued**, and the reason is that I wrote down
what I expected it to show — large read sets, scoping refusing often, bounds
inapplicable, set propagation asked constantly — and that expectation is the
whole information content of the experiment. Running it would buy a confirmation
and cost a session. The prediction stands in
`notes/questions/2026-08-18-the-same-three-mechanisms-on-a-dense-graph-and-a-real-cross-source-property-conflict.md`
as a prediction; if something later contradicts it, that is the finding.

## What is being done instead, and why it is the objective

The north star is **$ per solved episode above floor**, and the argument for
this whole substrate is the advantage curve: three points, one corpus, seven
orders of magnitude, ordered by *how much of the answer lives in structure the
model must be handed*. The largest of them —
**1.85e11 on ultimate parent, from 1.99M tokens of ownership edges** — is
computed by handing a language model **the entire graph**.

That framing has never been tested, and this week's work built the instrument
that tests it: a query's **read set** is now measurable, so the *minimum context
a correct answerer needs* is a number rather than an assumption. If a point
query depends on three filings, then an opponent with oracle retrieval is given
three filings, not 254,815 edges, and the advantage that framing claims is
mostly an artefact of the framing.

So: measure the necessary context per query class, and price both framings.

**Predicted before the measurement:**

1. The point query's necessary context is **under 500 tokens** (a chain of
   median length ~2, plus the competing filings where they exist), against
   1.99M for the whole graph — a **>3,000x** reduction in the opponent's cost.
2. The advantage therefore **falls by three to four orders of magnitude** on
   that row, from ~1e11 to ~1e7, and **does not vanish**, because the symbolic
   side is 2.8 µs.
3. For the aggregate queries — the US-domiciled count over 598 ambiguous
   alignments, the census of which of 117,129 answers are undetermined —
   retrieval cannot shrink anything, because the dependency **is** the corpus.
   Those rows stay within 1 order of magnitude of their naive value.
4. So the spread *within one corpus and one substrate* is at least **four orders
   of magnitude**, driven by dependency size rather than corpus size — which is
   a different variable from the one the published curve names.

**What would make this a failure worth recording:** if necessary context is not
much smaller than the corpus for any query class here, the published framing was
right and the instrument found nothing.

## The pricing convention, stated because a ratio without one is not a number

- Symbolic: measured CPU seconds at `cost.py`'s `$0.02` per core-hour.
- LLM: **input tokens only, at published per-Mtok rates**, assuming the model is
  perfect, answers in zero output tokens, and pays no retrieval cost. That is a
  **lower bound on its cost**, not an estimate of it — which is why these rows,
  unlike the earlier ones, do not carry the equal-accuracy assumption and are
  not stamped NOT QUOTABLE. A lower bound needs no accuracy claim.
- Rates: **$1/Mtok** (the cheap tier) and **$15/Mtok** (the frontier tier), the
  same two this repo's earlier rows used, so the numbers are comparable.
- Tokens: **characters / 4**, stated rather than implied, and checked against
  the published 1.99M figure for the same corpus.
