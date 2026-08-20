---
title: A phrase proposer unlocks an impossible relation — and its gain elsewhere is a vocabulary prior, not reading
date: 2026-08-19
status: measured
arm: relation-readability
---

`industry` read **0.000** because `CapitalisedMentions` proposes runs of
capitalised words and 97.9% of `industry` values are lowercase. The reader could
not produce a candidate, so the relation was unanswerable by construction.

`PhraseMentions` (new, in `symbolic_ai_core/reader/learned.py`) proposes from a
**learned phrase inventory** — the fillers seen in training, plus any productive
suffix they share, so an unseen `pharmaceutical industry` is proposable from
`… industry` — and keeps capitalised runs alongside so proper-noun relations are
unaffected. Determiners are stripped, because gold says `pharmaceutical industry`
and never `the pharmaceutical industry`.

## Both relations

| relation | proposer | coverage | correct | precision | k/n |
|---|---|---|---|---|---|
| `industry` | CapitalisedMentions | 0.092 | **0.000** | 0.000 | 0/2058 |
| | **PhraseMentions** | 0.081 | **0.025** | 0.307 | 51/2058 |
| `parent` | CapitalisedMentions | 0.286 | 0.109 | 0.382 | 195/1788 |
| | **PhraseMentions** | 0.283 | **0.128** | 0.451 | **228/1788** |

`industry` becomes answerable — a relation that was structurally impossible now
produces 51 correct answers at 0.307 precision. It is far below its containment
ceiling of 0.241, so most of that relation is still unread, but the barrier that
made it *unreadable* is gone.

And `parent` gained **+33 articles**, which is five times larger than any feature
intervention this session produced. **That is the result that needed checking.**

## The `parent` gain is a vocabulary prior

Splitting the test articles by whether their gold parent appeared in the
training-fold inventory:

| | articles | correct |
|---|---|---|
| gold parent **was** in the inventory | 795 (44.5%) | **0.184** |
| gold parent was **not** | 993 (55.5%) | **0.088** |

**2.1x better on answers it has seen before.** On answers it has not seen, 0.088
— at or below what the capitalised proposer manages overall (0.109).

So the +33 is not better reading. It is the proposer **preferring candidates it
knows are parents**, which is a prior over the answer set rather than a signal
from the text. That is the same shape as the renaming control on the generated
domains: an improvement that comes from knowing the vocabulary, not from reading
the language.

## What is legitimately claimable

- **`industry` 0.000 → 0.025 is real and is not a prior**: the relation went from
  having no expressible candidates to having some, and the suffix rule proposes
  values never seen in training.
- **`parent` +33 is a prior and should be reported as one.** A deployed system
  usually *does* have a candidate KB, so the prior is usable and worth having —
  but it must not be counted as evidence that candidate generation was the
  reading bottleneck.
- **Candidate generation is a hard bound nobody was measuring.** Before this,
  every number on `industry` was a statement about a component that could not
  represent the answer. The proposer belongs in any future decomposition beside
  the classifier and the ranker.

## What would have refuted the deflation

The unseen-inventory half performing at the seen-inventory rate — the gain would
then have been reading rather than memory. It is 0.088 against 0.184.

## Limits

- One corpus, two relations.
- The inventory is induced per fold from training gold only, so there is no
  leakage; the 44.5% overlap is a property of the corpus, not of the method.
- `industry`'s 0.025 is 51 events and should not be quoted to three decimals.
