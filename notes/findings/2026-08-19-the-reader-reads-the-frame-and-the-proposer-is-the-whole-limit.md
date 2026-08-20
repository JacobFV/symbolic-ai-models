---
title: The reader reads the frame — 98.6% survives renaming — and the proposer is the entire limit on generalising
date: 2026-08-19
status: provisional
arm: occupation-control
confirms:
  - all three registered predictions, including the mechanism attribution
supersedes:
  - the "closed vocabulary" caveat attached to occupation's 0.615
---

## Why this was run

The second-domain arm measured the learned reader reading `occupation` at
**0.615** end-to-end and recorded it `status: provisional` for one stated reason:
the proposer is `PhraseMentions.induce`d from training fillers, so a
closed-vocabulary lookup was a live alternative to reading, and **the renaming
control had not been run**. That control has killed a headline here before —
ensemble-001's 1.14 bits went to **0.038** under permutation.

Two controls, chosen because they ask different questions and the registered
prediction was that they would **disagree**:

- **renamed** — every occupation string replaced by an invented token,
  consistently across intro text, gold and training fillers. Vocabulary
  destroyed, syntactic frame untouched.
- **unseen** — the *vocabulary* split four ways; test only on articles whose
  every gold occupation is absent from training. Nothing renamed, frame
  untouched.

## What was measured

847 biographies, 4-fold, `runs/occupation_control.json`.

| arm | contain | propose | clf | rank | product | measured | n |
|---|---|---|---|---|---|---|---|
| base | 0.825 | 0.927 | 0.897 | 0.888 | 0.609 | **0.600** | 847 |
| renamed | 0.806 | 0.943 | 0.883 | 0.894 | 0.601 | **0.591** | 847 |
| unseen | 0.582 | **0.000** | 0.000 | 0.000 | 0.000 | **0.000** | 184 |

## The result

**Renaming retains 98.6%.** 0.591 against 0.600, with every one of the four
factors flat. This is the strongest renaming survival in the repo's history and
it is the opposite of what the control usually finds here. The reader is not
matching lexemes — it is reading the **position in a syntactic frame**, and the
frame does not care that a bishop is now a `kelvor`.

The closed-vocabulary alternative also turned out to be **the wrong worry on its
own terms**: there are **494 distinct occupation values across 847 articles**,
0.583 per article. That is not a small closed set.

**The unseen-value holdout collapses to exactly 0.000, and the collapse lands
precisely where it was predicted to.** Proposal is **0.000** while **containment
stays at 0.582** — the answer is in the text five times in nine, and the reader
never gets to see it, because a proposer induced from training fillers cannot
offer a filler it has never encountered. The classifier and the ranker are not
implicated; they are never reached.

## What this means, and it is not a caveat

The two controls disagreeing *is* the finding. `occupation`'s 0.615 is **genuine
frame-reading**, and its inability to generalise to a new value is **not a
property of the reader at all** — it is one named, measured, replaceable
component returning zero.

That converts a vague limit into an engineering target with a computable ceiling.
On the unseen slice containment is 0.582 and the downstream factors run ~0.89
each, so a proposer that could offer unseen noun phrases would put the ceiling
near **0.582 × 0.89 × 0.89 ≈ 0.46** on exactly the slice that currently reads
zero. That is the single largest identified headroom in the reading arm, and it
sits in the component the four-factor decomposition was built to expose.

It also sharpens yesterday's correction. The classifier was never the binding
factor; off-corpus it was **containment**, and here, for unseen values, it is
**proposal**. Three domains of evidence now say the same thing: **the components
outside the original three-factor decomposition are where the headroom is.**

## What would refute this

A generic noun-phrase proposer that raises proposal on the unseen slice but
leaves the end-to-end rate near zero — which would mean the classifier and ranker
silently depended on the induced vocabulary too, and the ceiling above is
arithmetic rather than achievable. That is the next experiment and it is cheap.

## Limits

Base here reads **0.600**, not the arm's 0.615, because this run trains only on
articles carrying occupation gold while the decomposition trained on all 850;
a slightly smaller supervision pool. The gap is 0.015 and does not touch any
conclusion. Single domain, single relation, no floor audit on the unseen slice.
