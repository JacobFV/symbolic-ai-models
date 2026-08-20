---
title: The inventory trade is real and must be chosen — the crossover is 18.2% novel values
date: 2026-08-19
status: provisional
arm: union-proposer
refutes:
  - my registered prediction that the union would recover the seen slice
---

## Why this was run

Swapping the proposer's inventory to WordNet bought **+0.288** on unseen
occupations and cost **−0.064** on seen ones. That finding named its own refuter:
the cost might be an artefact of *replacing* the training-induced phrases rather
than a genuine precision cost of a large inventory. The union settles it, and it
is also the configuration anyone would actually deploy — there is no obvious
reason to discard what supervision taught in order to gain what the standard
knows.

**Registered prediction:** the union recovers most of the seen slice (≥ 0.57)
while keeping the unseen near 0.288, because `PhraseMentions` matches
longest-first so an exact gold phrase should still beat a WordNet fragment.

## What was measured

847 biographies, 4-fold, same reader, same folds. `runs/union_proposer.json`.

| proposer | seen | unseen |
|---|---|---|
| training-induced | **0.600** | 0.000 |
| WordNet `noun.person` | 0.536 | **0.288** |
| union | 0.547 | 0.277 |

## The result: refuted, and the mechanism is clean

**The union does not rescue the seen slice.** 0.547 against a predicted ≥ 0.57.
Adding the training phrases *back* to WordNet buys only **+0.011** over WordNet
alone (0.536 → 0.547), which locates the damage precisely: it is done by
**WordNet's presence in the candidate set**, not by the absence of the induced
phrases. The ranker carries it — 0.888 induced, 0.819 WordNet, **0.806** union —
because 18,705 person-nouns put more plausible wrong candidates in front of it in
every sentence.

So the trade is **real and has to be chosen**, not engineered away. That is a
more useful answer than a free win would have been, because it makes the choice
explicit and it makes it computable.

## The decision rule, and it is one number

Let `f` be the share of encountered values that the system has never been
supervised on. Setting the two arms equal gives a crossover at

    f* = 0.064 / (0.064 + 0.288) = **0.182**

| f novel | induced | WordNet | union | best |
|---|---|---|---|---|
| 0.05 | 0.570 | 0.524 | 0.534 | induced |
| 0.10 | 0.540 | 0.511 | 0.520 | induced |
| 0.182 | 0.491 | 0.491 | 0.498 | union |
| 0.217 | 0.470 | 0.482 | 0.488 | union |
| 0.30 | 0.420 | 0.462 | 0.466 | union |
| 0.50 | 0.300 | 0.412 | 0.412 | WordNet |

**Below 18.2% novel values, keep the training-induced inventory. Above it, take
the external one** — and in the band just above, the union is best by a small
margin, which is the only place its +0.011 earns anything.

On this corpus the novel share is **0.217**, just past the crossover, so the
union is the right configuration here — by 0.018 over induced, which is a thin
margin honestly reported rather than a headline.

## Why this matters beyond one relation

This is the first place in the arm where a component choice is decided by a
**measured property of the deployment** rather than by a benchmark ranking. The
novel-value share is observable without labels — it is how often a proposed
candidate falls outside the training inventory — so the rule can be evaluated at
run time on a corpus nobody has annotated.

It also reframes the north star for this component. `f` is not a constant: a
system reading a fixed domain forever sees `f → 0` and should keep its induced
inventory; a system reading open text sees `f` stay high and should pay the
ranker cost. **The right proposer is a function of the corpus, not of the
architecture.**

## Limits

One relation, one domain, n=184 on the unseen slice. The crossover is a
**two-point linear fit** — exactly the shape this repo has flagged as
untrustworthy in its own status notes — and it assumes the seen and unseen rates
are constant as the mix changes, which is not tested. No floor audit. The
0.018 margin at f=0.217 is well inside anything a second fetch would move.
