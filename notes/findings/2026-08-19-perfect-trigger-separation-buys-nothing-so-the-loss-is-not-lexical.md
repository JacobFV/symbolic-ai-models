---
title: Perfect trigger separation buys 0.005 — so the loss is not lexical, and the fork's premise needs revising
date: 2026-08-19
status: measured
arm: representation
---

The clustering finding ended on a falsifiable claim: *any representation induced
from this corpus alone will fail the same way.* Its failure was specific —
distributional similarity merged `subsidiary`, `division` and `owned` with `is`,
`by` and `company`, because in this genre they share contexts by construction.

So this induces a grouping that **cannot** fail that way. Words are scored by
smoothed PMI with the **positive class** rather than by their contexts, bucketed
into eight, computed **per fold on training sentences only**.

## The separation is exactly right

| word | bucket (0–7) |
|---|---|
| `subsidiary` | **7** |
| `division`, `unit`, `owned`, `acquired` | **6** |
| `is` | 2 |
| `company` | 1 |
| `the` | 1 |

Every trigger in the top two buckets, every piece of boilerplate at the bottom.
This is precisely the separation distributional clustering could not make, and it
is as clean as any representation could be on this corpus.

## And it buys nothing

| arm | coverage | correct | precision | k/n |
|---|---|---|---|---|
| baseline (frames) | 0.306 | 0.116 | 0.378 | 207/1788 |
| + label groups | 0.323 | **0.121** | 0.374 | 216/1788 |

**+0.005, nine articles in 1,788, z ≈ 0.46.** Coverage rises slightly, precision
does not move.

Predicted both halves — clean separation, little gain — and the second half is
the one that matters, because it removes an explanation.

## What it removes, and what it does to the fork

The clustering result could be dismissed as *a bad induction*: cluster better and
the representation would pay. **That escape is now closed.** The induction here is
not merely better, it is ideal for the purpose — it uses the labels to find
exactly the distinction the task needs — and it is worth half a point.

The reason is visible in an earlier measurement. Content-word triggers have a
**mean count of 4.40** at this corpus size. A grouping helps by letting a rare
trigger borrow a common one's weight, and there are not enough genuinely rare
triggers carrying enough mass for that to matter. **The long tail of triggers is
not where the loss is.**

Which revises the framing of the previous finding. *"What is needed is a
representation learned outside this corpus"* assumed the missing thing is
**lexical** — better knowledge of which words signal ownership. Perfect lexical
knowledge, handed to the reader, is worth 0.005. So:

> The reader's ceiling is not caused by not knowing which words are triggers.

What is left is **structure**: given that a sentence contains `subsidiary`,
deciding whether it states the relation *about this subject* and *which mention
fills the slot* is not a lexical question. The classifier is at 0.395 recall and
the ranker at 0.533 with the trigger words fully available to both.

That is a sharper hypothesis than "representation" and it points somewhere
different — at whatever encodes *argument structure*, which a bag of features
does not have at all, rather than at a better vocabulary.

## What would have refuted it

The grouping buying a real gain — the representation hypothesis would then have
been right in its lexical form, and the cheap version of it would have worked.
It bought nine articles.

## Honest limits

- **One relation, one corpus.** `country` and `headquarters` may distribute their
  trigger mass differently; `country` in particular has no lexical trigger at all.
- **+0.005 is not zero.** It is a small positive that a larger corpus might grow;
  the claim is that it is far too small to be the ceiling's cause, not that it is
  nothing.
