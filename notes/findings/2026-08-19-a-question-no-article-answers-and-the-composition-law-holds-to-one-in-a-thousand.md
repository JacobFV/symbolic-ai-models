---
title: A question no article answers — the composition law holds to 0.001, and the hand reader breaks it upward
date: 2026-08-19
status: measured
arm: multi-hop-world
---

*Who ultimately controls RCA Records?* The RCA Records article says Sony Music.
Nothing in it says who owns Sony Music — that is a different article, by someone
else, that never mentions RCA. The answer exists only in a world assembled from
both, which is the capability this programme is for and the thing a prompt-window
reader cannot do without being handed both documents.

**191 two-hop chains lie entirely inside the 1,661-article corpus** (118 distinct
grandparents), so the query is scored against Wikidata rather than judged.
`runs/multi_hop_world.json`.

## 1. The composition law, with both factors identical

Earlier arms measured that a composed query multiplies reader error — `parent` at
0.149 and `country` at 0.181 gave 0.007 F1 on their join. Here **both hops are
the same relation read by the same reader**, so `p₁ = p₂` exactly and the
independence prediction is unambiguous.

| arm | one hop | **two hop** | independent prediction `p₁²` | ratio |
|---|---|---|---|---|
| learned reader | 0.178 | **0.031** | 0.032 | **0.97** |
| hand patterns | 0.173 | **0.058** | 0.030 | **1.93** |

**The learned reader lands within 0.001 of `p₁²`.** Its two hops are independent
to the precision this sample can measure, which is the cleanest confirmation the
composition law has had — and the strongest statement of the cost of composition:
a reader at 0.18 answers a two-hop question 3 times in 100.

**The hand reader is nearly twice its independent prediction.** Its hops are
positively correlated, and the mechanism is legible: four patterns succeed on
canonically-phrased articles, and a canonically-phrased article tends to name a
parent whose own article is also canonically phrased. A pattern reader does not
sample the corpus uniformly, so its errors clump — which makes it *better* at
multi-hop than its single-hop rate implies, and worse than it looks at coverage.

That is a property worth carrying: **independence is a property of how a reader
fails, not of the query.** The learned reader is the one that behaves like the
model, and it is the one whose failures are spread evenly.

## 2. Linking was free, and the test was easier than it looked

Predicted that cross-document entity resolution would lose 20–40% of correctly
read parents. Measured **0.971** (learned) and **1.000** (hand) linked given a
correct first hop.

That prediction was wrong for a reason worth stating rather than celebrating:
the gold parent label and the target article's title both come from the same
knowledge base, so a correctly-read parent is a string that already *is* a title.
**The linking test is easy by construction here**, and this number should not be
read as evidence that cross-document identity is easy in general. It says only
that when the read string is right, joining it costs nothing on this corpus.

## 3. What the world costs, and what re-reading costs

Ingesting all 1,661 articles: 350,041 tokens, 20.9 s, **$1.16e-04 once**.

| queries answered from the world | ingestion per query |
|---|---|
| 1 | $1.16e-04 |
| 100 | $1.16e-06 |
| 10,000 | $1.16e-08 |
| 1,000,000 | $1.16e-10 |

A $3/Mtok API asked to re-read the corpus for each query pays **$1.05 every
time**. Even at a single query the world is **9,050x** cheaper, and the ratio
grows linearly with use — which is the whole economic argument for persistence,
now measured on real text rather than asserted:

> a fact extracted once and consulted a million times is priced differently from
> a context window re-read a million times.

## 4. What this does not show

- **Accuracy is low in absolute terms.** 0.031 two-hop for the learned reader and
  0.058 for the patterns. The economics are strong and the reading is weak, and
  the composed query is where that shows most.
- The one-hop rates here (0.178 / 0.173) are on the **191-chain subset**, a
  harder population than the full corpus (0.182 / 0.393 for the hand reader),
  because a company whose parent also has an article is a different kind of
  company.
- The API row prices re-reading the *whole corpus* per query, which is the
  comparison persistence is for. An API given only the two relevant articles
  would pay far less, and would need to be told which two — which is the
  retrieval problem this measurement does not address.

## What would have refuted it

Two-hop accuracy landing near one-hop, which would have meant the second hop is
nearly free and composition does not multiply. It landed at `p₁²` to within
0.001 for the reader whose failures are uncorrelated.
