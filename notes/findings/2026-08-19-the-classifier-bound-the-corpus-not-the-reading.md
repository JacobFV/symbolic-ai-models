---
title: The classifier bound the corpus, not the reading — off-corpus, containment binds and the reader reads at 0.615
date: 2026-08-19
status: provisional
arm: second-domain-people
refutes:
  - "the classifier is the binding factor in reading" (7/7 on companies, 1/4 here)
  - my own registered prediction that birthplace would have the highest containment
confirms:
  - "reading factors as containment x proposal x classifier x ranker, and the product reproduces the measured rate"
---

## Why this was run

Every number in the reading arm came from **company intros**: seven relations, one
register, one corpus. Three claims were stated generally and none had ever been
asked a question outside the corpus that produced them. This repo has recorded
five claims that died because a number fitted on one sample was quoted as a law,
so the arm's own generality was the largest unexamined assumption in it.

Same measurement, unchanged code path, on **850 biographies** — different register
(a life, not a corporate description), different relation family, same gold source
(Wikidata), so the comparison is about the text and not about the annotation.
Predictions were registered in `notes/autonomy/predictions.jsonl` **before the
fetch finished**.

## What was measured

`data/artifacts/people_relations.jsonl`, 850 people, 4-fold, both proposers.
`runs/people_decomposition.json`.

| relation | proposer | contain | propose | clf | rank | product | measured | n |
|---|---|---|---|---|---|---|---|---|
| birthplace | Capitalised | 0.223 | 0.794 | 0.327 | 0.816 | 0.047 | 0.046 | 846 |
| birthplace | Phrase | 0.223 | 0.847 | 0.319 | 0.804 | 0.048 | 0.048 | 846 |
| occupation | Capitalised | 0.825 | **0.000** | 0.000 | 0.000 | 0.000 | 0.000 | 847 |
| occupation | Phrase | 0.825 | 0.930 | 0.911 | 0.895 | 0.626 | **0.615** | 847 |
| employer | Capitalised | 0.592 | 0.804 | 0.513 | 0.869 | 0.212 | 0.184 | 250 |
| employer | Phrase | 0.592 | 0.635 | 0.511 | 0.792 | 0.152 | 0.136 | 250 |
| educated_at | Capitalised | 0.119 | 0.807 | 0.196 | 1.000 | 0.019 | 0.019 | 479 |
| educated_at | Phrase | 0.119 | 0.684 | 0.128 | 1.000 | 0.010 | 0.010 | 479 |

## The three claims, off-corpus

**1. The decomposition survives — this is the one that generalises.** Product
against measured: **max gap 0.028, mean 0.007**, against 0.019 max on companies.
Four factors multiplied reproduce end-to-end reading in a domain they were never
fitted on. The identity is a property of the reader, not of the corpus.

**2. "The classifier is the binding factor" was a fact about companies.**
It bound **7/7** there and **1/4** here. **Containment** binds in three of four —
the gold value is simply not in the text. This is the claim to withdraw: the
arm's most-repeated sentence described the corpus that produced it, and the
twelve failed feature interventions were failing against a ceiling that was never
the classifier's to raise in the general case.

**3. `occupation` reads 0.000 under a capitalised proposer** — proposal exactly
**0.000**, the same structural zero `industry` had, for the same reason (its
values are lowercase common nouns; measured at **0.8% capitalised** in the fetch).
Confirmed as predicted, and it is now the second independent instance, which
makes it a property of the proposer rather than an accident of one relation.

**Refuted, mine:** I predicted `birthplace` would have the *highest* containment,
because a birth clause is near-obligatory in a biography. It has the **lowest**
of the three proper-noun relations at 0.223, and `educated_at` is lower still at
0.119. The mechanism: Wikidata records a birthplace at municipality granularity
while the prose names a country or a region, so the two disagree on *which*
correct answer to state. The near-obligatory clause is there; the annotation is
not pointing at it.

## The finding under the finding

**0.615.** That is `occupation` end-to-end, and it is **2.7× the best number the
company arm ever produced** (headquarters, 0.230). The company relations did not
look hard because reading is hard. They looked hard because their containment ran
0.241–0.592 — the answer was in the text half the time — and *every* factor
downstream was being multiplied by that. Where containment is high (0.825) the
same reader, unchanged, reads at 0.615 with a classifier at 0.911.

So the reading arm's ceiling was **annotation–text mismatch**, not capability.
That reframes the arm's headline claim and it reframes the critical path: the
lever with the most headroom is not a better classifier, it is **choosing
relations whose gold the prose actually states** — which the containment screen
already measures for free, before anything is fitted.

## What would refute this

A third domain in which the classifier binds again in the majority, which would
make companies and biographies the two poles of a spectrum rather than
biographies the correction. Also: `occupation`'s 0.615 leans on a phrase proposer
induced from training fillers, so a closed-vocabulary effect is a live
alternative — the values are a small set ofoccupational categories, and the renaming
control that killed earlier claims has not been run on it.

## Limits

Single fetch, no renaming control, no floor audit, `employer` at n=250. `status:
provisional` is meant literally: this is a scouting number that contradicts a
headline, which makes it worth recording immediately and worth attacking before
it is promoted.
