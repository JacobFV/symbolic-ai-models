---
title: On novel vocabulary the learned reader is indistinguishable from a two-line rule — the lift is +0.022 [-0.072, +0.116]
date: 2026-08-19
status: provisional
arm: head-noun-floor
retracts:
  - "the learned reader reads unseen occupations at a real lift over floor" (mine, twice today: +0.266, then +0.065)
confirms:
  - the reader's lead on SEEN vocabulary is real: +0.092, 95% CI [+0.045, +0.139]
---

## Why this was run

The floor audit closed with the learned reader ahead by **+0.065** on unseen
occupation values, and named its own weakness: the floor took the *longest*
WordNet person-noun in the copular window, and **longest is not the linguistic
rule**. The head of an English noun phrase is final; *"is a British former
professional racing cyclist"* answers `cyclist` because it ends the phrase. I
wrote that a head-based floor could close a further chunk of the lift and that I
could not rule it out.

It closed all of it.

## What was measured

847 biographies, same candidate set, same copular window, no supervision of any
kind in the floors. `runs/head_noun_floor.json`.

| rule inside the copular window | seen | unseen |
|---|---|---|
| longest candidate (the audit's floor) | 0.349 | 0.223 |
| rightmost end — the NP head | 0.156 | 0.120 |
| head of the *first* copular NP only | 0.156 | 0.120 |
| **rightmost with an agentive suffix** (`-ist -er -or -ian -man -ee -ant`) | **0.444** | **0.310** |
| learned reader | 0.536 | 0.288 |

## The result: the lift on novel values is gone

**A two-line rule scores 0.310 on values the system has never seen; the learned
reader scores 0.288.** With n=184:

| | rate | 95% CI |
|---|---|---|
| suffix floor | 0.310 | [0.247, 0.380] |
| learned reader | 0.288 | [0.227, 0.357] |
| difference | **+0.022** | **[−0.072, +0.116]** |

The difference is well inside noise, and so was the **+0.065** I reported an hour
ago against the weaker floor. The honest claim is not "the floor wins" — it is
**"on novel vocabulary the learned reader is not distinguishable from a
zero-supervision positional-plus-morphological rule."**

**On seen vocabulary the reader's lead is real:** 0.536 against 0.444, **+0.092,
95% CI [+0.045, +0.139]**, n=847. That interval excludes zero comfortably.

## What this actually says about the arm

Put the session's three claims together and the picture is consistent and much
narrower than any one of them sounded:

1. The reader **reads position in a frame** — 98.6% of its rate survives renaming
   every value to an invented token.
2. It can answer about **values it has never seen** — but that capability comes
   from the **external inventory**, and a morphological rule extracts it just as
   well.
3. What learning buys is **the seen vocabulary**: +0.092 and significant, against
   +0.022 and not.

So "open-vocabulary reading" belongs to **WordNet plus two lines of morphology**,
and the learned reader is a *vocabulary* model — which is the opposite of how I
framed it twice today. That also explains the shape everything else in this arm
had: the classifier binding on companies, the proposer binding on people. Both
are vocabulary components.

## What I got wrong, and it is instructive

Both registered predictions for this arm died:

- I predicted **rightmost-head would beat longest**. It is far worse — 0.120
  against 0.223 — because a 60-character window frequently runs past the head
  into a following clause (*"is a politician and diplomat"*, *"is a cyclist who
  rode for..."*), and rightmost happily takes the later noun. "Longest" was
  accidentally robust to that; "rightmost" is the correct rule applied to an
  incorrect span.
- I predicted the **agentive suffix would add little** over the head rule,
  because a WordNet person-noun filter should already be stronger than a suffix.
  It added **0.120 → 0.310**, the largest single jump in the audit. The suffix is
  not doing lexical work — it is doing **span** work, picking the head out of a
  window whose boundary is wrong.

The generalisable half is that **three of the five floors in this arm failed for
span reasons, not for signal reasons.** Two were too tight, one too loose. A
floor's score is a joint measurement of the rule and the span it is applied to,
and this arm has now conflated the two twice.

## The paired test was named as the refuter, run, and confirms it

Unpaired intervals are the weaker comparison, and an unpaired null is not
evidence of no effect. McNemar on the item-level agreement, same items:

| slice | both | reader only | floor only | neither | McNemar p |
|---|---|---|---|---|---|
| unseen (n=184) | 34 | 19 | **23** | 108 | **0.643** |
| seen (n=847) | 290 | **164** | 86 | 307 | **<0.0001** |

**On novel vocabulary the more powerful test still does not separate them** —
19 discordant wins against 23. **On seen vocabulary the reader wins decisively**,
164 against 86. The two claims in this note both survive the stronger test, and
they survive it in opposite directions, which is the cleanest form this result
could take.

## The result this hands back is better than the one it killed

The two systems **disagree on nearly a quarter of items and fail on different
ones**:

| slice | reader | floor | oracle union | headroom | agreement |
|---|---|---|---|---|---|
| unseen | 0.288 | 0.310 | **0.413** | **+0.103** | 0.772 |
| seen | 0.536 | 0.444 | **0.638** | **+0.102** | 0.705 |

A selector that could tell which of the two to trust per item would gain
**+0.10 on both slices** — larger than any single intervention measured in this
arm, including the WordNet swap. And the complementarity is *stable across the
vocabulary split*, which says the two are not making the same kind of mistake at
different rates; they are reading differently.

That is the arm's most actionable open number, and it points somewhere specific:
**not at a better reader, and not at a better rule, but at knowing which one is
right.** The reader already emits a confidence, so the cheapest test is whether
its own confidence separates the 19 items it uniquely gets from the 23 it
uniquely misses.

## What would still refute this

A larger unseen slice. n=184 is the binding constraint on every number here — the
paired test's power at 42 discordant pairs is low, and a real effect of the size
seen on the seen slice would need roughly four times the data to show up.

A larger unseen slice would also settle it — n=184 is the binding constraint on
every number here, and the fetch that produced it is rate-limited but repeatable.

## Limits

One relation, one domain. The floors get the same candidate set as the reader,
which is the fair comparison, but it also means **every** number here inherits
WordNet's 52% exact coverage of the gold vocabulary. Unpaired intervals. No
second seed.
