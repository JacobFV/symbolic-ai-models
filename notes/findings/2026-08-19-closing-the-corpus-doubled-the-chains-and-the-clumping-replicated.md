---
title: Closing the corpus doubled the chains — the hand reader's clumping replicated, and three-hop is unmeasurable by construction
date: 2026-08-19
status: measured
arm: multi-hop-world
---

The lesson note said plainly that no composed-query claim could rest on 191
chains at a few per cent. The fix is not a better estimator, it is more chains,
and the corpus was **not closed under the relation it is about**: 1,037 distinct
parent QIDs were named by the corpus and absent from it.

Fetching them — about 60 batched requests — added **841 articles**. Two-hop
chains **191 → 415**, plus **86 three-hop chains** that did not exist before.
`data/artifacts/wikipedia_parents_closed.jsonl`, 2,502 articles; the 168- and
1,661-article files are untouched, so every published number keeps its corpus.

## 1. The clumping replicates, at better power

| reader | corpus | one hop | two hop | `p₁²` | **ratio** | z | p |
|---|---|---|---|---|---|---|---|
| hand | 191 chains | 0.173 | 11/191 = 0.058 | 0.030 | **1.93** | 2.25 | 0.025 |
| **hand** | **415 chains** | 0.176 | **20/415 = 0.048** | 0.031 | **1.56** | 2.04 | **0.042** |
| learned | 415 chains | 0.120 | 6/415 = 0.014 | 0.014 | **1.00** | −0.01 | 0.994 |

**Same direction, independent chain population, twice the events.** The hand
reader beats independence on both corpora at p = 0.025 and p = 0.042; the ratio
falls from 1.93 to 1.56, which is what one expects when the first estimate was
the high tail of a noisy draw. The mechanism proposed earlier survives the
replication: four patterns succeed on canonically-phrased articles, and such an
article tends to name a parent whose own article is also canonical.

**The learned reader lands at ratio 1.00, z = −0.01.** Yesterday's "within 0.001"
was withdrawn as luck at k=6; this is the same conclusion at k=6 again but now
with the hand reader as a *positive control in the same measurement* — the test
can detect clumping when clumping is there, and it does not detect it here.
That is a much better reason to believe independence than the point estimate was.

## 2. The learned reader got worse, and the reason is a cross-check

One-hop fell **0.178 → 0.120** despite training on 2,502 articles instead of
1,661. The reader did not degrade; the **population did**. The 841 new articles
are parent companies — hubs — and hubs are exactly the articles measured to read
worst (0.126 against 0.197, mean in-degree 0.124 for wrong against 0.076 for
correct). Closing the corpus under the parent relation necessarily enriches it
with hubs, so the chain set got harder in precisely the way the blast-radius
finding predicts.

Two findings measured for different reasons agreeing on a third quantity is the
kind of check this repo is usually short of.

## 3. Three-hop is unmeasurable, and that is arithmetic not pessimism

86 three-hop chains now exist. At a one-hop rate of 0.120 the independent
prediction is `0.120³ = 0.0017`, which over 86 chains is **0.15 expected
successes**. No three-hop claim can be made from this corpus at this reader
quality — not with a better test, not with more careful analysis.

To get 20 expected three-hop successes at this reader you would need ~11,500
three-hop chains; at a reader of 0.4 you would need 300. **The reader is the
binding constraint on measurability, not the corpus** — which is the same
conclusion the six closed levers reached, arriving from the statistics instead.

## 4. Economics, restated on the bigger world

Ingesting 2,502 articles: 566,513 tokens, 26.9 s, **$1.50e-04 once**. A $3/Mtok
API re-reading the corpus per query pays **$1.70 every time** — 11,355x at a
single query. Both sides scaled with the corpus, as they must; the ratio is
stable because both are linear in tokens.

## What would have refuted the replication

The hand reader's excess vanishing on the new chain population — it would have
meant the first result was a draw from a noisy tail and the clumping story was
imagination. It fell from 1.93 to 1.56 and stayed significant, which is the
profile of a real effect first measured optimistically.
