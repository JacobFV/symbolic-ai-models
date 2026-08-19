---
title: The stage accounting closes — rendering is minor
date: 2026-08-19
status: measured
arm: price-the-renderer
---

## Applying the lesson immediately, to the stage nobody had measured

The lesson written this turn says to check a metric where its **missing term
dominates**. The ledger knows three stages — read, solve, render — and only two
had ever been measured. No milestone has priced producing the grounded
paragraph, which is the pipeline's actual deliverable.

| domain | read ms | solve ms | render ms | read % | solve % | **render %** |
|---|---:|---:|---:|---:|---:|---:|
| flood | 0.206 | 9.236 | 0.019 | 2.2% | 97.6% | **0.2%** |
| scheduling | 0.251 | 24.576 | 0.017 | 1.0% | 98.9% | **0.1%** |
| solvency | 0.057 | 0.002 | 0.006 | 87.8% | 2.8% | **9.4%** |

**Rendering is minor everywhere**, at most 9.4%. I predicted it would be
comparable to reading in solvency; it is about a tenth of it. That is a negative
result and it **closes** the stage accounting rather than opening it: all three
stages are now measured, and the read/solve split is the whole story.

## The one number worth keeping

Solvency's renderer costs **0.006 ms against a solver at 0.002 ms** — the
pipeline spends **three times more explaining the answer than computing it**. Put
with the rest of that row:

> In solvency, **97.2% of the pipeline is text handling** (87.8% reading, 9.4%
> rendering) and **2.8% is reasoning.**

That is the sharpest available statement of what a symbolic pipeline costs when
the reasoning is genuinely cheap, and it is the regime the programme's thesis
describes.

## Why this was worth running anyway

The direction was predictable; the *share* was not, and the share is the
diagnostic. A renderer at 5% changes nothing; at 60% it would have meant
solvency's cost is dominated by explanation rather than by parsing, which is a
different claim about where symbolic pipelines spend.

It also forecloses a future surprise of exactly the kind that produced the last
two findings — "we never priced rendering" is now answered rather than
outstanding.

## What would refute this

- Renderers here emit a few sentences from a handful of claims. A renderer that
  had to *select* what to say — ranking, summarising, choosing among many true
  statements — would not be a string-formatting routine and this measurement
  would not transfer.
- Single-machine Python timings again. The ordering is what survives.
