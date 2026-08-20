---
title: Supervision must go through the proposer — acting on the diagnostic pays 3.9x, and only when both halves move
date: 2026-08-19
status: measured
arm: relation-readability
---

The lexicon-gap diagnostic flagged `industry` at **0.416** and called every other
relation a model problem. A triage rule is worth having only if acting on it pays,
so this acts on it — with `parent` as the control, since no alias is induced for
it and nothing should change.

Two changes, both induced from the gold alone:

1. **The proposer normalises.** `PhraseMentions(alias_heads=True)` strips the head
   noun the gold values share (`… industry`) and maps the remainder back, so
   *automotive company* proposes the span and reports the canonical `automotive
   industry`.
2. **Supervision goes through the proposer.** A sentence is labelled when **the
   proposer can produce a gold value from it**, rather than when it contains the
   gold string.

| relation | arm | coverage | correct | precision | k/n |
|---|---|---|---|---|---|
| `industry` | phrase + literal supervision | 0.081 | 0.025 | 0.307 | 51/2058 |
| | alias proposer + literal supervision | 0.059 | **0.020** | 0.336 | 41/2058 |
| | **alias proposer + proposer supervision** | 0.235 | **0.097** | 0.413 | **200/2058** |
| `parent` | phrase + literal supervision | 0.283 | 0.128 | 0.451 | 228/1788 |
| | alias proposer + literal supervision | 0.283 | 0.128 | 0.451 | 228/1788 |
| | alias proposer + proposer supervision | 0.276 | **0.129** | 0.468 | 231/1788 |

## The two halves are useless apart

**The alias proposer alone makes `industry` worse** — 0.025 → 0.020. It proposes
more candidates, and the classifier was trained on sentences selected by literal
containment, so the new candidates arrive in sentences nothing taught it to
label. Extra candidates without extra supervision is extra noise.

Together they give **0.097, a 3.9x improvement**, with coverage 0.081 → 0.235 and
precision 0.307 → 0.413. Both columns up, which is the shape of a real fix rather
than a coverage/precision trade.

`parent` is flat — 0.128, 0.128, 0.129 — exactly as predicted, because no head is
shared by company names so no alias is induced. **The change is not a general
accuracy knob**, which is the control that makes the `industry` number mean
something.

## The general principle

> **A sentence that cannot yield the answer is a bad positive; a sentence that can
> and is unlabelled is a wasted one.** Distant supervision by containment gets
> both wrong whenever the proposer and the gold disagree about what the answer
> looks like.

Aligning them is free — it uses the proposer that already exists — and it is not
specific to `industry`. Any relation whose values are stated in a normalised form
different from the gold's has the same misalignment, and the lexicon-gap
diagnostic is how you find them.

## The full trajectory on one relation

| stage | `industry` | what changed |
|---|---|---|
| capitalised proposer | **0.000** | values are lowercase; no candidate can be produced |
| phrase proposer | 0.025 | the inventory and its productive suffix |
| **alias + proposer supervision** | **0.097** | the derived form, and training that can see it |

From structurally impossible to **0.097** in three steps, each one identified by a
measurement rather than guessed: the four-factor decomposition found the
proposer at 0.006, the lexicon gap found the derivation at 0.416, and this found
the misalignment between the two.

`industry` is still the weakest relation measured and 0.097 is not a good number.
The claim is about the method, not the score.

## What would have refuted it

`parent` moving. The change would then have been a general knob and the
diagnostic's specificity worthless. It moved by three articles in 1,788.
