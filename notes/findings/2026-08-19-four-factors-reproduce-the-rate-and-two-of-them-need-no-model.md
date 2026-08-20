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

## Extended to five relations: it holds, and the classifier is binding in all of them

The four-row version named its own limit. All five relations with gold on the same
articles, both proposers — ten rows:

| relation | proposer | contain | propose | **classifier** | ranker | product | measured | gap |
|---|---|---|---|---|---|---|---|---|
| `parent` | Capitalised | 0.592 | 0.782 | **0.338** | 0.782 | 0.122 | 0.116 | +0.007 |
| | Phrase | 0.592 | 0.871 | **0.351** | 0.759 | 0.138 | 0.133 | +0.005 |
| `country` | Capitalised | 0.579 | 0.804 | **0.455** | 0.889 | 0.188 | 0.169 | +0.019 |
| | Phrase | 0.579 | 0.896 | **0.455** | 0.888 | 0.209 | 0.192 | +0.018 |
| `headquarters` | Capitalised | 0.551 | 0.873 | **0.536** | 0.870 | 0.224 | 0.218 | +0.006 |
| | Phrase | 0.551 | 0.937 | **0.522** | 0.873 | 0.235 | 0.230 | +0.005 |
| `founder` | Capitalised | 0.424 | 0.735 | **0.372** | 0.856 | 0.099 | 0.098 | +0.001 |
| | Phrase | 0.424 | 0.789 | **0.376** | 0.859 | 0.108 | 0.107 | +0.001 |
| `industry` | Capitalised | 0.241 | **0.006** | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| | Phrase | 0.241 | 0.805 | **0.158** | 0.810 | 0.025 | 0.025 | 0.000 |

**Every gap is between 0.000 and 0.019, and every one is positive** — the product
is a slight *upper* bound, which is what it should be, since the four gates can be
passed by different sentences in the same article.

**The classifier is the lowest factor in all five relations** — 0.158 to 0.536,
against a ranker that never drops below 0.759 and a proposal that never drops
below 0.735 once the proposer can represent the values. The one exception proves
the rule: `industry` under capitalised runs is proposer-bound at 0.006, which is
the case where the component cannot express the answer at all.

That generalises the model-class conclusion well beyond `parent`. **The
sentence-level decision — does this sentence state this relation — is the binding
factor for every relation measured**, and it is the factor that four
representations and a set of explicit conjunctions could not move.

The phrase proposer raises `proposal` in every relation (+0.05 to +0.09) and moves
the classifier and ranker by ≤0.015, which is the decomposition confirming from a
third angle that its `parent` gain was proposal — a vocabulary prior — and not
reading.

## Limits

- **One corpus, one genre.** Five relations, but all company intros.
- The classifier factors here differ slightly from the four-row run (`parent`
  0.338 against 0.302) because `RELS` now contains five relations, so distant
  supervision assigns some sentences to a different label. The comparison within
  this table is like-for-like; across the two runs it is not.
- The `ranker` factor here is conditioned on *a labelled sentence containing the
  gold* and reads ≈0.80; the 0.533 quoted earlier in the session is a different
  conditional over articles, not a contradiction.
- `industry`'s row is 51 correct answers.
