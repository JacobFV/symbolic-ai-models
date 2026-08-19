---
title: A feature picked against a hand-listed negative class
date: 2026-08-19
status: lesson
---

## What happened

Choosing WordNet hypernym ancestors to mark "this verb ends a relation", I took
the ancestors **reached by my stale verbs and not by my fifteen relation verbs**.
That looked like a controlled choice — a positive class and a negative class,
both explicit.

The eight ancestors it produced fire on **52.2% of real English**. Two of them
account for 95% of that: `change` at 6,899 token fires and `transfer` at 2,191,
against `leave` 315, `end` 271, `remove` 91, `exit` 12, `deprive` 5. `change`
sits near the root of WordNet's verb hierarchy, so *increase*, *add*, *process*
and *update* all reach it — and none of those was in my fifteen.

Held out, recall fell from **0.86 to 0.42**. A fifteen-item negative class
inflated it about twofold.

## The mechanism

A hand-listed negative class contains the things you thought of. A feature's
false-positive rate is decided by the things you did not — and for a taxonomic
feature that is a function of **depth**, which is not visible from any small
list. The list looks like a control because it has two classes; what it lacks is
*scale*, and scale is exactly what a false-positive rate is made of.

## The guard

**Measure a candidate feature's firing rate on a large unlabelled population
before adopting it.** It needs no labels — a rate is enough — and it is the
cheapest measurement in this whole family. Ten thousand real sentences took
seconds and said something fifteen hand-picked verbs could not.

For a taxonomy specifically: **prefer deep ancestors, and check the depth by
firing rate rather than by intuition.** `discontinue` fired five times in 10,650
sentences; `change` fired 6,899. They look equally reasonable written down.

The same shape has now appeared three times today:

- a cue list that was 85% false positives on real prose, twice, with a different
  dominant error in each genre;
- ancestors chosen against fifteen verbs, wrong by 100× at the sentence level.

Each was caught by the same move: **run it on a corpus nobody here wrote.**

## Related

- [[2026-08-19-a-detector-experiment-needs-a-baseline-arm-for-every-check]] — the
  same error at the level of an arm rather than a feature.
- [[2026-08-19-a-verification-that-uses-the-mechanisms-own-predicate-decides-the-experiment]]
