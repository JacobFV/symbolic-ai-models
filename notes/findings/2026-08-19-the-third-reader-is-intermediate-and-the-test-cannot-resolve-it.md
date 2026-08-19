---
title: The third reader is intermediate, the test cannot resolve it — and character shape matches vocabulary on one relation
date: 2026-08-19
status: measured
arm: multi-hop-world
---

The clumping result's last open control is a **third reader**: the perceptron and
logistic variants share features, proposer and supervision, so they are not
independent evidence that *learned* readers are uncorrelated. A fame prior failed
the competence bar (0.000 on two relations, nothing to correlate). This builds the
other option the queue named.

`LearnedSpanReader(base_features=False, extra_features=char_features)` shares the
mention proposer and the distant supervision and has **not one lexical feature**:
character 3- and 4-grams of the sentence with names, numbers and dates replaced by
sentinel characters, at the classifier *and* at the ranker.

## The result is intermediate, and honestly undetermined

| relation | reader | accuracy | odds ratio | χ² p | both-correct pairs |
|---|---|---|---|---|---|
| `headquarters` | learned (words) | 0.212 | 1.24 | 0.595 | 17 |
| `headquarters` | **char (no words)** | **0.212** | **1.76** | **0.068** | 22 |
| `headquarters` | hand | 0.198 | 2.43 | 0.006 | 20 |
| `parent` | char | 0.077 | 1.42 | 0.756 | 4 |
| `country` | char | 0.147 | 6.27 | <0.001 | 16 |

Only the `headquarters` row is usable. `parent` at 0.077 falls below the stated
competence bar of ~0.15 and yields four both-correct pairs; `country` is the
relation with **76% answer sharing** between neighbours and is confounded for
every reader.

On that one usable row the character reader lands **between** the word-based
learned reader (1.24) and the patterns (2.43), at **p = 0.068** — the edge of
detection with 22 events. **The test cannot resolve it.** It neither confirms nor
refutes "learned readers do not clump"; it says the question needs more
both-correct pairs than 415 chains at these accuracies can supply.

That is a smaller claim than either possible headline, and it is what the data
supports.

## The side result is cleaner than the one it was built for

**On `headquarters` the character reader matches the word reader exactly: 0.212
against 0.212**, with no lexical feature of any kind. The vocabulary contributes
nothing over the *shape* of the sentence around its mentions — *"…, headquartered
in ␁"* is recoverable from characters and sentinels alone.

It does **not** transfer: on `parent` the word reader is 0.092 against the
character reader's 0.077, so lexis is carrying about a fifth of that relation.
The difference lines up with the frame statistics measured earlier —
`headquarters` has the more canonical frame (top-5 share 0.274 against `parent`'s
0.179), and a canonical frame is exactly what a character n-gram can capture
without knowing a single word.

## What this leaves

The queue entry stays open with the gap **narrowed and re-specified**. What is
needed is not a more different reader — that has now been tried twice, once too
weak and once undetermined — but **more both-correct pairs**, which means either
a reader well above 0.2 on a clean relation or a corpus with several thousand
chains. Both are larger jobs than a feature swap.

## What would have refuted the surviving claim

The character reader clumping at the patterns' level (≈2.4, p<0.01) on
`headquarters`. That would have said the hand/learned split is not about being
learned at all, and that whatever produces clumping survives replacing every
lexical feature. It came in at 1.76 with p = 0.068, which points that way without
reaching it.
