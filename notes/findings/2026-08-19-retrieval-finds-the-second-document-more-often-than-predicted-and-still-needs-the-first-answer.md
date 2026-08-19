---
title: Retrieval finds the second document more often than predicted — and still cannot start without the first answer
date: 2026-08-19
status: measured
arm: retrieval-baseline
---

The multi-hop result compared a persistent world against an API re-reading all
1,661 articles per query, and its own note called that comparison unfair: nobody
deploys it. A retrieval system fetches a handful of documents and pays for a
handful. This is the fair version, and it attacks the strongest claim this
programme currently holds.

BM25 over the same corpus — no model, no GPU, no pretrained weights, so the
baseline is something this repo could deploy beside its kernels.
`runs/retrieval_baseline.json`.

## 1. What retrieval finds, from the question alone

| top-k | hop-1 article | **hop-2 article** | both | iterative, **given gold hop 1** |
|---|---|---|---|---|
| 1 | 0.885 | **0.073** | 0.016 | 0.670 |
| 3 | 0.984 | 0.429 | 0.424 | 0.953 |
| 5 | 0.995 | **0.492** | 0.492 | 0.979 |
| 10 | 0.995 | 0.545 | 0.545 | 0.995 |

**Predicted the hop-2 article in the top 5 for "well under 20%" of chains.
Measured 0.492.** Wrong, and wrong in retrieval's favour — a 1,661-article
corpus is topically clustered enough that a company's parent is often lexically
near it. On a corpus of millions this number would fall, and that is a reason to
distrust it rather than to lean on it.

## 2. The structural claim survives, and it is the one that matters

The last column is retrieval's **ceiling**, not an achievable accuracy: it is
handed the gold answer to hop 1 and asked only whether the second retrieval then
succeeds. It does, 0.953 at k=3.

That is exactly the point. **The second retrieval is keyed on hop 1's answer**,
so an iterative RAG loop inherits the same extraction factor `p₁` the symbolic
reader has. With a reader at 0.178, the loop reaches the hop-2 article about 17%
of the time however good the retriever is. *Multi-hop retrieval does not remove
the extraction problem; it moves it inside the loop* — and it pays for two
retrievals and two reads to get there, where the persistent world paid once and
had already done the join.

The single-shot column says the same thing from the other side: at k=1, the hop-2
article is found **7.3%** of the time. Without an iteration keyed on an extracted
answer, the question simply does not reach the document that holds half of it.

## 3. The cost verdict survives the fair comparison

| | per query |
|---|---|
| single-shot RAG, 5 articles | $3.16e-03 |
| **iterative RAG, 2x5 articles** | **$6.32e-03** |
| persistent world, ingestion | **$1.16e-04 once** |

| queries | world per query | vs iterative RAG |
|---|---|---|
| 1 | $1.16e-04 | **54.5x** |
| 10 | $1.16e-05 | 545x |
| 100 | $1.16e-06 | 5,450x |
| 10,000 | $1.16e-08 | **545,020x** |

**The world is cheaper from the first query onward** — the whole ingestion of
1,661 articles costs under 2% of one iterative RAG query. The earlier 9,050x
against full re-reading was the wrong comparison and the right one is 54.5x at
n=1, growing linearly.

## 4. What this does not settle

- **Accuracy is not compared.** Both sides are priced; only the symbolic side's
  reading accuracy is measured (0.031 two-hop). An LLM reading five retrieved
  articles would very likely read them better. The claim here is about **cost and
  reachability**, not capability, and the reachability half is the durable one.
- **BM25, not a dense retriever.** A better similarity function would raise the
  hop-2 numbers; it would not make hop 2 reachable *without* hop 1's answer,
  which is the structural limit.
- **1,661 articles.** The clustering that helped retrieval here is a
  small-corpus effect and should be expected to weaken with scale.

## What would have refuted it

The hop-2 article being reachable from the question at high rate without
iteration — retrieval would then do the join implicitly and the persistent
world's advantage would be cost alone. At k=1 it is 7.3%.
