---
title: Position was an artefact there and is a signal here
date: 2026-08-19
status: measured
arm: entity-typing
---

## Crude typing does not rescue the ranker

Three routes named **entity typing** as the missing capability, and the ranker
refutation named exactly what it picks instead of owners — nationality adjectives
and bare acronyms. So: reject a candidate that is a single word which is a
nationality adjective or an all-caps acronym. No gazetteer, no network, the same
closed-class shape as the cancellation cues.

| policy | coverage | correct | **precision** |
|---|---:|---:|---:|
| first match | 0.589 | **0.369** | **0.626** |
| first match + typing | 0.548 | 0.333 | 0.609 |
| ranked by corroboration | 0.589 | 0.315 | 0.535 |
| **ranked + typing** | 0.548 | 0.298 | **0.543** |

**Typing moves the ranker by 0.008 and costs first-match 0.017.** Coverage falls
by 7 articles in both arms, because the acronym rule rejects real single-word
company names along with *CPR*. That was the refutation condition: the ranker
stays below first-match, so the nationality examples were vivid but not the bulk
of its deficit.

## What is actually carrying the task

Precision by the candidate's **position** in the intro:

| rank | n | **precision** |
|---:|---:|---:|
| **1** | 99 | **0.626** |
| 2 | 40 | 0.375 |
| 3 | 18 | 0.278 |
| 4 | 7 | 0.286 |
| *(last, whatever its rank)* | 99 | *0.485* |

**Monotone, and the first candidate is 1.7× the second.** Position dominates every
content-based idea tried on this task:

| feature | precision |
|---|---:|
| **position (first match)** | **0.626** |
| crude entity typing | 0.609 |
| candidate agreement | 0.603 |
| mention-count ranking | 0.535 |

The one thing that beats it — corroboration at 0.718 — does so as a **filter over**
first-match, not as a replacement for it. **Everything that replaced position
lost.**

## The reframe, and it is not a contradiction

Flood's headline finding was that `read_signature`'s 1.000 was **propped up by
position** — hard-coded paragraph indices — and shuffling the paragraphs took it
to 0.000. The repo then spent considerable effort building content-based readers
to remove that crutch. On real prose, position is the best signal available and
none of the replacements beats it.

> **Position was an artefact there and is a signal here.** In a generated surface
> the ordering is imposed by a five-paragraph template: destroyed by shuffling,
> and therefore a leak. In an encyclopedia intro it is **editorial convention** —
> a lead states the current owner first — which is stable across documents written
> by different people, and therefore a feature.

The test that separates them is the one the repo already runs: **does shuffling
destroy it?** A template's order does not survive `interleave`; a genre's
convention is not something the reader imposed, and there is nothing to shuffle
because every document was written that way independently.

That is worth carrying because the repo's instinct — position is a crutch, content
is the real thing — is **half right, and the half that is wrong is the half that
applies to real text.**

## What would refute this

- 99 first-rank candidates and 40 second-rank; the 1-vs-2 gap is the claim and
  the tail is thin.
- One genre with strong editorial convention. News, filings and transcripts order
  differently, and a genre with no convention would restore the repo's instinct.
- The extractor's patterns may themselves be ordered — if the `subsidiary of`
  pattern tends to fire earlier than `acquired by`, part of the position effect is
  the pattern list, not the prose. Unmeasured.
