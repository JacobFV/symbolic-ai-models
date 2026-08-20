---
title: Four factors reproduce the rate exactly — and two of them need no model, which is the screening statistic
date: 2026-08-19
status: measured
arm: relation-readability
---

Every decomposition this session used **ceiling × classifier × ranker**. The
phrase-proposer result showed a fourth factor nobody had measured: a candidate
the proposer cannot produce is an answer the reader cannot give, and on `industry`
that factor was zero while the other three looked ordinary.

Measured properly, on the same articles, for both proposers:

| relation | proposer | contain | propose | classifier | ranker | **product** | **measured** |
|---|---|---|---|---|---|---|---|
| `parent` | Capitalised | 0.592 | 0.782 | **0.302** | 0.796 | 0.111 | **0.107** |
| `parent` | Phrase | 0.592 | 0.871 | **0.317** | 0.812 | 0.133 | **0.129** |
| `industry` | Capitalised | 0.241 | **0.006** | 0.000 | 0.000 | 0.000 | **0.000** |
| `industry` | Phrase | 0.241 | 0.805 | **0.138** | 0.818 | 0.022 | **0.021** |

**The product lands within 0.004 of the measured rate in all four rows.** The
decomposition is complete — there is no fifth factor hiding, and document-level
aggregation is worth almost nothing here, which is consistent with the earlier
finding that the oracle over the reader's own proposals sits 0.012 above argmax.

## Different relations, different bottlenecks

- **`parent` is classifier-bound.** 0.302 against ≥0.59 for everything else. The
  reader recognises fewer than a third of the sentences that state the relation
  and are proposable.
- **`industry` under capitalised runs is proposer-bound at 0.006** — the entire
  story, exactly as the lowercase-values finding said.
- **The phrase proposer's `parent` gain decomposes as mostly proposal**: 0.782 →
  0.871, with the classifier and ranker moving 0.015 each. That is the same
  conclusion the seen/unseen split reached — it proposes the right candidate more
  often because it knows which candidates are parents.

Nobody could have said "these two relations have different bottlenecks" before
the proposer was measured, because it was assumed to be 1.0.

## Two of the four need no model at all — the screening statistic, found

`containment` and `proposal` are properties of **the corpus and the proposer**.
Neither needs a classifier, a ranker, or any training. Their product is a
**model-free upper bound on any reader**:

| relation | proposer | contain × propose | reader achieved |
|---|---|---|---|
| `parent` | Capitalised | **0.463** | 0.107 |
| `parent` | Phrase | **0.516** | 0.129 |
| `industry` | Capitalised | **0.001** | 0.000 |
| `industry` | Phrase | **0.194** | 0.021 |

That is the screening statistic the frame-concentration attempt failed to find
two turns ago. It answers the practical question directly — *is this relation
worth building an extractor for, and does my proposer admit its answers?* — and
it is computable in seconds from gold strings and a proposer, with no fitting.

It would have said, before any work: `industry` under capitalised runs has a
ceiling of **0.001** and is not worth attempting; under a phrase proposer it has
0.194 and is. That is exactly the triage the earlier attempt was reaching for, and
it comes from the decomposition rather than from a correlation over five points.

## What would have refuted it

The product missing the measured rate — a fifth factor, or interaction between
them, would have shown as a systematic gap. The largest discrepancy across four
rows is 0.004, and it is in the direction aggregation predicts.

## Limits

- **Two relations, one corpus.** The claim that the product is complete rests on
  four rows.
- The `ranker` factor here is conditioned on *a labelled sentence containing the
  gold* and reads ≈0.80; the 0.533 quoted earlier in the session is a different
  conditional over articles, not a contradiction.
- `industry`'s row is 51 correct answers.
