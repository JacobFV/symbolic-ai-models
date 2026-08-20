---
title: The floor under open-vocabulary reading is 0.223, not zero — the lift is +0.065 and WordNet did most of the work
date: 2026-08-19
status: provisional
arm: open-vocabulary-floor
corrects:
  - notes/findings/2026-08-19-the-limit-was-inventory-size-and-wordnet-buys-open-vocabulary-reading.md (the result stands; the size of it does not)
---

## Why this was run

The WordNet arm reported the learned reader answering **0.288** on occupation
values it was never supervised on and called it open-vocabulary reading. **That
number had no floor under it.** This repo's most expensive recurring mistake is
quoting a lift over a floor that was too low — `rgt`'s "+0.587, first of
nineteen" was a floor 0.065 short — so the number does not mean anything until
something trivial has tried to buy it.

Four floors, later five, all handed **the same WordNet candidate set the reader
gets**, so the comparison is about the reasoning and not the proposer.

## What was measured

847 biographies, 4-fold. `runs/open_vocabulary_floor.json`.

| floor | seen | unseen |
|---|---|---|
| prior (most frequent training value) | 0.281 | **0.000** |
| first proposed candidate | 0.000 | 0.000 |
| longest proposed candidate | 0.032 | 0.022 |
| copular, first candidate after *is/was a* | 0.017 | 0.016 |
| **copular, longest candidate in the NP** | **0.349** | **0.223** |
| longest candidate anywhere in sentence one | 0.168 | 0.082 |
| learned reader | 0.536 | 0.288 |

## The result: the headline survives and shrinks by a factor of four

**Lift on unseen values is +0.065, not +0.266.** One regex — *"is/was a"*, take
the longest WordNet person-noun in the next 60 characters — reaches **0.223**,
which is **77%** of the learned reader's 0.288. On seen values the floor is 0.349
against 0.536, a lift of +0.187.

So the learned reader is genuinely ahead on both slices, and the previous
finding's qualitative claim stands: the system answers correctly about values it
has never encountered. **But the component that made that possible is WordNet,
not the learning.** An external standard plus a formulaic pattern is most of the
capability; the reader contributes a quarter of it on novel values, and roughly
three times as much on familiar ones (+0.187 against +0.065) — which is what
learning a vocabulary should look like, and is now measured rather than assumed.

## The floor I built first was too low, and I caught it by reading it

The first `copular` floor scored **0.016** and would have licensed a **+0.266**
lift. It was wrong: a non-greedy `{0,2}?` modifier group never consumes the
modifiers, so the floor looked for a candidate within two characters of *"is a"*
and *"is a British former professional racing cyclist"* has 34 characters of
modifier before its head. **The floor was built to fail.**

Widening the window to 60 characters and taking the longest candidate in it moved
the floor **0.016 → 0.223**, a factor of fourteen, and cut the headline lift by
0.201. Nothing about the reader changed.

The guard that worked here was not a control or a refuter — it was **reading the
floor's own code and asking what it could possibly match**. A floor that scores
near zero on a formulaic corpus is not evidence that the task is hard; it is a
bug report. Worth adding to `notes/lessons/`: *a suspiciously weak floor is a
finding about the floor.*

## Two harness checks, both clean

- `prior` scores **exactly 0.000** on the unseen slice, as it must — held-out
  values never appear in training. The vocabulary split does not leak.
- `first` scores 0.000 on both slices, which looked like a second bug and is not:
  WordNet's `noun.person` contains **surnames as common nouns** (`smith`,
  `mason`, `carter`), so the first proposed candidate in a biography is
  systematically part of the subject's own name. That is also a live source of
  ranker noise in the WordNet arm's **−0.064** seen-slice cost.

## The refuter was named, run, and did not fire

I wrote that a floor taking the longest person-noun anywhere in sentence one
might erase the lift entirely, and that I would not bet against it. It reaches
**0.082** on unseen values — well below the copular floor's 0.223 and below a
third of the reader's 0.288. The lift survives.

It also says something the audit did not set out to measure. Dropping the
copular pattern and keeping everything else — same inventory, same sentence,
same "take the longest" rule — costs **0.223 → 0.082**, nearly two thirds. So
most of what the cheap floor knows is **where in the clause to look**, not which
words are occupations. That is the third independent measurement pointing at the
same thing: renaming survival at 98.6%, the classifier holding at 0.790 on
unseen values, and now a floor that collapses when position is removed. **The
signal in this task is positional.**

## What would refute this

A floor that keeps the copular position and improves the choice within it — for
instance preferring the head noun of the NP by suffix rather than by length. On
present evidence that could plausibly close a further chunk of the +0.065, and
nothing here rules it out.

## Limits

One relation, one domain, unseen n=184. The +0.065 lift is roughly the width of
what a second fetch could move; no confidence interval is computed here and it
should be before this is promoted.
