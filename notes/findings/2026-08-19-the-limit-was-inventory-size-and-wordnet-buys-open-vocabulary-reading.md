---
title: The limit was inventory size, not the lexical approach — WordNet takes unseen occupations from 0.000 to 0.288
date: 2026-08-19
status: provisional
arm: wordnet-proposer
refutes:
  - notes/findings/2026-08-19-the-lexical-proposer-cannot-generalise-a-long-tailed-inventory.md (mine, committed the same day)
confirms:
  - the standing rule that external standards are givens rather than things to re-derive
---

## Why this was run

Hours earlier I concluded that **a lexical proposer cannot generalise a
long-tailed inventory**, because both routes drawn from training fillers — exact
phrase and shared head — read **0.000** on unseen occupations while containment
sat at **0.582**. The finding named its own refuter: an inventory drawn from
*outside* the training data. This is that refuter, run deliberately because it
was the experiment that could embarrass the thing just committed.

WordNet's `noun.person` supersense is the right shape — **18,705 lemmas** of
people-by-role. It covers **257/494 = 52.0%** of the gold occupation vocabulary
exactly. Only the candidate set changes; training fillers still supervise the
classifier.

## What was measured

847 biographies, 4-fold, `runs/wordnet_proposer.json`.

| slice | contain | propose | clf | rank | product | measured | n |
|---|---|---|---|---|---|---|---|
| seen | 0.825 | 0.923 | 0.870 | 0.819 | 0.542 | **0.536** | 847 |
| unseen | 0.582 | **0.842** | 0.790 | 0.706 | 0.273 | **0.288** | 184 |

Against the training-induced proposer: unseen proposal **0.000 → 0.842**,
end-to-end **0.000 → 0.288**. Seen falls **0.600 → 0.536**.

## The result: my previous finding is wrong

**The limit was inventory size, not the lexical approach.** A lexical proposer
generalises perfectly well once it is not restricted to whatever supervision
happened to contain. Both registered predictions for this arm were confirmed,
including the cost: an 18,705-word inventory proposes more wrong candidates, and
the seen slice pays **−0.064** for it, most of it in the ranker (0.888 → 0.819).

The trade is strongly positive — **−0.064 on seen buys +0.288 on unseen** — and
the two slices are not the same size, but the unseen slice is the one that
represents every value the system will meet in deployment and never saw in
training.

**What this rules out is more interesting than what it rules in.** The classifier
holds at **0.790** and the ranker at **0.706** on values they were never trained
on. They did *not* secretly depend on the induced vocabulary; the split outcome
this experiment was designed to detect did not happen. Combined with the control
arm's finding that **98.6% of the rate survives renaming every value to an
invented token**, the picture is consistent and now measured from three
directions: the reader reads **position in a syntactic frame**, and its
vocabulary dependence lives *entirely* in one swappable component.

That is open-vocabulary reading. It is the first result in this arm where the
system answers correctly about a value it has never encountered in any form.

## What I got wrong, and the mechanism

The suffix arm measured two lexical routes at zero and generalised to *all*
lexical routes. Both measured routes shared a property I did not isolate: they
derive the inventory **from the supervision**. The conclusion should have been
"an inventory derived from training fillers cannot generalise", which is nearly a
tautology, rather than "a lexical proposer cannot". The word that did the damage
is *lexical*.

The guard that would have caught it in advance: the finding's own refuter section
named this exact experiment as cheap, and I wrote the strong claim into the title
anyway.

## What would refute this

The union — WordNet **plus** induced phrases — recovering the seen slice's 0.600
while keeping the unseen 0.288 would show the −0.064 is an artefact of *replacing*
the inventory rather than a genuine precision cost of a large one. That is the
obvious next run and it is the configuration that would actually ship.

## Limits

One relation, one domain, single fetch. `unseen` n=184. WordNet's person lemmas
include named individuals (`claude debussy`), which is noise the ranker has to
sort and may account for part of the seen-slice cost. No floor audit.
