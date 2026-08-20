---
title: Four representations, none worth half a point — the limit is the model class, not the features
date: 2026-08-19
status: measured
arm: representation
---

The lexical result said the ceiling is not about knowing which words are
triggers, and pointed at **structure**: whether a sentence states the relation
*about this subject*, and which mention fills the slot. This tests that with the
cheapest structural features available — the relative order of **subject,
trigger and candidate**, whether a trigger lies between them, mention distance,
and same-clause — using the subject the ABI has carried since `Reader.run(query=)`
was wired, and no parser, because none is installed and none is being added.

| arm | coverage | correct | precision | k/n |
|---|---|---|---|---|
| baseline (frames) | 0.306 | 0.116 | 0.378 | 207/1788 |
| + argument structure | 0.306 | **0.119** | 0.389 | 213/1788 |

**+0.003. Six articles in 1,788.** Predicted 0.01–0.03 and that it would beat the
lexical grouping. It came in **below** it.

## Four representations, and the pattern is the result

| what was added | on `parent` |
|---|---|
| WordNet supersenses (external, category) | **0.000** |
| distributional clusters (corpus, context) | **−0.007** |
| label-aware groups (corpus, *ideal* lexical) | **+0.005** |
| cheap argument structure (corpus, order) | **+0.003** |

Four qualitatively different feature families — external and internal, lexical
and structural, one of them **supervised with the labels themselves and therefore
as good as a lexical feature can be on this corpus**. None is worth half a point.

That is no longer a statement about any feature. **It is a statement about the
model class.** A linear model over sparse indicator features has a fixed way of
using evidence: each feature votes, the votes add. Adding a feature that encodes
a *relationship* — this word is a trigger, that mention is the subject, the
trigger sits between them — gives it three more votes, not a way to condition one
on another. What the task needs is for the trigger's identity to *select* which
positional evidence matters, and no bag of indicators expresses that at any size.

## Where the loss actually sits

Of 1,788 articles the reader answers **547** and is right on **207**. Against a
containment ceiling of 0.594:

- it **fails to recognise** roughly half the sentences that state the relation
  (coverage 0.306 against a reachable 0.594);
- and when it does recognise one it picks the right mention **38%** of the time.

Both halves resisted all four interventions, which is what makes the model-class
reading more likely than a missing-feature one.

## What this settles for the fork

Twelve interventions have now been closed on this reader — eight in the earlier
arms, four here. The case for the excluded component is now as strong as it can
be made **from inside the scope**, and it rests on something more specific than
"neural is better":

> The missing thing is a model that can make one piece of evidence condition the
> use of another. Every representation tried here hands the linear model more
> indicators, and the measured return on the fourth is the same as on the first.

That is a claim about **composition of evidence**, not about vocabulary or
pretraining, and it is the sharpest version of the fork this session has reached.

## What would have refuted it

Argument structure buying materially more than lexis — the "it is structural, not
lexical" reading would then have been right and the fix would be inside the
current model class. It bought less.

## Honest limits

- **All four measured on `parent` only.** `headquarters` responded to frames
  earlier (+33% on the ranker), so a relation with a canonical frame may behave
  differently, and the model-class claim is not tested there.
- **+0.003 and +0.005 are positive.** The claim is that they are far too small to
  be the ceiling's cause, not that features do nothing.
