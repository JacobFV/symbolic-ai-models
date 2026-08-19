---
title: The extractor that wins on facts by 0.121 F1 loses on every aggregate query — abstention builds a half-empty world, and the ranking of extractors is a property of whether you measure facts or answers
date: 2026-08-18
author: lead
status: provisional
tags: [extraction, composition, cost, metrics, refuted-prediction, abstention, system-cost]
---

## The question `CLAUDE.md` requires and nobody had asked

> Cost is charged to the **system**: if a reasoner only works because something
> upstream produced a graph, that upstream component is in the ledger whether or
> not it exists yet.

Both arrows are measured, separately: extraction at ~62% of a 0.99 ceiling,
reasoning at 37x–13,987x maintenance advantage. **What does the second do when it
runs on what the first produces?**

Two worlds over the same 5,000 OpenAlex works — the **reference** built from
OpenAlex's labels, the **extracted** built by the zero-shot registry extractor,
which needs no training split and so carries no leakage anywhere. Then queries of
increasing dependency.

## Result 1 — error amplifies 1.85x, and recall is what dies

| query class | n | Jaccard | precision | recall | **amplification** |
|---|---:|---:|---:|---:|---:|
| `institutions_of(work)` — depth 1 | 5,000 | 0.544 | 83.9% | 43.8% | 1.00x |
| `works_at(institution)` | 2,000 | 0.331 | 94.1% | 42.1% | 1.47x |
| `collaborators(institution)` | 1,913 | **0.157** | 84.0% | **20.4%** | **1.85x** |
| `works_at_count(institution)` | 2,000 | — | — | — | **100% median relative error** |

I predicted union would *raise* recall and *lower* precision. The opposite:
precision holds at 84–94% and recall collapses to 20.4%.

**The mechanism is world size.** The extracted world has **2,270 institutions and
8,114 facts** against the reference's **4,539 and 15,543** — half the entities,
52% of the facts — because the extractor **abstains** on every ambiguous
component. A collaborator that was never extracted anywhere cannot be recovered
by any union, and a count over a half-empty world is off by 100%.

## Result 2 — so the operating point was chosen on the wrong metric

If abstention is what empties the world, take it out. `v4r` emits **every**
candidate for an ambiguous component instead of refusing — at the fact level that
is strictly worse, and it is exactly the "guessing where the system knows least"
that lost three times in this repo today.

| | **v4** abstains | **v4r** high recall | Δ |
|---|---:|---:|---:|
| world | 2,270 inst / 8,114 facts | **4,355 inst / 25,714 facts** | — |
| **fact-level F1** | **0.576** | 0.455 | **−0.121** |
| `collaborators` F1 | 0.328 | **0.413** | **+0.085** |
| `works_at` F1 | 0.582 | **0.640** | **+0.058** |
| count median relative error | 100.0% | **50.0%** | **halved** |

> **The extractor that wins on facts by 0.121 F1 loses on every aggregate query.**

`v4r`'s world reaches **4,355 of the reference's 4,539 institutions** — near-total
entity coverage — at the cost of precision 36.5%. And that trade is worth making,
because aggregate queries pay for **completeness**, not precision: a spurious fact
pollutes only the queries that touch it, while a missing entity is unreachable
from everywhere.

## What this overturns

**"Abstention beats guessing" is true at the fact level and backwards at the
system level.** I concluded it three times today — the word-overlap fallback, the
relaxed admission in the geo arm, and the extractor's own design — every time on
fact-level evidence alone, and every time it was the only evidence available.
Now it is not.

This is the repo's oldest documented trap in a new costume:

> *A ranking is a property of a metric, never of a set of models. Where two
> defensible metrics disagree, that disagreement **is** the finding.*

Here the two metrics rank the two extractors **inversely**, and the one this
programme has been optimising — fact-level F1 — is the one that does not
correspond to anything a user asks for.

There is also a real tension with a stated engineering rule here, **"no fallbacks
— fail loudly"**. That rule is about a *silent* fallback making a broken component
read as a working one, and it stands. An extractor that deliberately emits its
uncertain candidates is not silent — but it does mean **world construction and
answer construction want opposite defaults**, and nothing in the architecture
currently says so.

## The ledger, which is the point of the exercise

Building this world once, over 5,000 works:

| | | |
|---|---:|---|
| symbolic | 0.9 s, **$5.08e-06** | 57.6% F1 at the fact level |
| model, input tokens only, perfect extraction assumed | 1,268,408 tok, **$19.03** | a lower bound |
| ratio | **3,746,454x** | |

So every advantage in `HANDOVER.md` §3, §3b and §3c is quoted over **a world
someone else built**. Built by us, at 3.7 million times less, the world is 57.6%
right at the fact level and answers `collaborators` at Jaccard 0.157 — or 0.196
if you pick the operating point on the query rather than on the fact.

## Floors, computed after the fact

These numbers were first published **without floors**, against this repo's
standing rule that a lift is quoted against a floor or not quoted at all — and
against `symbolic_ai_core/cost.py`, which enforces it in code by dividing by
`accuracy - floor`. `scripts/query_floors.py` computes them: return the `N` most
frequent items in the reference world, `N` = the mean true answer size, using no
per-query information at all.

| query class | floor | best measured | **lift** | share that was floor |
|---|---:|---:|---:|---:|
| `institutions_of(work)` | 0.034 | 0.576 | **0.542** | 6.0% |
| `collaborators(institution)` | **0.120** | 0.417 | **0.297** | **28.8%** |
| `works_at(institution)` | 0.027 | 0.671 | **0.644** | 4.0% |
| `works_at_both(A,B)` | 0.022 | 0.465 | **0.443** | 4.8% |
| `institutions_unique_to(w1,w2)` | 0.033 | 0.599 | **0.566** | 5.6% |

**No floor meets or beats its measured system, so nothing here retracts.** But
`collaborators` — the class quoted most in this arm — had **29%** of its score
bought by a guess that ignores the query, because collaboration is heavy-tailed
and large institutions co-occur with nearly everyone. Read its lift as **0.297**,
not 0.417. The other four lose 4–6%.

## What would refute it

- **Two operating points, not a curve.** `v4` and `v4r` bracket a range; the best
  point is somewhere between and was not searched. The *inversion* is the claim,
  not either number.
- **One query family.** `collaborators` and `works_at` are set unions over an
  inverted index. A query that intersects, or that requires *all* of something,
  should punish over-generation instead of rewarding it — and that experiment
  would sharpen the rule from "completeness wins" to "completeness wins for
  existential queries", which is the shape this repo keeps finding.
- **The anchor is agreement with OpenAlex**, not truth, as in every finding in
  this arm.
- **Amplification is measured against Jaccard**, `(1−J_query)/(1−J_fact)`. A
  different error measure gives a different multiplier; the ordering does not
  change.

## Reproduce

```bash
SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \
  uv run python -u scripts/two_arrows_end_to_end.py
```

`runs/two_arrows_end_to_end.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `error-propagation-arrow1-to-arrow2`.
