---
title: A closed-class feature transfers; an open-class lexicon does not
date: 2026-08-19
status: measured
arm: verb-class-staleness
---

## The floor is liftable, in one domain

Continuing the WordNet line, two more corrections made the verb gate work — and
then made it clear it works only where it was tuned.

**Sense dominance, not sense priority.** First-sense selection fires on `dated`
(WordNet's first sense of *date* is the romantic one, whose chain reaches
*leave*), which appears in every solvency filing sentence and cost that surface
1.000 → 0.650. Requiring the transition reading on **more than 20% of the
lemma's senses** removes it: `dated` sits at 0.20 while every genuine transition
verb measured sits at 0.27 or above and every relation verb at 0.00.

*The 0.2 was set by one false positive and is labelled as fitted. What makes it
defensible is that it costs nothing: held-out recall is 0.33 at that threshold
and 0.33 for the first-sense rule it replaces.*

With that, on solvency:

| gate | clean | owns **uncued** | owns+filing uncued |
|---|---:|---:|---:|
| none | 1.000 | 0.475 | 0.433 |
| **verb (deep roots, sense-dominant)** | **1.000** | **1.000** | 0.492 |

**The declared floor of the day goes 0.475 → 1.000 at no cost on the clean
surface** — the first thing that moves that arm by *reading* rather than by
refusing. The remaining arm stays at 0.492 because its distractor is not stale at
all: *"An unaudited memorandum from sub_0 on 31 May shows 387.57 USD"* is a claim
that was never true, not one that was withdrawn. Different failure, and it belongs
to the insensitivity response.

## And then it destroys the other two domains

| domain, honest surface | no gate | verb gate |
|---|---:|---:|
| solvency, uncued owns | 0.475 | **1.000** |
| scheduling, hard machine | 0.767 | 0.675 |
| **flood, hard distractors** | **0.589** | **0.014** |

**`can` is what kills flood.** WordNet has it as a verb — *"terminate the
employment of"* — so one of its two senses reaches `remove` and the fraction is
0.5. It appears **90 times in thirty flood documents**. `empty`, `complete` and
`laden` fail the same way.

That is the limit of sense dominance, stated precisely: **it protects against a
*rare* wrong sense and not against a *low-sense-count* word one of whose readings
happens to be a transition.** `dated` is 1 of 5 and is caught; `can` is 1 of 2 and
is not.

The damage also scales with **claim density**. Flood realises a claim in almost
every sentence, so deleting 13% of them destroys the world; solvency's ownership
paragraph survives losing one.

## The contrast is the finding

| | `stale_by_cancellation` | `stale_by_verb` |
|---|---|---|
| vocabulary | **closed-class**, 11 cues | **open-class**, 11,529 lemmas |
| real prose firing | **0.004** | **0.156** |
| across the three generated surfaces | **byte-identical** | +0.525 / −0.092 / **−0.575** |

> **A closed-class feature transfers; an open-class lexicon does not.** Its
> false-positive rate grows with the vocabulary it draws on, and the damage a
> *deletion* gate does grows with the claim density of the surface it is pointed
> at. The two multiply.

`stale_by_verb` is kept, documented with every number, and **wired into no default
path**. A dead end that is not written down gets re-derived; one that is written
down as a component gets used.

## A tooling note worth keeping

`uv add nltk` followed by `uv remove nltk` **silently dropped the `solvers`
extra**, taking `z3-solver` and `clingo` out of the environment — the SMT and ASP
kernels. `pyproject.toml` was never modified, so nothing was committed wrong, and
`uv sync --extra solvers` restored it. A plain `uv run` re-syncs to the default
extras, so any dependency change in this repo needs the extra named explicitly
afterwards.

## What would refute this

- One threshold, set by one word, on 26 verbs total. The 0.33 held-out recall has
  a wide rule-of-three bound.
- The three end-to-end numbers use the distractors I wrote; the flood collapse in
  particular is driven by `can`, which is a property of that surface's phrasing
  templates as much as of WordNet.
- A part-of-speech tagger was tried and removed: it takes real-prose firing
  0.057 → 0.017 under the any-sense rule and buys nothing once sense dominance is
  in place. It was not re-tried *with* sense dominance, and `can` as a modal is
  exactly the case a tagger would catch.
