---
title: Distinguishable is not identifiable
date: 2026-08-19
status: lesson
---

## The mistake

Asking whether a reader could separate two roles, I measured whether their
observations **differ**. They differed in 93.3% of cases, and the script printed
*REACHABLE — the empty cell is unsolved rather than closed*.

The two things are not the same:

- **Distinguishable** — the observations are not identical. A property of a
  *pair*.
- **Identifiable** — there is a consistent rule assigning the right role. A
  property of the *mapping*, across the whole corpus.

Anything with incidental variation is distinguishable. Here the observations
differed by node degree in a randomly generated road network: real variation,
carrying no information about which region was the depot. The rule "highest
degree wins" scored 33.3% against 28.5% chance.

## What it cost

Nearly a published conclusion in the wrong direction, and — worse — a redirect of
the research front. "Reachable" says *build a better content-free reader*;
"closed" says *the lexical resource is now a necessity*. Those are different
quarters of work.

## The guard

**When the question is "can something be inferred", test the mapping, not the
pair.** Two tests, in order of strength:

1. **Propose the rule and score it against chance.** Cheap, and it catches
   features that vary without informing. Quote the chance rate beside it — 33.3%
   looks like a signal until 28.5% is next to it.
2. **Test whether observation → answer is a function at all.** Collect
   (observation, label) pairs across the corpus and count observations carrying
   more than one label. This bounds *every possible* deterministic reader at
   once, rather than one proposed rule at a time, and it is the version worth
   reaching for — it turned 93.3% "distinguishable" into 21/21 role-slots
   ambiguous.

The second test is architecture-independent, which is what makes it a proof
rather than an experiment. Reach for it whenever the conclusion would be "no
model can do this".

## Related

- [[2026-08-19-the-empty-cell-is-closed-and-distinguishable-is-not-identifiable]]
- Same family as the slice inversions: a statistic computed over the wrong
  population, or here the wrong object, answers a question nobody asked.
