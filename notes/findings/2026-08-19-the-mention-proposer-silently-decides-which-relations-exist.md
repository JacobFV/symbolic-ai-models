---
title: The mention proposer silently decides which relations are answerable — and no screening statistic survived
date: 2026-08-19
status: measured
arm: relation-readability
---

`headquarters` reads at 0.219 and `parent` at 0.119 with the same reader, corpus
and supervision, and they differ measurably *before any reading* — top-5 frame
share 0.714 against 0.436. If that generalised it would be a **screening
statistic**: a way to tell from the corpus alone whether a relation is worth
building an extractor for.

Five relations were fetched for the same 2,502 articles to fit it — `parent`
(P749), `country` (P17), `headquarters` (P159), `founder` (P112), `industry`
(P452). **Two of the five turned out to be unmeasurable, and finding out why is
worth more than the fit.**

## What the five actually did

| relation | gold | containment | top-5 | mean count | coverage | correct |
|---|---|---|---|---|---|---|
| `parent` | 1,788 | 0.592 | 0.436 | 4.49 | 0.327 | 0.119 |
| `country` | 2,349 | 0.579 | 0.414 | 3.52 | 0.408 | 0.169 |
| `headquarters` | 2,394 | 0.551 | 0.714 | 5.53 | 0.377 | **0.219** |
| `founder` | 1,017 | 0.424 | 0.368 | 2.06 | 0.206 | 0.102 |
| `industry` | 2,058 | 0.241 | 1.000 | 1.33 | 0.105 | **0.000** |

## Two invalid rows, two different silent failures

**`founder` first read 0.000** — and it is not a hard relation. `supervise_distant`
labels only the relations named in `real_text_reader.RELS`, which was
`("parent", "headquarters", "country")`. A relation absent from that tuple is
never supervised, trains on nothing, and reports zero with no error. Adding it
took `founder` to 0.102.

**`industry` reads 0.000 and cannot be fixed that way.** Its gold values are
`automotive industry`, `video game industry`, `financial services`, `retail` —
**97.9% of them start with a lowercase letter**, against 99.9% of `founder`
values that do not. `CapitalisedMentions` proposes runs of capitalised words, so
an `industry` value **can never be a candidate**. The reader is structurally
incapable of answering the relation and says so by returning nothing.

That is the finding worth keeping:

> **The mention proposer silently decides which relations exist.** It was chosen
> as knowledge of English — proper nouns are capitalised — and it quietly
> restricts the system to relations whose values are proper nouns. Nothing
> errors, nothing warns, and the failure is indistinguishable from a hard
> relation.

This is the same shape as the lesson notes on silent property failures: a
component chosen for one good reason bounds something nobody was tracking. An
`industry`-shaped relation needs a different proposer — noun-phrase chunks, not
capitalised runs — and no amount of reader work substitutes.

## And the screening statistic did not survive

Over the four valid relations:

| statistic | r with `correct` |
|---|---|
| containment | −0.201 |
| mean frame count | +0.508 |
| top-5 frame share | +0.788 |

Top-5 share is the best of them and it is **four points with `parent` as an
outlier** — high frame concentration would predict `parent` reads better than
`country`, and it reads worse. Over five points (including the invalid rows) the
same statistic reads −0.470, which is how much two broken rows move a
correlation on this sample size.

**Four points do not establish a predictor**, and this note does not claim one.
What it establishes is that two of five relations were unmeasurable for reasons
that had nothing to do with difficulty, which is the more useful half.

## What would have refuted it

`industry` values being capitalised — the 0.000 would then have been about the
relation rather than the proposer, and the structural claim would be wrong. They
are lowercase 97.9% of the time.
